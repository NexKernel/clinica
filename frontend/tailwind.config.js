/** @type {import('tailwindcss').Config} */
const brand = (name) => `rgb(var(--brand-${name}) / <alpha-value>)`

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: brand('primary'),
          dark: brand('primary-dark'),
          light: brand('primary-light'),
        },
        accent: brand('accent'),
        background: brand('background'),
        surface: brand('surface'),
        foreground: brand('foreground'),
        muted: brand('muted'),
        border: brand('border'),
        success: brand('success'),
        warning: { DEFAULT: brand('warning'), dark: brand('warning-dark') },
        danger: brand('danger'),
        info: brand('info'),
        chart: {
          1: 'rgb(var(--chart-1) / <alpha-value>)',
          2: 'rgb(var(--chart-2) / <alpha-value>)',
          3: 'rgb(var(--chart-3) / <alpha-value>)',
          4: 'rgb(var(--chart-4) / <alpha-value>)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
      borderRadius: {
        xl: '0.875rem',
        '2xl': '1.125rem',
      },
      boxShadow: {
        card: '0 1px 2px 0 rgb(83 103 100 / 0.04), 0 8px 24px -16px rgb(83 103 100 / 0.18)',
        popover: '0 8px 32px -12px rgb(83 103 100 / 0.28)',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.18s ease-out',
      },
    },
  },
  plugins: [],
}
