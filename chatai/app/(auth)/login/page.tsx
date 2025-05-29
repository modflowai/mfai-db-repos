'use client';

import { GoogleSignInButton } from '@/components/google-signin-button';
import { GitHubSignInButton } from '@/components/github-signin-button';
import { GuestSignInButton } from '@/components/guest-signin-button';
import { Turnstile } from '@marsidev/react-turnstile';
import Image from 'next/image';
import { useState } from 'react';

const ENABLE_GUEST_AUTH = process.env.NEXT_PUBLIC_ENABLE_GUEST_AUTH !== 'false';

export default function Page() {
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  return (
    <div className="flex h-dvh w-screen items-start pt-12 md:pt-0 md:items-center justify-center bg-background">
      <div className="relative w-full max-w-md">
        {/* Card with glow effect */}
        <div className="relative overflow-hidden rounded-2xl bg-zinc-950 border border-zinc-800">
          {/* Top glow effect */}
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-zinc-400 to-transparent" />
          <div className="absolute top-0 left-0 right-0 h-20 bg-gradient-to-b from-zinc-400/10 to-transparent" />
          
          <div className="relative flex flex-col gap-8 p-8 sm:p-10">
            {/* Logo with teal glow effect */}
            <div className="flex flex-col items-center justify-center gap-6">
              <div className="relative flex items-center justify-center">
                {/* Background glow */}
                <div className="absolute inset-0">
                  <div className="h-48 w-48 rounded-full bg-white/[0.07] blur-3xl" />
                </div>
                
                {/* Logo without container - just the SVG with glow */}
                <Image
                  src="/600_square_MODFLOWAI_logo.svg"
                  alt="MODFLOW-AI Logo"
                  width={160}
                  height={160}
                  className="relative"
                  style={{
                    filter: 'drop-shadow(0 0 13px rgba(255, 255, 255, 0.3)) drop-shadow(0 0 25px rgba(255, 255, 255, 0.15))',
                  }}
                />
              </div>
              
              <div className="text-center">
                <h3 className="text-2xl font-semibold text-zinc-50">Welcome to MODFLOW-AI</h3>
                <p className="mt-2 text-sm text-zinc-400">
                  Sign in to continue
                </p>
              </div>
            </div>
            
            {/* Cloudflare Turnstile Widget */}
            <div className="flex justify-center">
              {process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY ? (
                <Turnstile
                  siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY}
                  onSuccess={(token) => setTurnstileToken(token)}
                  onError={(error) => {
                    console.error('Turnstile error:', error);
                    setTurnstileToken(null);
                  }}
                  onExpire={() => {
                    setTurnstileToken(null);
                  }}
                  options={{
                    theme: 'dark',
                  }}
                />
              ) : (
                <div className="rounded-lg bg-zinc-800 px-4 py-2 text-xs text-zinc-400">
                  Turnstile verification not configured
                </div>
              )}
            </div>
            
            <div className="flex flex-col gap-4">
              <GoogleSignInButton className="w-full bg-zinc-900 hover:bg-zinc-800 border-zinc-700">
                Sign in with Google
              </GoogleSignInButton>

              <GitHubSignInButton className="w-full bg-zinc-900 hover:bg-zinc-800 border-zinc-700">
                Sign in with GitHub
              </GitHubSignInButton>
              
              {ENABLE_GUEST_AUTH && (
                <>
                  <div className="relative my-4">
                    <div className="absolute inset-0 flex items-center">
                      <span className="w-full border-t border-zinc-800" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                      <span className="bg-zinc-950 px-2 text-zinc-500">
                        Or try it out
                      </span>
                    </div>
                  </div>
                  
                  <GuestSignInButton className="w-full bg-zinc-900 hover:bg-zinc-800 border-zinc-700">
                    Continue as Guest
                  </GuestSignInButton>
                  
                  <p className="text-xs text-center text-zinc-500 mt-4">
                    Guest accounts have limited access. Sign in with Google or GitHub for full features.
                  </p>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}