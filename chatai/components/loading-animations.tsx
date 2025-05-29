'use client';

import React from 'react';
import Image from 'next/image';
import { TextShimmerWave } from './text-shimmer-wave';

interface LoadingTextProps {
  text?: string;
  className?: string;
}

export function LoadingText({ 
  text = "MODFLOW-AI is analyzing...", 
  className = "" 
}: LoadingTextProps) {
  return (
    <TextShimmerWave
      className={`font-medium ${className}`}
      duration={2}
      spread={0.8}
      zDistance={8}
      scaleDistance={1.05}
      rotateYDistance={5}
    >
      {text}
    </TextShimmerWave>
  );
}

// Subtle variant for smaller text
export function LoadingTextSubtle({ 
  text = "Loading...", 
  className = "" 
}: LoadingTextProps) {
  return (
    <TextShimmerWave
      className={`font-normal ${className}`}
      duration={1.5}
      spread={1.2}
      zDistance={4}
      scaleDistance={1.02}
      rotateYDistance={2}
      xDistance={1}
      yDistance={-1}
    >
      {text}
    </TextShimmerWave>
  );
}

// Dramatic variant for important loading states
export function LoadingTextDramatic({ 
  text = "Initializing MODFLOW-AI...", 
  className = "" 
}: LoadingTextProps) {
  return (
    <TextShimmerWave
      className={`font-semibold ${className}`}
      duration={2.5}
      spread={0.6}
      zDistance={12}
      scaleDistance={1.1}
      rotateYDistance={8}
      xDistance={3}
      yDistance={-3}
    >
      {text}
    </TextShimmerWave>
  );
}

interface EpicLogoLoaderProps {
  size?: number;
  showParticles?: boolean;
  className?: string;
}

export function EpicLogoLoader({ 
  size = 32, 
  showParticles = true, 
  className = "" 
}: EpicLogoLoaderProps) {
  return (
    <div className={`logo-elegant-loading ${className}`} style={{ width: size, height: size }}>
      <Image
        src="/600_square_MODFLOWAI_logo.svg"
        alt="MODFLOW-AI Loading"
        width={size}
        height={size}
        className="flex-shrink-0"
        priority
      />
    </div>
  );
}

interface LoadingMessageProps {
  message?: string;
  showLogo?: boolean;
  logoSize?: number;
  className?: string;
}

export function LoadingMessage({ 
  message = "Generating response...", 
  showLogo = true,
  logoSize = 24,
  className = ""
}: LoadingMessageProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {showLogo && (
        <EpicLogoLoader size={logoSize} showParticles={false} />
      )}
      <LoadingText text={message} className="text-sm" />
    </div>
  );
}

interface TypingIndicatorProps {
  className?: string;
}

export function TypingIndicator({ className = "" }: TypingIndicatorProps) {
  return (
    <div className={`loading-dots ${className}`}>
      <div className="loading-dot" />
      <div className="loading-dot" />
      <div className="loading-dot" />
    </div>
  );
}

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'logo' | 'dots' | 'shimmer';
  text?: string;
  className?: string;
}

export function LoadingSpinner({ 
  size = 'md', 
  variant = 'logo',
  text,
  className = ""
}: LoadingSpinnerProps) {
  const sizeMap = {
    sm: 16,
    md: 24,
    lg: 32
  };

  const logoSize = sizeMap[size];

  if (variant === 'logo') {
    return (
      <div className={`flex flex-col items-center gap-3 ${className}`}>
        <EpicLogoLoader size={logoSize} />
        {text && <LoadingText text={text} className="text-xs" />}
      </div>
    );
  }

  if (variant === 'dots') {
    return (
      <div className={`flex flex-col items-center gap-3 ${className}`}>
        <TypingIndicator />
        {text && <LoadingText text={text} className="text-xs" />}
      </div>
    );
  }

  if (variant === 'shimmer') {
    return (
      <div className={`flex items-center justify-center ${className}`}>
        <LoadingText text={text || "Loading..."} />
      </div>
    );
  }

  return null;
}

// Enhanced loading states for different contexts
export function ChatLoadingState() {
  return (
    <div className="flex items-center gap-3 px-4 py-3 mx-4 my-2 rounded-2xl bg-muted/50 backdrop-blur-sm">
      <EpicLogoLoader size={20} />
      <LoadingText text="MODFLOW-AI is thinking..." className="text-sm" />
    </div>
  );
}

export function SidebarLoadingState() {
  return (
    <div className="flex items-center gap-2 px-2 py-1">
      <EpicLogoLoader size={16} />
      <LoadingTextSubtle text="Loading..." className="text-xs" />
    </div>
  );
}

export function FullPageLoadingState() {
  return (
    <div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="flex flex-col items-center gap-4">
        <EpicLogoLoader size={64} />
        <LoadingTextDramatic text="Initializing MODFLOW-AI..." className="text-lg" />
      </div>
    </div>
  );
}