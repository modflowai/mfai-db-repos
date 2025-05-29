'use client';

import React from 'react';
import { 
  LoadingText, 
  LoadingTextSubtle,
  LoadingTextDramatic,
  EpicLogoLoader, 
  LoadingMessage, 
  TypingIndicator, 
  LoadingSpinner,
  ChatLoadingState,
  SidebarLoadingState,
  FullPageLoadingState 
} from './loading-animations';
import { TextShimmerWave } from './text-shimmer-wave';

export function LoadingDemo() {
  return (
    <div className="p-8 space-y-12 bg-background min-h-screen">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8 text-center">
          🚀 MODFLOW-AI Loading Animations Demo
        </h1>
        
        {/* Text Shimmer Effects */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">✨ 3D Text Shimmer Wave Effects</h2>
          <div className="bg-card p-6 rounded-lg border space-y-6">
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-muted-foreground">Standard Loading Text</h3>
              <LoadingText text="MODFLOW-AI is analyzing your data..." className="text-lg" />
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-muted-foreground">Subtle Variant (for smaller UI)</h3>
              <LoadingTextSubtle text="Processing groundwater flow models..." className="text-sm" />
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-muted-foreground">Dramatic Variant (for important actions)</h3>
              <LoadingTextDramatic text="Initializing Advanced Simulation..." className="text-lg" />
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-muted-foreground">Custom Configuration</h3>
              <TextShimmerWave
                duration={1.5}
                spread={0.5}
                zDistance={15}
                scaleDistance={1.15}
                rotateYDistance={12}
                className="text-base font-semibold"
              >
                Building mesh topology...
              </TextShimmerWave>
            </div>
          </div>
        </section>

        {/* Epic Logo Animations */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">⚡ Epic Logo Loading Animations</h2>
          <div className="bg-card p-6 rounded-lg border">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 items-center justify-items-center">
              <div className="text-center space-y-2">
                <EpicLogoLoader size={32} />
                <p className="text-xs text-muted-foreground">Small (32px)</p>
              </div>
              <div className="text-center space-y-2">
                <EpicLogoLoader size={48} />
                <p className="text-xs text-muted-foreground">Medium (48px)</p>
              </div>
              <div className="text-center space-y-2">
                <EpicLogoLoader size={64} />
                <p className="text-xs text-muted-foreground">Large (64px)</p>
              </div>
              <div className="text-center space-y-2">
                <EpicLogoLoader size={80} showParticles={false} />
                <p className="text-xs text-muted-foreground">No Particles</p>
              </div>
            </div>
          </div>
        </section>

        {/* Combined Loading States */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">🎯 Combined Loading Components</h2>
          <div className="bg-card p-6 rounded-lg border space-y-6">
            <LoadingMessage message="Initializing MODFLOW simulation..." />
            <TypingIndicator />
            <LoadingSpinner variant="logo" text="Loading model data..." />
            <LoadingSpinner variant="dots" text="Processing..." />
            <LoadingSpinner variant="shimmer" text="Almost ready..." />
          </div>
        </section>

        {/* Context-Specific Loading States */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">📱 Context-Specific Loading States</h2>
          
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-medium mb-2">Chat Loading State</h3>
              <ChatLoadingState />
            </div>
            
            <div>
              <h3 className="text-sm font-medium mb-2">Sidebar Loading State</h3>
              <div className="bg-sidebar-background p-4 rounded-lg border max-w-xs">
                <SidebarLoadingState />
              </div>
            </div>
          </div>
        </section>

        {/* Performance Info */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">⚙️ Performance Features</h2>
          <div className="bg-card p-6 rounded-lg border">
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>✅ <strong>3D Text Animations:</strong> Sophisticated per-character animations with depth, rotation, and scaling</li>
              <li>✅ <strong>GPU Accelerated:</strong> Uses CSS transforms and filters for smooth 60fps animations</li>
              <li>✅ <strong>Reduced Motion Support:</strong> Respects prefers-reduced-motion accessibility setting</li>
              <li>✅ <strong>Brand-Appropriate:</strong> Logo never spins - maintains professional appearance</li>
              <li>✅ <strong>Blue Theme Integration:</strong> Seamlessly matches MODFLOW-AI brand colors</li>
              <li>✅ <strong>Modular Design:</strong> Individual components can be used independently</li>
              <li>✅ <strong>Framer Motion Powered:</strong> Leverages industry-standard animation library</li>
            </ul>
          </div>
        </section>

        {/* Full Page Demo Button */}
        <section className="text-center">
          <button 
            onClick={() => {
              const demo = document.createElement('div');
              demo.innerHTML = '<div id="full-page-demo"></div>';
              document.body.appendChild(demo);
              
              const DemoComponent = () => React.createElement(FullPageLoadingState);
              setTimeout(() => {
                document.body.removeChild(demo);
              }, 3000);
            }}
            className="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            🌟 Preview Full Page Loading (3s demo)
          </button>
        </section>
      </div>
    </div>
  );
}