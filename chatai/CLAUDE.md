# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Documentation Strategy

**Important**: This project maintains detailed documentation of its evolution:

- **`docs/original_behavior.md`** - Analysis of the initial codebase state, implementation details, and baseline behaviors before any modifications
- **`docs/roadmap.md`** - Planned changes, feature additions, and architectural improvements  
- **`docs/changelog.md`** - Detailed record of all changes made, including rationale and impact

**Always check these docs before making changes** to understand the original system and avoid breaking existing functionality.

## Project Overview

This is the **Chat SDK** - an open-source template for building powerful chatbot applications. It's designed to help developers quickly build production-ready chatbots without starting from scratch, supporting everything from small side projects to full-scale enterprise solutions.

Built with Next.js App Router, AI SDK, and PostgreSQL with advanced features like generative UI, artifacts, code execution, multimodal support, and built-in authentication.

## Essential Commands

### Development Setup
```bash
# Install dependencies
pnpm install

# Database migration (REQUIRED before first run)
pnpm exec tsx lib/db/migrate.ts

# Start development server  
pnpm dev
```

### Database Operations
```bash
# Generate new migrations
pnpm db:generate

# Run migrations
pnpm db:migrate

# Open Drizzle Studio
pnpm db:studio

# Push schema changes  
pnpm db:push
```

### Code Quality & Testing
```bash
# Lint and auto-fix
pnpm lint
pnpm lint:fix

# Format with Biome
pnpm format

# Run Playwright E2E tests
pnpm test
```

### Build & Production
```bash
# Build for production (includes automatic DB migration)
pnpm build

# Start production server
pnpm start
```

## Critical Setup Requirements

### Environment Variables
Copy `.env.example` to `.env.local` and configure:

**Required:**
- `AUTH_SECRET` - Generate with `openssl rand -base64 32`
- `POSTGRES_URL` - PostgreSQL connection string  
- `BLOB_READ_WRITE_TOKEN` - Vercel Blob storage token
- `XAI_API_KEY` - xAI Grok API key from https://console.x.ai/

**Optional:**
- `REDIS_URL` - Redis for caching
- Additional provider API keys as needed

### Database Initialization
**CRITICAL:** Must run `pnpm exec tsx lib/db/migrate.ts` before first use.
Without this, authentication and chat persistence will fail.

## Architecture Overview

### Next.js App Router Structure
- `app/(auth)/` - Authentication routes and API handlers
- `app/(chat)/` - Main chat interface and chat API
- `artifacts/` - Generative UI artifacts (text, code, image, sheet)
- `lib/ai/` - AI providers, models, tools, and prompts
- `lib/db/` - Database schema, queries, migrations (Drizzle ORM)

### Core Features

**Generative User Interfaces**
- Go beyond text with interactive UI components in chat responses
- Custom artifacts for specific workflows and activities

**Artifacts System** 
- **Text**: Rich text editing with ProseMirror
- **Code**: Syntax-highlighted editor with execution capabilities  
- **Image**: AI image generation
- **Sheet**: Spreadsheet/data grid functionality

**Code Execution**
- Run code snippets directly in browser
- Display outputs as text or images in chat

**Multimodal Support**
- File uploads, images, and media attachments
- Stored in Vercel Blob storage with secure URLs

**Authentication & Sharing**
- Built-in email/password authentication via Auth.js
- Guest user support (auto-created sessions)
- Chat visibility controls for sharing

### AI Provider System

**Model Configuration**
- Uses AI SDK for model abstraction
- Default: xAI Grok models (`grok-2-vision-1212`, `grok-3-mini-beta`)
- Configurable per use case in `lib/ai/providers.ts`
- Separate models for chat, reasoning, title generation, artifacts

**Tool Integration**
- Document creation and editing tools
- Weather information tool
- Suggestion system for collaborative editing

### Data Flow Architecture

1. **Request Processing**: Messages go through Next.js middleware → Vercel firewall → rate limiting → `/api/chat`
2. **Model Interaction**: AI SDK's `streamText` with custom provider routing
3. **Response Streaming**: Data stream protocol via `useChat` hook
4. **Persistence**: `onFinish` callback saves to PostgreSQL via Drizzle ORM
5. **User Interaction**: Vote, edit, and share capabilities

### Database Schema (PostgreSQL + Drizzle)

**Core Tables:**
- **Users**: Authentication (OAuth + guest users)
- **Chats**: Conversation history with visibility settings
- **Messages**: v2 schema with parts and attachments support
- **Documents**: Artifact storage and versioning
- **Suggestions**: Collaborative editing suggestions
- **Votes**: Message feedback system

**Key Features:**
- Multi-database provider support (Neon, Supabase, etc.)
- Type-safe queries with Drizzle ORM
- Automatic migrations on build

## Customization Guide

### Models and Providers

**Switching Providers**
- Edit `lib/ai/models.ts` to change the `myProvider` configuration
- Default uses xAI, but supports all AI SDK providers (Anthropic, OpenAI, etc.)
- Install provider packages and update model references

**Model Types:**
- `chat-model` - Main conversation model
- `chat-model-reasoning` - Reasoning with extractReasoningMiddleware 
- `title-model` - Chat title generation
- `artifact-model` - Artifact creation/editing
- `small-model` - Image generation (imageModels)

**Example Provider Switch:**
```typescript
import { anthropic } from "@ai-sdk/anthropic";

export const myProvider = customProvider({
  languageModels: {
    "chat-model": anthropic("claude-3-5-sonnet"),
    // ... other models
  }
});
```

### Adding Custom Artifacts

**Structure:**
```
artifacts/
  custom/
    client.tsx  # Client-side artifact UI
    server.ts   # Server-side processing
```

**Integration Steps:**
1. Create client/server files in `artifacts/custom/`
2. Add to `lib/artifacts/server.ts` documentHandlersByArtifactKind
3. Update database schema in `lib/db/schema.ts` 
4. Register in `components/artifact.tsx` artifactDefinitions

**Artifact Capabilities:**
- Streaming updates with onStreamPart
- Diff mode for version comparison
- Custom toolbar actions
- Metadata management
- Content persistence

### Theming

**CSS Variables System:**
- Uses Tailwind + shadcn/ui with CSS custom properties
- Modify `app/globals.css` for theme customization
- Supports light/dark mode with automatic switching

**Key Variables:**
- `--background/--foreground` - Base colors
- `--primary/--primary-foreground` - Primary brand colors
- `--secondary/--muted/--accent` - Supporting colors
- `--sidebar-*` - Sidebar specific colors
- `--destructive` - Error/warning states
- `--border/--input/--ring` - UI element styling

**Convention:**
Background suffix omitted - `bg-primary` uses `--primary`, `text-primary-foreground` uses `--primary-foreground`

### Typography

**Default Fonts:**
- Geist Sans (sans-serif)
- Geist Mono (monospace)

**Custom Font Setup:**
1. Import via `next/font` in `app/layout.tsx`
2. Add CSS variables with `variable` option
3. Update `tailwind.config.ts` fontFamily configuration

**Example:**
```typescript
const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

// In tailwind.config.ts
fontFamily: {
  sans: ['var(--font-inter)'],
}
```

### Security & Performance

**Protection:**
- Vercel Firewall for endpoint protection
- Rate limiting on expensive endpoints like `/api/chat`
- Session-based authentication with middleware

**Optimization:**
- Streaming responses for real-time UX
- Blob storage for efficient file handling
- Serverless function deployment model

### Testing Strategy

**Playwright E2E Testing:**
- Chat interface flows
- Artifact creation and editing
- Authentication and session management
- Reasoning capabilities
- Test environment uses `PLAYWRIGHT=True` flag

### Development Notes

**Tech Stack:**
- Next.js 15 App Router with React 19
- TypeScript for type safety
- Tailwind CSS + shadcn/ui components
- Biome (formatting) + ESLint (linting)

**Common Patterns:**
- Server Actions in `actions.ts` files
- API routes with Zod schema validation
- Streaming responses for AI interactions
- Database queries centralized in `lib/db/queries.ts`

**Deployment:**
- Optimized for Vercel with 1-click deploy
- Automatic environment setup with integrations
- Production builds include automatic DB migration