'use client';

import { useEffect, useState } from 'react';
import { AlertDialog, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from './ui/alert-dialog';
import { Button } from './ui/button';
import { Clock, Calendar, Zap, Crown } from 'lucide-react';

type RateLimitType = 'minute' | 'daily';

interface RateLimitModalProps {
  isOpen: boolean;
  onClose: () => void;
  type: RateLimitType;
  retryAfterSeconds: number;
  limit: number;
  userRole: 'guest' | 'regular' | 'premium';
  nextTier?: {
    role: 'guest' | 'regular' | 'premium';
    dailyLimit: number;
  } | null;
}

export function RateLimitModal({ 
  isOpen, 
  onClose, 
  type, 
  retryAfterSeconds: initialRetryAfter, 
  limit,
  userRole,
  nextTier
}: RateLimitModalProps) {
  const [retryAfterSeconds, setRetryAfterSeconds] = useState(initialRetryAfter);

  // Update countdown timer
  useEffect(() => {
    if (!isOpen || retryAfterSeconds <= 0) return;

    const interval = setInterval(() => {
      setRetryAfterSeconds(prev => {
        if (prev <= 1) {
          // Use setTimeout to defer the onClose call to avoid state update during render
          setTimeout(onClose, 0);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isOpen, retryAfterSeconds, onClose]);

  // Reset timer when modal opens
  useEffect(() => {
    if (isOpen) {
      setRetryAfterSeconds(initialRetryAfter);
    }
  }, [isOpen, initialRetryAfter]);

  const formatTime = (seconds: number) => {
    if (seconds < 60) {
      return `${seconds} second${seconds !== 1 ? 's' : ''}`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (remainingSeconds === 0) {
      return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
    }
    return `${minutes}m ${remainingSeconds}s`;
  };

  const getIcon = () => {
    if (type === 'minute') {
      return <Clock className="size-6 text-orange-500" />;
    }
    return <Calendar className="size-6 text-red-500" />;
  };

  const getTitle = () => {
    if (type === 'minute') {
      return "Slow down there! ⚡";
    }
    return "Daily limit reached 📅";
  };

  const getDescription = () => {
    if (type === 'minute') {
      return (
        <div className="space-y-3">
          <p>You&apos;re sending messages too quickly. Please take a moment to slow down.</p>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="size-4" />
            <span>You can send another message in <strong className="text-foreground">{formatTime(retryAfterSeconds)}</strong></span>
          </div>
        </div>
      );
    } else {
      return (
        <div className="space-y-4">
          <p>You&apos;ve reached your daily limit of <strong>{limit} messages</strong>.</p>
          {userRole === 'guest' && nextTier && (
            <div className="bg-muted p-3 rounded-lg">
              <div className="flex items-center gap-2 text-sm">
                <Zap className="size-4 text-blue-500" />
                <span className="font-medium">Want more messages?</span>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                Sign in with Google or GitHub to get {nextTier.dailyLimit} messages per day!
              </p>
            </div>
          )}
          {userRole === 'regular' && (
            <div className="bg-muted p-3 rounded-lg">
              <div className="flex items-center gap-2 text-sm">
                <Crown className="size-4 text-amber-500" />
                <span className="font-medium">Want higher limits?</span>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                Premium plans with higher limits will be available in the future!
              </p>
            </div>
          )}
        </div>
      );
    }
  };

  const getFooterButtons = () => {
    if (type === 'minute') {
      return (
        <Button onClick={onClose} className="w-full">
          Got it ({retryAfterSeconds}s)
        </Button>
      );
    } else {
      return (
        <div className="flex gap-2 w-full">
          <Button variant="outline" onClick={onClose} className="flex-1">
            Close
          </Button>
          {userRole === 'guest' && nextTier && (
            <Button 
              className="flex-1"
              onClick={() => {
                onClose();
                window.location.href = '/login';
              }}
            >
              Get {nextTier.dailyLimit} Messages/Day
            </Button>
          )}
          {userRole === 'regular' && (
            <Button 
              className="flex-1"
              onClick={() => {
                onClose();
                // TODO: Implement request more credits functionality
                alert('Request for more credits - Coming soon!');
              }}
            >
              Ask for more credits
            </Button>
          )}
        </div>
      );
    }
  };

  return (
    <AlertDialog open={isOpen} onOpenChange={onClose}>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          <div className="flex items-center gap-3">
            {getIcon()}
            <AlertDialogTitle>{getTitle()}</AlertDialogTitle>
          </div>
          <AlertDialogDescription asChild>
            <div>
              {getDescription()}
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          {getFooterButtons()}
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}