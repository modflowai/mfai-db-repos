'use client';

import type { Attachment, UIMessage } from 'ai';
import { useChat } from '@ai-sdk/react';
import { useEffect, useState } from 'react';
import useSWR, { useSWRConfig } from 'swr';
import { ChatHeader } from '@/components/chat-header';
import type { Vote } from '@/lib/db/schema';
import { fetcher, fetchWithErrorHandlers, generateUUID } from '@/lib/utils';
import { Artifact } from './artifact';
import { MultimodalInput } from './multimodal-input';
import { Messages } from './messages';
import type { VisibilityType } from './visibility-selector';
import { useArtifactSelector } from '@/hooks/use-artifact';
import { unstable_serialize } from 'swr/infinite';
import { getChatHistoryPaginationKey } from './sidebar-history';
import { toast } from './toast';
import type { Session } from 'next-auth';
import { useSearchParams } from 'next/navigation';
import { useChatVisibility } from '@/hooks/use-chat-visibility';
import { useAutoResume } from '@/hooks/use-auto-resume';
import { ChatSDKError } from '@/lib/errors';
import { RateLimitModal } from './rate-limit-modal';

export function Chat({
  id,
  initialMessages,
  initialChatModel,
  initialVisibilityType,
  isReadonly,
  session,
  autoResume,
}: {
  id: string;
  initialMessages: Array<UIMessage>;
  initialChatModel: string;
  initialVisibilityType: VisibilityType;
  isReadonly: boolean;
  session: Session;
  autoResume: boolean;
}) {
  const { mutate } = useSWRConfig();

  const { visibilityType } = useChatVisibility({
    chatId: id,
    initialVisibilityType,
  });

  const {
    messages,
    setMessages,
    handleSubmit,
    input,
    setInput,
    append,
    status,
    stop,
    reload,
    experimental_resume,
    data,
    error,
  } = useChat({
    id,
    initialMessages,
    experimental_throttle: 100,
    sendExtraMessageFields: true,
    generateId: generateUUID,
    fetch: fetchWithErrorHandlers,
    experimental_prepareRequestBody: (body) => ({
      id,
      message: body.messages.at(-1),
      selectedChatModel: initialChatModel,
      selectedVisibilityType: visibilityType,
    }),
    onFinish: () => {
      mutate(unstable_serialize(getChatHistoryPaginationKey));
    },
    onError: async (error) => {
      if (error instanceof ChatSDKError) {
        // Handle rate limit errors with custom modal
        if (error.type === 'rate_limit' && error.rateLimitDetails) {
          // Calculate next tier information
          let nextTier = null;
          try {
            const response = await fetch(`/api/rate-limit/next-tier?userRole=${error.rateLimitDetails.userRole}`);
            if (response.ok) {
              const { nextTierInfo } = await response.json();
              nextTier = nextTierInfo ? {
                role: nextTierInfo.role,
                dailyLimit: nextTierInfo.limits.find((l: any) => l.timeWindow === 'daily')?.limit || 0
              } : null;
            }
          } catch (fetchError) {
            console.error('Failed to fetch next tier info:', fetchError);
          }

          setRateLimitModal({
            isOpen: true,
            type: error.rateLimitDetails.timeWindow,
            retryAfterSeconds: error.rateLimitDetails.retryAfterSeconds,
            limit: error.rateLimitDetails.limit,
            userRole: error.rateLimitDetails.userRole,
            nextTier
          });
        } else {
          // Handle other errors with toast
          toast({
            type: 'error',
            description: error.message,
          });
        }
      }
    },
  });

  // Reset chat status when rate limit or other errors occur
  useEffect(() => {
    if (error && (status === 'submitted' || status === 'streaming')) {
      // Force reset the status by stopping current stream
      stop();
    }
  }, [error, status, stop]);

  const searchParams = useSearchParams();
  const query = searchParams.get('query');

  const [hasAppendedQuery, setHasAppendedQuery] = useState(false);

  useEffect(() => {
    if (query && !hasAppendedQuery) {
      append({
        role: 'user',
        content: query,
      });

      setHasAppendedQuery(true);
      window.history.replaceState({}, '', `/chat/${id}`);
    }
  }, [query, append, hasAppendedQuery, id]);

  const { data: votes } = useSWR<Array<Vote>>(
    messages.length >= 2 ? `/api/vote?chatId=${id}` : null,
    fetcher,
  );

  const [attachments, setAttachments] = useState<Array<Attachment>>([]);
  const isArtifactVisible = useArtifactSelector((state) => state.isVisible);

  // Rate limit modal state
  const [rateLimitModal, setRateLimitModal] = useState<{
    isOpen: boolean;
    type: 'minute' | 'daily';
    retryAfterSeconds: number;
    limit: number;
    userRole: 'guest' | 'regular' | 'premium';
    nextTier?: {
      role: 'guest' | 'regular' | 'premium';
      dailyLimit: number;
    } | null;
  }>({
    isOpen: false,
    type: 'minute',
    retryAfterSeconds: 0,
    limit: 0,
    userRole: 'guest',
    nextTier: undefined
  });

  useAutoResume({
    autoResume,
    initialMessages,
    experimental_resume,
    data,
    setMessages,
  });

  const closeRateLimitModal = () => {
    setRateLimitModal(prev => ({ ...prev, isOpen: false }));
  };

  return (
    <>
      <div className="flex flex-col min-w-0 h-dvh bg-background">
        <ChatHeader
          chatId={id}
          selectedModelId={initialChatModel}
          selectedVisibilityType={initialVisibilityType}
          isReadonly={isReadonly}
          session={session}
        />

        <Messages
          chatId={id}
          status={status}
          votes={votes}
          messages={messages}
          setMessages={setMessages}
          reload={reload}
          isReadonly={isReadonly}
          isArtifactVisible={isArtifactVisible}
        />

        <form className="flex mx-auto px-4 bg-background pb-4 md:pb-6 gap-2 w-full md:max-w-3xl">
          {!isReadonly && (
            <MultimodalInput
              chatId={id}
              input={input}
              setInput={setInput}
              handleSubmit={handleSubmit}
              status={status}
              stop={stop}
              attachments={attachments}
              setAttachments={setAttachments}
              messages={messages}
              setMessages={setMessages}
              append={append}
              selectedVisibilityType={visibilityType}
              error={error}
            />
          )}
        </form>
      </div>

      <Artifact
        chatId={id}
        input={input}
        setInput={setInput}
        handleSubmit={handleSubmit}
        status={status}
        stop={stop}
        attachments={attachments}
        setAttachments={setAttachments}
        append={append}
        messages={messages}
        setMessages={setMessages}
        reload={reload}
        votes={votes}
        isReadonly={isReadonly}
        selectedVisibilityType={visibilityType}
        error={error}
      />

      <RateLimitModal
        isOpen={rateLimitModal.isOpen}
        onClose={closeRateLimitModal}
        type={rateLimitModal.type}
        retryAfterSeconds={rateLimitModal.retryAfterSeconds}
        limit={rateLimitModal.limit}
        userRole={rateLimitModal.userRole}
        nextTier={rateLimitModal.nextTier}
      />
    </>
  );
}
