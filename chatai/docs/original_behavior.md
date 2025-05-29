# Original Behavior Documentation

This document captures the original behavior and implementation details of the Chat SDK, particularly focusing on areas that may need modification or improvement in the future.

## Guest User System Analysis

### Current Implementation (As of Analysis Date)

The Chat SDK implements a **permanent guest user system** that differs significantly from typical "temporary guest" implementations found in most applications.

### Key Characteristics

#### 1. Permanent Database Storage
- **Guest users are real database records** stored permanently in the `User` table
- Each guest receives a unique email format: `guest-{timestamp}` (e.g., `guest-1703123456789`)
- Guests have actual hashed passwords generated and stored in the database
- **No cleanup mechanism exists** - guest users persist indefinitely

#### 2. Session Persistence Mechanism
- Uses **NextAuth JWT tokens** stored in HTTP-only secure cookies
- Cookies survive browser restarts (not session-only)
- Middleware validates existing tokens and restores guest sessions
- Full session restoration occurs across browser/server restarts

#### 3. Complete Feature Parity
Guest users have identical capabilities to registered users:
- ✅ Create and own `Chat` records via `userId` foreign key
- ✅ Create `Document` artifacts (text, code, image, sheet)
- ✅ Vote on messages  
- ✅ Full chat history persistence
- ✅ Share conversations (with visibility controls)
- ✅ All data persists permanently in PostgreSQL

### Technical Implementation Details

#### Guest User Creation Flow
**File: `lib/db/queries.ts` (lines 66-81)**
```typescript
export async function createGuestUser() {
  const email = `guest-${Date.now()}`;
  const password = generateHashedPassword(generateUUID());

  try {
    return await db.insert(user).values({ email, password }).returning({
      id: user.id,
      email: user.email,
    });
  } catch (error) {
    throw new ChatSDKError(
      'bad_request:database',
      'Failed to create guest user',
    );
  }
}
```

#### Authentication Configuration
**File: `app/(auth)/auth.ts` (lines 65-72)**
```typescript
Credentials({
  id: 'guest',
  credentials: {},
  async authorize() {
    const [guestUser] = await createGuestUser();
    return { ...guestUser, type: 'guest' };
  },
}),
```

#### Middleware Routing Logic
**File: `middleware.ts` (lines 26-32)**
```typescript
if (!token) {
  const redirectUrl = encodeURIComponent(request.url);
  
  return NextResponse.redirect(
    new URL(`/api/auth/guest?redirectUrl=${redirectUrl}`, request.url),
  );
}
```

#### Guest Route Handler
**File: `app/(auth)/api/auth/guest/route.ts`**
- Checks for existing tokens
- Creates new guest session if none exists
- Redirects to appropriate destination
- Uses NextAuth's `signIn('guest')` method

### Database Schema Impact

#### User Table Structure
Guest users are stored identically to regular users:
- Same `User` table schema
- Unique UUID primary keys  
- Email field with `guest-{timestamp}` pattern
- Hashed password storage
- No differentiation at database level

#### Relational Data
- **Chats**: Owned via `userId` foreign key
- **Documents**: Created and versioned by guest users
- **Messages**: Full messaging capabilities
- **Votes**: Can vote on message quality
- **Suggestions**: Can participate in collaborative editing

### User Experience Implications

#### Benefits
- **Seamless onboarding** - no registration friction
- **No data loss** - conversations persist across sessions
- **Full feature access** - identical to registered users
- **Easy conversion** - can upgrade to full account later
- **Demo-friendly** - perfect for showcasing capabilities

#### Potential Issues
- **Database growth** - unlimited guest user creation
- **Storage costs** - permanent data retention without cleanup
- **Privacy concerns** - permanent storage without explicit consent
- **Resource usage** - abandoned guest accounts consuming space
- **Analytics complexity** - difficulty distinguishing active vs abandoned guests

### Comparison with Typical Guest Implementations

#### Standard Guest Systems Usually Implement:
- ❌ Temporary in-memory storage
- ❌ Session-only data that expires on browser close
- ❌ Limited feature access (read-only or basic functionality)
- ❌ Data cleanup on session expiration
- ❌ Explicit prompts to register for persistence

#### Chat SDK Guest System:
- ✅ **Permanent database storage**
- ✅ **Cross-session persistence via cookies**
- ✅ **Full feature parity with registered users**
- ✅ **No automatic cleanup**
- ✅ **Silent permanent account creation**

### Future Modification Considerations

#### Potential Improvements
1. **Guest User Cleanup**
   - Implement TTL (time-to-live) for inactive guest accounts
   - Add database cleanup jobs for abandoned guests
   - Consider data retention policies

2. **Enhanced Guest Management**
   - Add guest user analytics and monitoring
   - Implement guest-to-registered user conversion tracking
   - Consider guest user limitations vs full users

3. **Privacy and Consent**
   - Add explicit consent for data persistence
   - Implement guest data deletion capabilities
   - Consider GDPR compliance for guest data

4. **Performance Optimization**
   - Monitor database growth from guest users
   - Implement archival strategies for old guest data
   - Consider separate storage tiers for guest vs registered users

#### Architectural Alternatives
1. **Session-Based Guests**
   - Store guest data in Redis/memory with TTL
   - Prompt for registration before data loss
   - Implement explicit conversion flow

2. **Hybrid Approach**
   - Limited-time persistence (e.g., 30 days)
   - Automatic cleanup with user notification
   - Progressive feature unlocking

3. **Explicit Guest Mode**
   - Clear indication of guest status
   - Explicit prompts about data persistence
   - User-controlled data retention

### Configuration Files Involved

#### Core Authentication
- `app/(auth)/auth.ts` - NextAuth configuration with guest provider
- `app/(auth)/auth.config.ts` - Auth configuration settings
- `middleware.ts` - Request routing and session validation

#### Database Layer
- `lib/db/schema.ts` - User table schema definition
- `lib/db/queries.ts` - Guest user creation logic
- `lib/db/migrations/` - Database schema evolution

#### API Routes
- `app/(auth)/api/auth/guest/route.ts` - Guest authentication endpoint
- `app/(auth)/api/auth/[...nextauth]/route.ts` - NextAuth API handler

#### Frontend Components
- `components/auth-form.tsx` - Authentication UI components
- `components/sidebar-user-nav.tsx` - User navigation for guests

### Security Considerations

#### Current Security Model
- Guest users have same database access patterns as registered users
- Session tokens secured via HTTP-only cookies
- Guest identification via email regex pattern: `/^guest-\d+$/`
- No rate limiting specific to guest users

#### Potential Security Improvements
- Implement guest-specific rate limiting
- Add guest user activity monitoring
- Consider guest data encryption or separation
- Implement guest session timeout policies

---

**Note**: This documentation reflects the system state as analyzed. Any modifications to guest user behavior should reference this baseline implementation to understand the full scope of changes required.