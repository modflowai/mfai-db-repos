'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Turnstile } from '@marsidev/react-turnstile';
import { Button } from '@/components/ui/button';
import { LoaderIcon } from '@/components/icons';
import { cn } from '@/lib/utils';

interface GuestSignInButtonProps {
  className?: string;
  children?: React.ReactNode;
}

export function GuestSignInButton({ 
  className, 
  children = 'Continue as Guest' 
}: GuestSignInButtonProps) {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [showTurnstile, setShowTurnstile] = useState(false);

  const handleGuestSignIn = async () => {
    if (!turnstileToken) {
      setShowTurnstile(true);
      return;
    }

    setIsLoading(true);

    try {
      const redirectUrl = new URLSearchParams(window.location.search).get('redirectUrl') || '/';
      const response = await fetch(`/api/auth/guest?turnstile=${turnstileToken}&redirectUrl=${encodeURIComponent(redirectUrl)}`);
      
      if (!response.ok) {
        throw new Error('Failed to create guest account');
      }

      // The guest route will handle the redirect
      window.location.href = redirectUrl;
    } catch (error) {
      console.error('Guest sign-in error:', error);
      // Reset to allow retry
      setTurnstileToken(null);
      setShowTurnstile(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTurnstileSuccess = async (token: string) => {
    setTurnstileToken(token);
    setIsLoading(true);

    try {
      const redirectUrl = new URLSearchParams(window.location.search).get('redirectUrl') || '/';
      const response = await fetch(`/api/auth/guest?turnstile=${token}&redirectUrl=${encodeURIComponent(redirectUrl)}`);
      
      if (!response.ok) {
        throw new Error('Failed to create guest account');
      }

      // The guest route will handle the redirect
      window.location.href = redirectUrl;
    } catch (error) {
      console.error('Guest sign-in error:', error);
      // Reset to allow retry
      setTurnstileToken(null);
      setShowTurnstile(false);
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full">
      {!showTurnstile ? (
        <Button
          variant="outline"
          className={cn('w-full', className)}
          onClick={handleGuestSignIn}
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <span className="mr-2 animate-spin">
                <LoaderIcon />
              </span>
              Creating guest session...
            </>
          ) : (
            children
          )}
        </Button>
      ) : (
        <div className="flex flex-col items-center gap-4">
          <p className="text-sm text-muted-foreground">Please verify you&apos;re human</p>
          {process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY ? (
            <Turnstile
              siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY}
              onSuccess={handleTurnstileSuccess}
              onError={(error) => {
                console.error('Turnstile error:', error);
                setShowTurnstile(false);
                setTurnstileToken(null);
              }}
              onExpire={() => {
                setTurnstileToken(null);
              }}
            />
          ) : (
            <p className="text-sm text-red-500">
              Turnstile not configured. Please add NEXT_PUBLIC_TURNSTILE_SITE_KEY to your environment.
            </p>
          )}
        </div>
      )}
    </div>
  );
}