import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['var(--font-jetbrains-mono)', 'JetBrains Mono', 'Consolas', 'monospace'],
      },
      spacing: {
        '0.5': '2px',   // 8px grid: 2px
        '1': '4px',     // 8px grid: 4px  
        '1.5': '6px',   // 8px grid: 6px
        '2': '8px',     // 8px grid: 8px (base unit)
        '2.5': '10px',  // 8px grid: 10px
        '3': '12px',    // 8px grid: 12px
        '3.5': '14px',  // 8px grid: 14px
        '4': '16px',    // 8px grid: 16px (2 units)
        '5': '20px',    // 8px grid: 20px
        '6': '24px',    // 8px grid: 24px (3 units)
        '7': '28px',    // 8px grid: 28px
        '8': '32px',    // 8px grid: 32px (4 units)
        '9': '36px',    // 8px grid: 36px
        '10': '40px',   // 8px grid: 40px (5 units)
        '11': '44px',   // 8px grid: 44px
        '12': '48px',   // 8px grid: 48px (6 units)
        '14': '56px',   // 8px grid: 56px (7 units)
        '16': '64px',   // 8px grid: 64px (8 units)
        '20': '80px',   // 8px grid: 80px (10 units)
        '24': '96px',   // 8px grid: 96px (12 units)
        '28': '112px',  // 8px grid: 112px (14 units)
        '32': '128px',  // 8px grid: 128px (16 units)
        '36': '144px',  // 8px grid: 144px (18 units)
        '40': '160px',  // 8px grid: 160px (20 units)
        '44': '176px',  // 8px grid: 176px (22 units)
        '48': '192px',  // 8px grid: 192px (24 units)
        '52': '208px',  // 8px grid: 208px (26 units)
        '56': '224px',  // 8px grid: 224px (28 units)
        '60': '240px',  // 8px grid: 240px (30 units)
        '64': '256px',  // 8px grid: 256px (32 units)
        '72': '288px',  // 8px grid: 288px (36 units)
        '80': '320px',  // 8px grid: 320px (40 units)
        '96': '384px',  // 8px grid: 384px (48 units)
      },
      screens: {
        'toast-mobile': '600px',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        chart: {
          '1': 'hsl(var(--chart-1))',
          '2': 'hsl(var(--chart-2))',
          '3': 'hsl(var(--chart-3))',
          '4': 'hsl(var(--chart-4))',
          '5': 'hsl(var(--chart-5))',
        },
        sidebar: {
          DEFAULT: 'hsl(var(--sidebar-background))',
          foreground: 'hsl(var(--sidebar-foreground))',
          primary: 'hsl(var(--sidebar-primary))',
          'primary-foreground': 'hsl(var(--sidebar-primary-foreground))',
          accent: 'hsl(var(--sidebar-accent))',
          'accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
          border: 'hsl(var(--sidebar-border))',
          ring: 'hsl(var(--sidebar-ring))',
        },
      },
    },
  },
  plugins: [require('tailwindcss-animate'), require('@tailwindcss/typography')],
};
export default config;
