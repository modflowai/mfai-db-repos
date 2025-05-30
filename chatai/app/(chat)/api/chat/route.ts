import {
  appendClientMessage,
  appendResponseMessages,
  createDataStream,
  smoothStream,
  streamText,
} from 'ai';
import { auth, type UserType } from '@/app/(auth)/auth';
import { type RequestHints, systemPrompt } from '@/lib/ai/prompts';
import {
  createStreamId,
  deleteChatById,
  getChatById,
  getMessagesByChatId,
  getStreamIdsByChatId,
  saveChat,
  saveMessages,
  getUserById,
} from '@/lib/db/queries';
import { checkRateLimit } from '@/lib/rate-limit';
import { debugRateLimit } from '@/lib/debug-rate-limit';
import { generateUUID, getTrailingMessageId } from '@/lib/utils';
import { generateTitleFromUserMessage } from '../../actions';
import { createDocument } from '@/lib/ai/tools/create-document';
import { updateDocument } from '@/lib/ai/tools/update-document';
import { requestSuggestions } from '@/lib/ai/tools/request-suggestions';
import { getWeather } from '@/lib/ai/tools/get-weather';
import { intelligentMfaiSearch } from '@/lib/ai/tools/intelligent-mfai-search';
import { listRepositories } from '@/lib/ai/tools/list-repositories';
import { modularMfaiSearch } from '@/lib/ai/tools/modular-mfai-search';
import { relevanceChecker } from '@/lib/ai/tools/relevance-checker';
import { queryAnalyzer } from '@/lib/ai/tools/query-analyzer';
import { repositorySearcher } from '@/lib/ai/tools/repository-searcher';
import { createRepositoryWorkflow } from '@/lib/ai/workflow-engine';
import { createModularWorkflow, } from '@/lib/ai/modular-workflow-engine';
import { LLMIntentAnalyzer } from '@/lib/ai/llm-intent-analyzer';
import { myProvider, AI_PROVIDER } from '@/lib/ai/providers';
import { postRequestBodySchema, type PostRequestBody } from './schema';
import { geolocation } from '@vercel/functions';
import {
  createResumableStreamContext,
  type ResumableStreamContext,
} from 'resumable-stream';
import { after } from 'next/server';
import type { Chat } from '@/lib/db/schema';
import { differenceInSeconds } from 'date-fns';
import { ChatSDKError } from '@/lib/errors';

export const maxDuration = 60;

// Helper function to determine thinking budget based on message complexity
function determineBudget(messages: any[]): number {
  const lastMessage = messages[messages.length - 1];
  const messageLength = JSON.stringify(lastMessage).length;
  
  const MIN_BUDGET = Number.parseInt(process.env.THINKING_BUDGET_MIN || '1024');
  const MAX_BUDGET = Number.parseInt(process.env.THINKING_BUDGET_MAX || '24576');
  const DEFAULT_BUDGET = Number.parseInt(process.env.THINKING_BUDGET || '2048');
  
  // Simple heuristic: longer/complex messages get more thinking budget
  // Note: Values 1-1024 are automatically adjusted to 1024 by the API
  if (messageLength > 1000) return MAX_BUDGET;
  if (messageLength > 500) return DEFAULT_BUDGET;
  return MIN_BUDGET;
}

let globalStreamContext: ResumableStreamContext | null = null;

function getStreamContext() {
  if (!globalStreamContext) {
    try {
      globalStreamContext = createResumableStreamContext({
        waitUntil: after,
      });
    } catch (error: any) {
      if (error.message.includes('REDIS_URL')) {
        console.log(
          ' > Resumable streams are disabled due to missing REDIS_URL',
        );
      } else {
        console.error(error);
      }
    }
  }

  return globalStreamContext;
}

export async function POST(request: Request) {
  let requestBody: PostRequestBody;

  try {
    const json = await request.json();
    requestBody = postRequestBodySchema.parse(json);
  } catch (_) {
    return new ChatSDKError('bad_request:api').toResponse();
  }

  try {
    const { id, message, selectedChatModel, selectedVisibilityType } =
      requestBody;

    const session = await auth();

    if (!session?.user) {
      return new ChatSDKError('unauthorized:chat').toResponse();
    }

    const userType: UserType = session.user.type;

    // Get user's role from database for rate limiting
    const user = await getUserById(session.user.id);
    if (!user) {
      return new ChatSDKError('unauthorized:chat').toResponse();
    }

    // Rate limiting debug (can be removed in production)
    if (process.env.NODE_ENV === 'development') {
      await debugRateLimit(session.user.id);
    }
    
    // Check rate limits using database-driven system
    const rateLimitResult = await checkRateLimit(session.user.id, user.role);
    if (!rateLimitResult.allowed) {
      const { timeWindow, limit, resetTime } = rateLimitResult.blockedBy!;
      const retryAfterSeconds = Math.ceil((resetTime.getTime() - Date.now()) / 1000);
      
      // Create time-specific error messages
      let customMessage: string;
      const errorData: any = {
        timeWindow,
        limit,
        retryAfterSeconds,
        resetTime: resetTime.toISOString(),
        userRole: user.role
      };

      if (timeWindow === 'minute') {
        customMessage = `You're sending messages too quickly! Please wait ${retryAfterSeconds} seconds before trying again.`;
        errorData.type = 'rate_limit_minute';
      } else {
        customMessage = `You've reached your daily message limit of ${limit} messages. Please try again tomorrow or upgrade your account.`;
        errorData.type = 'rate_limit_daily';
      }
      
      const error = new ChatSDKError('rate_limit:chat', customMessage);
      const response = error.toResponse();
      
      // Add additional rate limit info to response headers
      response.headers.set('Retry-After', retryAfterSeconds.toString());
      response.headers.set('X-RateLimit-Type', timeWindow);
      response.headers.set('X-RateLimit-Limit', limit.toString());
      response.headers.set('X-RateLimit-Reset', resetTime.toISOString());
      response.headers.set('X-User-Role', user.role);
      
      return response;
    }

    const chat = await getChatById({ id });

    if (!chat) {
      const title = await generateTitleFromUserMessage({
        message,
      });

      await saveChat({
        id,
        userId: session.user.id,
        title,
        visibility: selectedVisibilityType,
      });
    } else {
      if (chat.userId !== session.user.id) {
        return new ChatSDKError('forbidden:chat').toResponse();
      }
    }

    const previousMessages = await getMessagesByChatId({ id });

    const messages = appendClientMessage({
      // @ts-expect-error: todo add type conversion from DBMessage[] to UIMessage[]
      messages: previousMessages,
      message,
    });

    const { longitude, latitude, city, country } = geolocation(request);

    const requestHints: RequestHints = {
      longitude,
      latitude,
      city,
      country,
    };

    await saveMessages({
      messages: [
        {
          chatId: id,
          id: message.id,
          role: 'user',
          parts: message.parts,
          attachments: message.experimental_attachments ?? [],
          createdAt: new Date(),
        },
      ],
    });

    const streamId = generateUUID();
    await createStreamId({ streamId, chatId: id });

    const stream = createDataStream({
      execute: async (dataStream) => {
        // Check if MCP is enabled and user query might benefit from repository search
        const lastMessage = messages[messages.length - 1];
        const mcpEnabled = process.env.MCP_ENABLED === 'true';
        
        // LLM analyzes if this query should use the intelligent workflow
        let useIntelligentWorkflow = false;
        let isRepositoryListRequest = false;
        if (mcpEnabled && selectedChatModel !== 'chat-model-reasoning') {
          try {
            const intentAnalysis = await LLMIntentAnalyzer.analyzeUserIntent(lastMessage.content);
            useIntelligentWorkflow = intentAnalysis.shouldSearch; // ONLY for actual searches
            isRepositoryListRequest = intentAnalysis.requiresRepositoryContext; // Separate flag for repo listing
            
            // Debug logging for chat route
            console.log('🚀 Chat Route Intent Analysis:', {
              query: lastMessage.content,
              shouldSearch: intentAnalysis.shouldSearch,
              requiresRepositoryContext: intentAnalysis.requiresRepositoryContext,
              useIntelligentWorkflow,
              isRepositoryListRequest,
              action: intentAnalysis.action,
              confidence: intentAnalysis.confidence
            });
            
            if (useIntelligentWorkflow) {
              dataStream.writeData({
                type: 'text-delta',
                content: `🤖 **Intelligent Agent Activated**: Using LLM-powered workflow for your query\n\n`,
              });
            }
          } catch (error) {
            console.warn('Failed to analyze intent for intelligent workflow:', error);
          }
        }

        // Use modular workflow for both search and repository listing queries  
        if (useIntelligentWorkflow || isRepositoryListRequest) {
          // Check if we should use the new modular workflow system
          const useModularWorkflow = process.env.MODULAR_WORKFLOW_ENABLED !== 'false'; // Default to enabled
          
          if (useModularWorkflow) {
            console.log('🚀 Using Modular Workflow System');
            console.log('🔧 Modular workflow - available tools:', Object.keys({
              getWeather,
              createDocument: createDocument({ session, dataStream }),
              updateDocument: updateDocument({ session, dataStream }),
              requestSuggestions: requestSuggestions({ session, dataStream }),
              intelligentMfaiSearch: intelligentMfaiSearch({ session, dataStream }),
              listRepositories: listRepositories({ session, dataStream }),
            }));
            
            // Use the new modular workflow system
            const modularWorkflow = createModularWorkflow(dataStream);
            console.log('🔧 Modular workflow - calling modular workflow engine...');
            const result = await modularWorkflow({
              model: myProvider.languageModel(selectedChatModel),
              system: systemPrompt({ selectedChatModel, requestHints }),
              messages,
              // Add Google thinking configuration for reasoning model
              ...(selectedChatModel === 'chat-model-reasoning' && AI_PROVIDER === 'google' ? {
                providerOptions: {
                  google: {
                    thinkingConfig: {
                      thinkingBudget: determineBudget(messages),
                      includeThoughts: true,
                    },
                  },
                },
              } : {}),
              experimental_transform: smoothStream({ chunking: 'word' }),
              experimental_generateMessageId: generateUUID,
              tools: {
                getWeather,
                createDocument: createDocument({ session, dataStream }),
                updateDocument: updateDocument({ session, dataStream }),
                requestSuggestions: requestSuggestions({ session, dataStream }),
                // Add MCP tools when enabled
                modularMfaiSearch: modularMfaiSearch({ session, dataStream }),
                relevanceChecker: relevanceChecker({ session, dataStream }),
                queryAnalyzer: queryAnalyzer({ session, dataStream }),
                repositorySearcher: repositorySearcher({ session, dataStream }),
                intelligentMfaiSearch: intelligentMfaiSearch({ session, dataStream }),
                listRepositories: listRepositories({ session, dataStream }),
              },
            });

            // Handle modular workflow result
            console.log('🔧 Modular workflow - result type:', typeof result);
            console.log('🔧 Modular workflow - result constructor:', result?.constructor?.name);
            console.log('🔧 Modular workflow - result has consumeStream:', typeof result?.consumeStream);
            console.log('🔧 Modular workflow - result has mergeIntoDataStream:', typeof result?.mergeIntoDataStream);
            
            if (result && typeof result.consumeStream === 'function' && typeof result.mergeIntoDataStream === 'function') {
              // This is a valid StreamText result, process it normally
              console.log('✅ Processing valid modular workflow StreamText result');
              console.log('🔧 Modular workflow - starting to consume stream...');
              result.consumeStream();
              console.log('🔧 Modular workflow - merging into data stream...');
              result.mergeIntoDataStream(dataStream, { sendReasoning: true });
              console.log('✅ Modular workflow - stream processing completed');
            } else if (result === null) {
              // Workflow completed and already streamed the response
              console.log('✅ Modular workflow completed - response already streamed to dataStream');
            } else {
              console.log('⚠️ Modular workflow - unexpected result type:', result);
            }
          } else {
            console.log('🔄 Using Legacy Workflow System');
            
            // Fall back to legacy workflow system
            const workflow = createRepositoryWorkflow(dataStream);
            const result = await workflow({
              model: myProvider.languageModel(selectedChatModel),
              system: systemPrompt({ selectedChatModel, requestHints }),
              messages,
              // Add Google thinking configuration for reasoning model
              ...(selectedChatModel === 'chat-model-reasoning' && AI_PROVIDER === 'google' ? {
                providerOptions: {
                  google: {
                    thinkingConfig: {
                      thinkingBudget: determineBudget(messages),
                      includeThoughts: true,
                    },
                  },
                },
              } : {}),
              experimental_transform: smoothStream({ chunking: 'word' }),
              experimental_generateMessageId: generateUUID,
              tools: {
                getWeather,
                createDocument: createDocument({ session, dataStream }),
                updateDocument: updateDocument({ session, dataStream }),
                requestSuggestions: requestSuggestions({ session, dataStream }),
                // Add MCP tools when enabled
                modularMfaiSearch: modularMfaiSearch({ session, dataStream }),
                relevanceChecker: relevanceChecker({ session, dataStream }),
                queryAnalyzer: queryAnalyzer({ session, dataStream }),
                repositorySearcher: repositorySearcher({ session, dataStream }),
                intelligentMfaiSearch: intelligentMfaiSearch({ session, dataStream }),
                listRepositories: listRepositories({ session, dataStream }),
              },
            });

            result.consumeStream();
            result.mergeIntoDataStream(dataStream, { sendReasoning: true });
          }
        } else {
          // Use standard streamText for general conversations
          const result = streamText({
            model: myProvider.languageModel(selectedChatModel),
            system: systemPrompt({ selectedChatModel, requestHints }),
            messages,
            maxSteps: 5,
            // Add Google thinking configuration for reasoning model
            ...(selectedChatModel === 'chat-model-reasoning' && AI_PROVIDER === 'google' ? {
              providerOptions: {
                google: {
                  thinkingConfig: {
                    thinkingBudget: determineBudget(messages),
                    includeThoughts: true,
                  },
                },
              },
            } : {}),
            experimental_activeTools:
              selectedChatModel === 'chat-model-reasoning' && AI_PROVIDER === 'xai'
                ? [] // Disable tools only for xAI reasoning mode
                : [
                    'getWeather',
                    'createDocument',
                    'updateDocument',
                    'requestSuggestions',
                    // MCP tools should NOT be available for general conversations
                    // ...(mcpEnabled ? ['intelligentMfaiSearch', 'listRepositories'] : []),
                  ],
            experimental_transform: smoothStream({ chunking: 'word' }),
            experimental_generateMessageId: generateUUID,
            tools: {
              getWeather,
              createDocument: createDocument({ session, dataStream }),
              updateDocument: updateDocument({ session, dataStream }),
              requestSuggestions: requestSuggestions({ session, dataStream }),
              // MCP tools should NOT be available for general conversations to prevent unwanted tool calls
              // ...(mcpEnabled ? {
              //   intelligentMfaiSearch: intelligentMfaiSearch({ session, dataStream }),
              //   listRepositories: listRepositories({ session, dataStream }),
              // } : {}),
            },
          });

          result.consumeStream();
          result.mergeIntoDataStream(dataStream, { sendReasoning: true });
        }
      },
      onFinish: async ({ response }) => {
        if (session.user?.id) {
          try {
            const assistantId = getTrailingMessageId({
              messages: response.messages.filter(
                (message) => message.role === 'assistant',
              ),
            });

            if (!assistantId) {
              throw new Error('No assistant message found!');
            }

            const [, assistantMessage] = appendResponseMessages({
              messages: [message],
              responseMessages: response.messages,
            });

            await saveMessages({
              messages: [
                {
                  id: assistantId,
                  chatId: id,
                  role: assistantMessage.role,
                  parts: assistantMessage.parts,
                  attachments:
                    assistantMessage.experimental_attachments ?? [],
                  createdAt: new Date(),
                },
              ],
            });
          } catch (_) {
            console.error('Failed to save chat');
          }
        }
      },
      onError: () => {
        return 'Oops, an error occurred!';
      },
    });

    const streamContext = getStreamContext();

    if (streamContext) {
      return new Response(
        await streamContext.resumableStream(streamId, () => stream),
      );
    } else {
      return new Response(stream);
    }
  } catch (error) {
    if (error instanceof ChatSDKError) {
      return error.toResponse();
    }
  }
}

export async function GET(request: Request) {
  const streamContext = getStreamContext();
  const resumeRequestedAt = new Date();

  if (!streamContext) {
    return new Response(null, { status: 204 });
  }

  const { searchParams } = new URL(request.url);
  const chatId = searchParams.get('chatId');

  if (!chatId) {
    return new ChatSDKError('bad_request:api').toResponse();
  }

  const session = await auth();

  if (!session?.user) {
    return new ChatSDKError('unauthorized:chat').toResponse();
  }

  let chat: Chat;

  try {
    chat = await getChatById({ id: chatId });
  } catch {
    return new ChatSDKError('not_found:chat').toResponse();
  }

  if (!chat) {
    return new ChatSDKError('not_found:chat').toResponse();
  }

  if (chat.visibility === 'private' && chat.userId !== session.user.id) {
    return new ChatSDKError('forbidden:chat').toResponse();
  }

  const streamIds = await getStreamIdsByChatId({ chatId });

  if (!streamIds.length) {
    return new ChatSDKError('not_found:stream').toResponse();
  }

  const recentStreamId = streamIds.at(-1);

  if (!recentStreamId) {
    return new ChatSDKError('not_found:stream').toResponse();
  }

  const emptyDataStream = createDataStream({
    execute: () => {},
  });

  const stream = await streamContext.resumableStream(
    recentStreamId,
    () => emptyDataStream,
  );

  /*
   * For when the generation is streaming during SSR
   * but the resumable stream has concluded at this point.
   */
  if (!stream) {
    const messages = await getMessagesByChatId({ id: chatId });
    const mostRecentMessage = messages.at(-1);

    if (!mostRecentMessage) {
      return new Response(emptyDataStream, { status: 200 });
    }

    if (mostRecentMessage.role !== 'assistant') {
      return new Response(emptyDataStream, { status: 200 });
    }

    const messageCreatedAt = new Date(mostRecentMessage.createdAt);

    if (differenceInSeconds(resumeRequestedAt, messageCreatedAt) > 15) {
      return new Response(emptyDataStream, { status: 200 });
    }

    const restoredStream = createDataStream({
      execute: (buffer) => {
        buffer.writeData({
          type: 'append-message',
          message: JSON.stringify(mostRecentMessage),
        });
      },
    });

    return new Response(restoredStream, { status: 200 });
  }

  return new Response(stream, { status: 200 });
}

export async function DELETE(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');

  if (!id) {
    return new ChatSDKError('bad_request:api').toResponse();
  }

  const session = await auth();

  if (!session?.user) {
    return new ChatSDKError('unauthorized:chat').toResponse();
  }

  const chat = await getChatById({ id });

  if (chat.userId !== session.user.id) {
    return new ChatSDKError('forbidden:chat').toResponse();
  }

  const deletedChat = await deleteChatById({ id });

  return Response.json(deletedChat, { status: 200 });
}
