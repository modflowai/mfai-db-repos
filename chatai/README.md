<a href="https://chat.vercel.ai/">
  <img alt="Next.js 14 and App Router-ready AI chatbot." src="app/(chat)/opengraph-image.png">
  <h1 align="center">Chat SDK</h1>
</a>

<p align="center">
    Chat SDK is a free, open-source template built with Next.js and the AI SDK that helps you quickly build powerful chatbot applications.
</p>

<p align="center">
  <a href="https://chat-sdk.dev"><strong>Read Docs</strong></a> ·
  <a href="#features"><strong>Features</strong></a> ·
  <a href="#model-providers"><strong>Model Providers</strong></a> ·
  <a href="#deploy-your-own"><strong>Deploy Your Own</strong></a> ·
  <a href="#running-locally"><strong>Running locally</strong></a>
</p>
<br/>

## ✨ Features

### 🚀 **Core Framework**
- **[Next.js 15](https://nextjs.org)** App Router with React 19
  - Advanced routing for seamless navigation and performance
  - React Server Components (RSCs) and Server Actions for server-side rendering
  - Optimized for production deployment

### 🤖 **AI-Powered**
- **[AI SDK](https://sdk.vercel.ai/docs)** integration
  - Unified API for generating text, structured objects, and tool calls with LLMs
  - Hooks for building dynamic chat and generative user interfaces
  - Supports xAI (default), OpenAI, Anthropic, Fireworks, and other model providers
  - **Reasoning** capabilities with extractReasoningMiddleware
  - **Tool usage** for enhanced functionality

### 🎨 **Generative User Interfaces**
- Go beyond text with interactive UI components in chat responses
- **Artifacts System** for complex workflows:
  - **Text**: Rich text editing with ProseMirror
  - **Code**: Syntax-highlighted editor with execution capabilities
  - **Image**: AI image generation and editing
  - **Sheet**: Spreadsheet/data grid functionality
- **Code Execution** - Run code snippets directly in browser
- **Diff Mode** for version comparison and collaborative editing

### 📁 **Multimodal Support**
- File uploads, images, and media attachments
- Secure file storage with [Vercel Blob](https://vercel.com/storage/blob)
- Support for all media types that models can process

### 🔐 **Authentication & Security**
- **[Auth.js](https://authjs.dev)** for simple and secure authentication
- **Multiple authentication methods**: 
  - Email/password authentication
  - Google OAuth integration
  - GitHub OAuth integration
  - Guest access with Cloudflare Turnstile protection
- **Login-first flow** with bot protection for guest accounts
- **Role-based user system**: Guest, Regular, and Premium roles with different rate limits
- **Professional rate limit experience** with smart modals and upgrade prompts
- **Chat visibility controls** for sharing conversations
- **Production-ready security** with Cloudflare Pro integration guidelines

### 🗄️ **Data Persistence**
- **[PostgreSQL](https://vercel.com/marketplace/neon)** with [Drizzle ORM](https://orm.drizzle.team/)
- Chat history and user data storage
- **Messages v2 schema** with parts and attachments support
- Document versioning for artifacts
- Suggestion system for collaborative editing

### 🎨 **Design System**
- **[shadcn/ui](https://ui.shadcn.com)** component library
- **[Tailwind CSS](https://tailwindcss.com)** for styling
- **[Radix UI](https://radix-ui.com)** primitives for accessibility
- **Light/Dark mode** support
- **Customizable themes** via CSS variables

### 🛡️ **Security & Performance**
- **Multi-layer security architecture**:
  - **Cloudflare Pro** integration ready (rate limiting, WAF, bot protection)
  - **Turnstile CAPTCHA** for guest account creation
  - **Login-first flow** prevents automated abuse
- **Professional rate limiting system** with enhanced user experience
  - **Database-driven limits**: Guest (3/min, 20/day), Regular (5/min, 100/day), Premium (10/min, 1000/day)
  - **Redis enforcement** with automatic TTL cleanup and graceful degradation
  - **Smart error modals**: Different UI for per-minute vs per-day limits
  - **Live countdown timers** for temporary rate limits
  - **Role-based upgrade prompts** with clear upgrade paths
  - **No UI blocking** - proper error handling without stuck states
- **Production security checklist** included
- **Session-based authentication** with middleware
- **Streaming responses** for real-time UX
- **Serverless function** deployment model

### 🧪 **Testing**
- **[Playwright](https://playwright.dev/)** E2E testing suite
- Tests for chat flows, artifacts, authentication, and reasoning
- CI/CD integration ready

## Model Providers

This template ships with [xAI](https://x.ai) `grok-2-1212` and `grok-3-mini-beta` as the default models. The AI SDK architecture allows you to easily switch between providers:

### Supported Providers
- **xAI** (default) - Grok models with reasoning capabilities
- **[OpenAI](https://openai.com)** - GPT models
- **[Anthropic](https://anthropic.com)** - Claude models
- **[Cohere](https://cohere.com/)** - Command models
- **[Fireworks](https://fireworks.ai/)** - Various open-source models
- **[Many more](https://sdk.vercel.ai/providers/ai-sdk-providers)** supported by AI SDK

### Model Configuration
Different models can be used for specific purposes:
- **Chat Model** - Main conversation interface
- **Reasoning Model** - Complex problem solving with chain-of-thought
- **Title Model** - Chat title generation
- **Artifact Model** - Document and code generation
- **Image Model** - Image generation and editing

Switch providers by editing `lib/ai/models.ts`:

```typescript
export const myProvider = customProvider({
  languageModels: {
    "chat-model": anthropic("claude-3-5-sonnet"), // Easy provider switch
    "title-model": openai("gpt-4o-mini"),
    // ... other models
  }
});
```

## Deploy Your Own

### 🚀 One-Click Deploy (Recommended)

Deploy to Vercel with automatic environment setup:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fvercel%2Fai-chatbot&env=AUTH_SECRET&envDescription=Generate%20a%20random%20secret%20to%20use%20for%20authentication&envLink=https%3A%2F%2Fgenerate-secret.vercel.app%2F32&project-name=my-awesome-chatbot&repository-name=my-awesome-chatbot&demo-title=AI%20Chatbot&demo-description=An%20Open-Source%20AI%20Chatbot%20Template%20Built%20With%20Next.js%20and%20the%20AI%20SDK%20by%20Vercel&demo-url=https%3A%2F%2Fchat.vercel.ai&products=%5B%7B%22type%22%3A%22integration%22%2C%22protocol%22%3A%22ai%22%2C%22productSlug%22%3A%22grok%22%2C%22integrationSlug%22%3A%22xai%22%7D%2C%7B%22type%22%3A%22integration%22%2C%22protocol%22%3A%22storage%22%2C%22productSlug%22%3A%22neon%22%2C%22integrationSlug%22%3A%22neon%22%7D%2C%7B%22type%22%3A%22blob%22%7D%5D)

This will automatically:
- Create a new repository
- Set up Vercel project
- Configure Neon PostgreSQL database
- Set up xAI integration
- Configure Vercel Blob storage

### 🔧 Manual Deployment

1. Fork this repository
2. Connect to Vercel
3. Configure environment variables (see below)
4. Deploy

## Running Locally

### Prerequisites
- Node.js 18+ and pnpm
- PostgreSQL database (local or hosted)
- AI provider API key (xAI, OpenAI, Anthropic, etc.)

### Quick Start

#### Method 1: With Vercel CLI (Recommended)
```bash
# Install Vercel CLI
npm i -g vercel

# Link to Vercel project
vercel link

# Pull environment variables
vercel env pull

# Install dependencies
pnpm install

# Run database migrations (REQUIRED)
pnpm exec tsx lib/db/migrate.ts

# Start development server
pnpm dev
```

#### Method 2: Manual Setup
```bash
# Clone and install
git clone <your-fork>
cd chat-ai-sdk
pnpm install

# Setup environment
cp .env.example .env.local
# Edit .env.local with your values

# Database setup (REQUIRED)
pnpm exec tsx lib/db/migrate.ts

# Start development
pnpm dev
```

Your app will be running on [localhost:3000](http://localhost:3000).

## 🗄️ Database Setup (Required)

This project uses [Drizzle ORM](https://orm.drizzle.team/) with PostgreSQL. Database setup is **mandatory** for the app to function.

### 1. Environment Variables

Create `.env.local` from the example:
```bash
cp .env.example .env.local
```

**Required Environment Variables:**
```bash
# Authentication
AUTH_SECRET=your-secret-here              # Generate: openssl rand -base64 32

# Database  
POSTGRES_URL=postgresql://user:pass@host:5432/db

# AI Provider (choose one or more)
XAI_API_KEY=your-xai-key                 # Get from https://console.x.ai/
OPENAI_API_KEY=your-openai-key           # Alternative to xAI
ANTHROPIC_API_KEY=your-anthropic-key     # Alternative to xAI

# File Storage
BLOB_READ_WRITE_TOKEN=your-blob-token    # Vercel Blob storage

# Rate Limiting (Required for production)
UPSTASH_REDIS_REST_URL=your-upstash-url   # Upstash Redis for rate limiting
UPSTASH_REDIS_REST_TOKEN=your-upstash-token

# Optional
REDIS_URL=your-redis-url                 # For additional caching
```

**Database Providers:**
- **[Neon](https://vercel.com/marketplace/neon)** (recommended, free tier)
- **[Supabase](https://supabase.com/)**
- **[Vercel Postgres](https://vercel.com/storage/postgres)**
- Any PostgreSQL-compatible database

### 2. Run Database Setup

**Complete Database Setup (Required for fresh installations):**

```bash
# 1. Run all migrations (creates tables and schema)
pnpm exec tsx lib/db/migrate.ts

# 2. Insert rate limits data (required for rate limiting functionality)
pnpm exec tsx lib/db/insert-rate-limits.ts
```

**What the migrations include:**
- ✅ User authentication system with role-based access (`guest`, `regular`, `premium`)
- ✅ Chat history and message persistence (v2 schema with parts/attachments)
- ✅ Artifacts system (documents, suggestions, voting)
- ✅ Rate limiting infrastructure with configurable limits per role
- ✅ File streaming and upload support

> ❗ **Important:** Without running both steps, you'll encounter errors like:
> - `CallbackRouteError` during authentication
> - `An error occurred while executing a database query`
> - Guest login and chat history won't work
> - Rate limiting will fail

### 3. Database Commands

```bash
# Generate new migrations after schema changes
pnpm db:generate

# Run migrations
pnpm db:migrate

# Open Drizzle Studio (database GUI)
pnpm db:studio

# Push schema changes directly
pnpm db:push
```

## 🛠️ Development

### Available Scripts

```bash
# Development
pnpm dev                    # Start development server
pnpm build                  # Build for production (includes auto-migration)
pnpm start                  # Start production server

# Code Quality
pnpm lint                   # Run ESLint
pnpm lint:fix              # Fix linting issues
pnpm format                # Format with Biome

# Testing
pnpm test                   # Run Playwright E2E tests

# Database
pnpm db:generate           # Generate migrations
pnpm db:migrate            # Run migrations
pnpm db:studio             # Open Drizzle Studio
pnpm db:push               # Push schema changes
```

### Project Structure

```
├── app/
│   ├── (auth)/            # Authentication routes
│   ├── (chat)/            # Main chat interface
│   └── api/               # API endpoints
├── artifacts/             # Generative UI artifacts
│   ├── text/              # Text artifact
│   ├── code/              # Code artifact  
│   ├── image/             # Image artifact
│   └── sheet/             # Sheet artifact
├── components/            # React components
├── lib/
│   ├── ai/                # AI providers and tools
│   ├── db/                # Database schema and queries
│   └── utils/             # Utility functions
├── hooks/                 # Custom React hooks
└── tests/                 # E2E tests
```

### Customization

#### Adding Custom Artifacts
1. Create folder in `artifacts/` with `client.tsx` and `server.ts`
2. Register in `lib/artifacts/server.ts`
3. Update database schema in `lib/db/schema.ts`
4. Add to `components/artifact.tsx`

#### Theming
- Edit CSS variables in `app/globals.css`
- Supports automatic light/dark mode switching
- Full Tailwind CSS customization

#### Typography
- Default: Geist Sans/Mono fonts
- Customize via `next/font` in `app/layout.tsx`
- Update `tailwind.config.ts` for font family changes

## 🚨 Troubleshooting

### Common Issues

**Database Connection Errors:**
- Ensure `POSTGRES_URL` is correctly formatted
- Run `pnpm exec tsx lib/db/migrate.ts`
- Check database provider status

**Authentication Issues:**
- Generate new `AUTH_SECRET` with `openssl rand -base64 32`
- Ensure database migrations have run
- Check browser console for detailed errors

**AI Provider Errors:**
- Verify API keys are valid and have sufficient credits
- Check rate limits and quotas
- Ensure correct model names in `lib/ai/models.ts`

**File Upload Issues:**
- Verify `BLOB_READ_WRITE_TOKEN` is set
- Check Vercel Blob storage limits
- Ensure proper CORS configuration

**Rate Limiting Issues:**
- Ensure `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are set
- Access Upstash Redis CLI: [https://console.upstash.com](https://console.upstash.com/vercel/kv/60af18fc-b7f5-4344-b3d9-0b969ef8c879?tab=cli)
- Clear all rate limit keys in Upstash Redis:
  ```
  EVAL "return redis.call('del', unpack(redis.call('keys', 'rate-limit:user:*')))" 0
  ```
- View all rate limit keys: `KEYS rate-limit:user:*`
- Delete specific user's limits: `DEL rate-limit:user:{userId}:minute rate-limit:user:{userId}:daily`
- Rate limits reset automatically (minute: 60s, daily: 24h)

### Getting Help

- 📖 **[Official Documentation](https://chat-sdk.dev/docs)**
- 🐛 **[Report Issues](https://github.com/vercel/ai-chatbot/issues)**
- 💬 **[Community Discussions](https://github.com/vercel/ai-chatbot/discussions)**

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

Built with:
- [Vercel](https://vercel.com) - Deployment and hosting
- [AI SDK](https://sdk.vercel.ai) - AI integration framework
- [Next.js](https://nextjs.org) - React framework
- [Drizzle ORM](https://orm.drizzle.team) - Database toolkit
- [shadcn/ui](https://ui.shadcn.com) - Component library
- [Tailwind CSS](https://tailwindcss.com) - CSS framework