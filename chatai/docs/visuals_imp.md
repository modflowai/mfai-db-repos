Transform the MODFLOW-AI chat interface into a visually stunning, modern application with these specific visual enhancements:

### 🌟 Premium Visual Aesthetics:
1. **Glassmorphism Effects**: Add subtle backdrop blur (backdrop-filter: blur(10px)) to panels with semi-transparent backgrounds (rgba(255,255,255,0.05)) and soft border highlights
2. **Gradient Accents**: Implement subtle blue-to-cyan gradients for active elements, buttons, and the MODFLOW-AI logo glow effect
3. **Enhanced Shadows**: Add layered box-shadows with multiple levels (0 4px 6px rgba(0,0,0,0.1), 0 1px 3px rgba(0,0,0,0.08)) for depth perception
4. **Refined Typography**: Use a modern font stack (Inter, SF Pro Display, or similar) with improved letter-spacing and line-height for better readability

### 🎯 Interface Polish:
1. **Smooth Transitions**: Add CSS transitions (transition: all 0.2s ease-in-out) to all interactive elements for fluid interactions
2. **Hover States**: Implement sophisticated hover effects with subtle scale transforms (transform: scale(1.02)) and glow effects
3. **Message Bubbles**: Redesign chat messages with rounded corners (border-radius: 16px), subtle gradients, and improved spacing
4. **Code Block Enhancement**: Style code blocks with better syntax highlighting, rounded corners, and a subtle border glow effect

### 🌈 Color Refinement:
1. **Sophisticated Dark Palette**: Use rich dark grays (#0a0a0a, #1a1a1a, #2a2a2a) instead of pure black for better contrast hierarchy
2. **Blue Accent System**: Implement a cohesive blue color system (#3b82f6, #60a5fa, #93c5fd) for consistency across all interactive elements
3. **Subtle Color Coding**: Add very subtle color hints for different message types without being overwhelming
4. **Border Treatments**: Use gradient borders (border-image: linear-gradient) for premium visual separation

### ✨ Micro-Interactions:
1. **Loading Animations**: Add elegant skeleton loaders and pulse effects for content loading states
2. **Message Animations**: Implement smooth slide-in animations for new messages with staggered timing
3. **Button Interactions**: Add ripple effects and subtle scale animations on button presses
4. **Scroll Indicators**: Style scrollbars with custom designs that match the overall aesthetic

### 🎨 Layout Refinements:
1. **Spacing Harmony**: Implement consistent spacing using a 8px grid system for visual rhythm
2. **Visual Hierarchy**: Enhance contrast between different UI levels using subtle background variations
3. **Icon Consistency**: Ensure all icons have consistent stroke width and styling with subtle hover animations
4. **Input Field Polish**: Style the message input with a modern design, subtle inner shadow, and focus states

### 🌟 Premium Details:
1. **Logo Treatment**: Add a subtle glow effect to the MODFLOW-AI logo with animated breathing effect
2. **Sidebar Enhancement**: Implement a more sophisticated sidebar design with better visual separation
3. **Status Indicators**: Design elegant online/offline and typing indicators with smooth animations
4. **Custom Scrollbars**: Create sleek, minimal scrollbars that complement the dark theme

Focus on creating a cohesive, premium visual experience that feels modern, professional, and polished. Use CSS-in-JS or Tailwind CSS for implementation, ensuring all animations are smooth (60fps) and the interface feels responsive and delightful to use.

The goal is to make the interface visually comparable to premium applications like Linear, Notion, or Vercel's dashboard - sophisticated, clean, and visually engaging without being distracting from the core functionality.


Add a spinning logo loading animation to the MODFLOW-AI chat interface:

1. **Spinning Logo Effect**: When the AI is generating a response, make the MODFLOW-AI logo spin smoothly (360-degree rotation, 2-second duration, infinite loop)

2. **Visual Enhancements**: 
   - Add a subtle blue glow effect around the spinning logo
   - Include a gentle scale pulse (1.0 to 1.1 scale) synchronized with the spin
   - Apply smooth CSS transitions for when the animation starts/stops

3. **Loading Message**: 
   - Display "MODFLOW-AI is thinking..." text next to the spinning logo
   - Add animated dots (...) that fade in and out sequentially
   - Use a semi-transparent dark background with rounded corners

4. **Implementation**: Use CSS animations or Framer Motion for smooth 60fps performance, and trigger the effect when isLoading state is true.

Make it look professional and polished, similar to premium AI chat applications.