# Production Security Implementation Checklist

This checklist provides step-by-step instructions for implementing security measures before launching the Chat SDK in production.

## Pre-Production Security Setup

### Phase 1: Cloudflare Dashboard Configuration (No Code Changes)

#### 1.1 Rate Limiting Rules

**Rule 1: Guest Account Creation Protection**
- Path: `/api/auth/guest`
- Threshold: 1 request per hour per IP
- Action: Challenge (shows CAPTCHA)
- Characteristics: IP Address

**Rule 2: Authentication Endpoint Protection**
- Path: `/api/auth/*`
- Threshold: 5 requests per hour per IP
- Action: Challenge
- Characteristics: IP Address

**Rule 3: Chat API Protection**
- Path: `/api/chat`
- Threshold: 20 requests per minute per IP
- Action: Block (429 response)
- Characteristics: IP Address

**Rule 4: General API Protection**
- Path: `/api/*`
- Threshold: 100 requests per minute per IP
- Action: Block (429 response)
- Characteristics: IP Address

#### 1.2 Firewall Rules

**Rule 1: Block Suspicious User Agents**
```
(http.request.uri.path contains "/api/" and 
 not http.user_agent contains any {"Mozilla" "Chrome" "Safari" "Edge"})
Action: Block
```

**Rule 2: Require Standard Headers**
```
(http.request.uri.path contains "/api/" and 
 not http.request.headers["accept"] contains any {"application/json" "text/plain" "*/*"})
Action: Challenge
```

**Rule 3: High Threat Score Protection**
```
(cf.threat_score gt 30 and http.request.uri.path contains "/api/")
Action: Challenge
```

#### 1.3 Bot Fight Mode
- Enable: Bot Fight Mode (available in Pro plan)
- This automatically challenges suspicious bot traffic

#### 1.4 Security Headers (Transform Rules)
Add these response headers to all requests:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

### Phase 2: Minimal Code Changes

#### 2.1 Turnstile Integration for Guest Creation

**Step 1: Install Turnstile Package**
```bash
pnpm add @marsidev/react-turnstile
```

**Step 2: Update Guest Route (`/app/(auth)/api/auth/guest/route.ts`)**
Add Turnstile verification before creating guest account:

```typescript
// Add to existing imports
const TURNSTILE_SECRET = process.env.TURNSTILE_SECRET_KEY;

// Add verification function
async function verifyTurnstile(token: string): Promise<boolean> {
  const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      secret: TURNSTILE_SECRET!,
      response: token,
    }),
  });
  const data = await response.json();
  return data.success;
}

// Modify GET handler to check for Turnstile token
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const turnstileToken = searchParams.get('turnstile');
  
  if (!turnstileToken || !(await verifyTurnstile(turnstileToken))) {
    return NextResponse.json({ error: 'Invalid captcha' }, { status: 403 });
  }
  
  // ... rest of existing code
}
```

**Step 3: Add Device Fingerprint Cookie**
In the same guest route, add a secure cookie:

```typescript
// After successful guest creation
const response = await signIn('guest', { redirect: false });
response.cookies.set('device_fp', generateUUID(), {
  httpOnly: true,
  secure: true,
  sameSite: 'strict',
  maxAge: 60 * 60 * 24 * 365, // 1 year
});
```

#### 2.2 Environment Variables to Add
```env
# Turnstile (already added)
TURNSTILE_SITE_KEY=your_site_key
TURNSTILE_SECRET_KEY=your_secret_key

# Optional: Feature flags
ENABLE_GUEST_CAPTCHA=true
ENABLE_DEVICE_TRACKING=true
```

### Phase 3: Testing Procedures

#### 3.1 Rate Limit Testing
1. Use a tool like `curl` or Postman to test limits:
   ```bash
   # Test guest creation limit (should block after 1)
   for i in {1..5}; do
     curl -X GET https://yourdomain.com/api/auth/guest
     sleep 1
   done
   ```

2. Verify 429 responses and challenge pages appear

#### 3.2 Turnstile Testing
1. Test with valid token → Guest account created
2. Test with invalid token → 403 error
3. Test with no token → 403 error

#### 3.3 Database Rate Limit Testing
1. Create a guest account
2. Send 3 messages quickly → 4th should fail
3. Wait 1 minute → Should work again
4. Send 20 messages throughout the day → 21st should fail

### Phase 4: Monitoring Setup

#### 4.1 Cloudflare Analytics
- Monitor: Rate limit triggers
- Monitor: Bot score distribution
- Monitor: Threat score patterns

#### 4.2 Application Metrics
- Track: Guest account creation rate
- Track: Message sending patterns
- Track: Failed authentication attempts

#### 4.3 Alerts to Configure
- Alert: >100 guest accounts created per hour
- Alert: >1000 rate limit blocks per hour
- Alert: Sudden spike in 429 responses

### Phase 5: Production Deployment

#### 5.1 Pre-Launch Checklist
- [ ] All Cloudflare rules configured and tested
- [ ] Turnstile integration deployed and tested
- [ ] Environment variables set in production
- [ ] Rate limits verified in staging environment
- [ ] Monitoring dashboards configured
- [ ] Alert thresholds set

#### 5.2 Launch Day
1. Enable all Cloudflare rules
2. Monitor metrics closely for first 24 hours
3. Be ready to adjust rate limits if too restrictive

#### 5.3 Post-Launch Optimization
- Review metrics after 1 week
- Adjust rate limits based on real usage
- Consider additional protections if abuse detected

## Rollback Plan

If security measures cause issues:

1. **Quick Fixes:**
   - Increase rate limits in Cloudflare dashboard
   - Temporarily disable Turnstile via env variable
   - Switch firewall rules from "Block" to "Log"

2. **Emergency Bypass:**
   - Create page rule to bypass security for specific IPs
   - Have bypass codes ready for important users

## Security Escalation Path

If abuse is detected despite these measures:

1. **Level 1:** Reduce guest message limits further
2. **Level 2:** Require email verification for guests
3. **Level 3:** Disable guest accounts temporarily
4. **Level 4:** Enable Cloudflare Under Attack Mode

---

**Remember:** It's better to start with slightly restrictive limits and relax them based on legitimate usage patterns than to start too permissive and try to restrict after abuse begins.