import {
  customProvider,
  extractReasoningMiddleware,
  wrapLanguageModel,
} from 'ai';
import { xai } from '@ai-sdk/xai';
import { google } from '@ai-sdk/google';
import { isTestEnvironment } from '../constants';
import {
  artifactModel,
  chatModel,
  reasoningModel,
  titleModel,
} from './models.test';

// Environment-based configuration
export const AI_PROVIDER = process.env.AI_PROVIDER || 'xai';
export const CHAT_MODEL = process.env.CHAT_MODEL || 'grok-2-vision-1212';
export const REASONING_MODEL = process.env.REASONING_MODEL || 'grok-3-mini-beta';
export const TITLE_MODEL = process.env.TITLE_MODEL || 'grok-2-1212';
export const ARTIFACT_MODEL = process.env.ARTIFACT_MODEL || 'grok-2-1212';

export const myProvider = isTestEnvironment
  ? customProvider({
      languageModels: {
        'chat-model': chatModel,
        'chat-model-reasoning': reasoningModel,
        'title-model': titleModel,
        'artifact-model': artifactModel,
      },
    })
  : AI_PROVIDER === 'google'
  ? customProvider({
      languageModels: {
        'chat-model': google(CHAT_MODEL),
        'chat-model-reasoning': google(REASONING_MODEL),
        'title-model': google(TITLE_MODEL),
        'artifact-model': google(ARTIFACT_MODEL),
      },
    })
  : customProvider({
      languageModels: {
        'chat-model': xai(CHAT_MODEL),
        'chat-model-reasoning': wrapLanguageModel({
          model: xai(REASONING_MODEL),
          middleware: extractReasoningMiddleware({ tagName: 'think' }),
        }),
        'title-model': xai(TITLE_MODEL),
        'artifact-model': xai(ARTIFACT_MODEL),
      },
      imageModels: {
        'small-model': xai.image('grok-2-image'),
      },
    });