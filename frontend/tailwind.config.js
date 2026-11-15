/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        mars: {
          50: '#fdf4f0',
          100: '#fbe8df',
          200: '#f6d1bf',
          300: '#eeae92',
          400: '#e38260',
          500: '#d75d36',
          600: '#c1440e',
          700: '#a3340e',
          800: '#832b12',
          900: '#6d2713',
          950: '#3c1106',
        },
        space: {
          950: '#07090e',
          900: '#0b0f17',
          850: '#101622',
          800: '#161e2e',
          750: '#1d273b',
          700: '#26334d',
          600: '#374768',
        },
        telemetry: {
          cyan: '#38bdf8',
          emerald: '#10b981',
          amber: '#f59e0b',
          rose: '#f43f5e',
          purple: '#a855f7',
        }
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', '"Liberation Mono"', '"Courier New"', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'ping-slow': 'ping 2.5s cubic-bezier(0, 0, 0.2, 1) infinite',
      }
    },
  },
  plugins: [],
}
