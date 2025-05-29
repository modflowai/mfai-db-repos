import { signIn } from '@/app/(auth)/auth';
import { isDevelopmentEnvironment } from '@/lib/constants';
import { getToken } from 'next-auth/jwt';
import { NextResponse } from 'next/server';

const TURNSTILE_SECRET = process.env.TURNSTILE_SECRET_KEY;
const ENABLE_GUEST_AUTH = process.env.NEXT_PUBLIC_ENABLE_GUEST_AUTH !== 'false';

async function verifyTurnstile(token: string): Promise<boolean> {
  if (!TURNSTILE_SECRET) {
    console.error('TURNSTILE_SECRET_KEY not configured');
    return false;
  }

  try {
    const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        secret: TURNSTILE_SECRET,
        response: token,
      }),
    });
    
    const data = await response.json();
    return data.success === true;
  } catch (error) {
    console.error('Turnstile verification error:', error);
    return false;
  }
}

export async function GET(request: Request) {
  // Check if guest auth is enabled
  if (!ENABLE_GUEST_AUTH) {
    return NextResponse.json({ error: 'Guest authentication is disabled' }, { status: 404 });
  }

  const { searchParams } = new URL(request.url);
  const redirectUrl = searchParams.get('redirectUrl') || '/';
  const turnstileToken = searchParams.get('turnstile');

  // Check if user already has a token
  const existingToken = await getToken({
    req: request,
    secret: process.env.AUTH_SECRET,
    secureCookie: !isDevelopmentEnvironment,
  });

  if (existingToken) {
    return NextResponse.redirect(new URL('/', request.url));
  }

  // Verify Turnstile token
  if (!turnstileToken) {
    return NextResponse.json({ error: 'Turnstile token required' }, { status: 400 });
  }

  const isValid = await verifyTurnstile(turnstileToken);
  if (!isValid) {
    return NextResponse.json({ error: 'Invalid captcha' }, { status: 403 });
  }

  // Create guest account and sign in
  return signIn('guest', { redirect: true, redirectTo: redirectUrl });
}
