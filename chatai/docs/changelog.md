# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Documentation structure in `docs/` folder
- `docs/original_behavior.md` - Analysis of initial codebase state
- `docs/roadmap.md` - Planned changes and improvements  
- `docs/changelog.md` - This changelog file
- Updated `CLAUDE.md` with documentation strategy

### Completed: Gemini Model Integration (Phase 3)
- ✅ Installed `@ai-sdk/google` package (v1.2.18) for Google Generative AI support
- ✅ Added comprehensive environment variables for AI provider configuration in `.env.example`
- ✅ Updated `lib/ai/providers.ts` with environment-based provider switching logic
- ✅ Modified chat route to support dynamic thinking budget for Gemini models
- ✅ Implemented `determineBudget()` function for intelligent token allocation
- ✅ Maintained full backward compatibility with existing xAI models

#### Technical Implementation Details
- **Provider Selection**: `AI_PROVIDER` environment variable controls provider (defaults to 'xai')
- **Model Configuration**: Separate env vars for chat, reasoning, title, and artifact models
- **Thinking Budget**: Dynamic allocation (1024-24576 tokens) based on message complexity
- **Google-specific Features**: `providerOptions` passed only when using Google + reasoning model
- **No Frontend Changes**: Reasoning toggle works identically for both providers

### Completed: Google OAuth Integration
- ✅ Added Google OAuth environment variables to `.env.example`
- ✅ Imported Google provider from `next-auth/providers/google` in `auth.ts`
- ✅ Configured Google provider with `AUTH_GOOGLE_ID` and `AUTH_GOOGLE_SECRET`
- ✅ Added `signIn` callback to handle Google OAuth user creation/linking
- ✅ Created reusable `GoogleSignInButton` component with Google branding
- ✅ Integrated Google sign-in button in both login and register pages
- ✅ Set up Google Cloud Console OAuth credentials (published for public access)
- ✅ Successfully tested with multiple Google accounts (organization and Gmail)

### Completed: User Role Column Implementation
- ✅ Added `role` column to User table schema with enum type (`'guest' | 'regular' | 'premium'`)
- ✅ Generated migration `0007_open_paibok.sql` with Drizzle ORM
- ✅ Successfully applied migration to production database
- ✅ Updated `createGuestUser()` to set role = 'guest'
- ✅ Updated `createUser()` (email/password) to set role = 'regular'
- ✅ Google OAuth users automatically get role = 'regular' via existing logic
- ✅ Added `UserRole` type and `roleToUserType()` mapping utility
- ✅ Maintained full backward compatibility with existing UserType system
- ✅ All existing users automatically assigned 'guest' role via migration default

### Completed: Database-Driven Rate Limiting System
- ✅ Created `RateLimit` table with role-based limits for multiple time windows
- ✅ Generated migration `0008_wild_zaran.sql` with seeded rate limits
- ✅ Implemented Redis-based rate limiting using Upstash
- ✅ Added `@upstash/redis` package and environment configuration
- ✅ Created `lib/rate-limit.ts` utility with multi-window checking
- ✅ Added `getRateLimitsByRole()` database query function
- ✅ Integrated rate limiting into chat API with proper 429 responses
- ✅ Fixed frontend useChat hook status management for rate limit errors
- ✅ Updated MultimodalInput to handle rate limit errors gracefully
- ✅ Added debug utilities for monitoring Redis keys and counters
- ✅ Implemented graceful degradation patterns for Redis failures
- ✅ Set rate limits: Guest (3/min, 20/day), Regular (5/min, 100/day), Premium (10/min, 1000/day)

### Completed: Enhanced Rate Limit User Experience
- ✅ Created dedicated `RateLimitModal` component with time-window-specific designs
- ✅ Implemented different modals for per-minute vs per-day rate limits
- ✅ Added per-minute modal with live countdown timer and auto-close functionality
- ✅ Added daily limit modal with role-based upgrade prompts and action buttons
- ✅ Enhanced `ChatSDKError` class with `RateLimitDetails` interface
- ✅ Updated API response headers to include rate limit metadata
- ✅ Improved `fetchWithErrorHandlers` to extract rate limit details from headers
- ✅ Added visual distinction with different icons (clock/calendar) and colors
- ✅ Implemented role-aware messaging for guest vs regular users
- ✅ Added professional upgrade prompts with clear value propositions

### Technical Details
- Google OAuth users are treated as `'regular'` user type
- Automatic user creation in database for new Google OAuth users
- Existing email/password and guest user flows remain unchanged
- UI maintains consistent styling with divider between OAuth and email options

### Context
- Established baseline documentation before making any functional changes
- Analyzed guest user system revealing permanent persistence behavior
- Planned minimal approach for Google OAuth integration

---

## [Phase 2 - In Progress] Production Security Hardening

### Added
- **Login-first authentication flow** to prevent automatic guest account creation
- **Cloudflare Turnstile integration** for bot protection on guest accounts
- **GitHub OAuth authentication** as additional sign-in method
- **Production security documentation** (`/docs/production-security-checklist.md`)
- Components:
  - `components/guest-signin-button.tsx` - Guest sign-in with Turnstile verification
  - `components/github-signin-button.tsx` - GitHub OAuth sign-in button

### Changed
- **Middleware redirect logic** - Now redirects unauthenticated users to `/login` instead of auto-creating guests
- **Guest account creation** - Requires Turnstile verification before account creation
- **Login/Register pages** - Added GitHub sign-in option and guest sign-in with CAPTCHA
- **Environment variables** - Added `NEXT_PUBLIC_TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`, `AUTH_GITHUB_ID`, `AUTH_GITHUB_SECRET`

### Security Improvements
- ✅ Prevented infinite redirect loop on login page
- ✅ Added Turnstile verification to guest account creation
- ✅ Implemented login-first flow to prevent automated abuse
- ✅ Added GitHub as additional OAuth provider
- ✅ Created comprehensive production security checklist

### Technical Details
- Guest accounts now require human verification via Turnstile
- OAuth providers (Google and GitHub) handle user creation automatically
- Middleware prevents redirect loops by allowing unauthenticated access to auth pages
- Total code changes: ~200 lines (including new components)

### Removed: Email/Password Authentication
- ✅ Removed register page and all registration routes
- ✅ Removed email/password Credentials provider from auth configuration
- ✅ Removed auth-form.tsx and actions.ts (no longer needed)
- ✅ Updated login page to show only OAuth and guest options
- ✅ Simplified createUser function for OAuth-only flow
- ✅ Updated middleware to remove register references
- ✅ Improved security by eliminating password management entirely

### Security Benefits
- No password storage means no password breaches
- No weak passwords or credential stuffing attacks
- OAuth providers handle all security (2FA, suspicious login detection)
- Reduced attack surface and support burden
- Natural spam reduction through provider verification

---

## Initial State (Before Documentation)

### Authentication System
- NextAuth v5 with Credentials provider for email/password
- Guest user system with permanent database persistence
- Automatic guest user creation on first visit
- Session management via HTTP-only cookies

### Core Features  
- Chat interface with AI SDK integration
- Artifacts system (text, code, image, sheet)
- Real-time message streaming
- File upload support via Vercel Blob
- PostgreSQL database with Drizzle ORM
- Playwright E2E testing suite

### Tech Stack
- Next.js 15 App Router with React 19
- TypeScript with strict configuration
- Tailwind CSS + shadcn/ui components
- Biome for formatting + ESLint for linting