/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Agromaq brand colors - customize these based on actual website
        'agromaq-green': {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a', // Primary green
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
        'agromaq-yellow': {
          50: '#fefce8',
          100: '#fef9c3',
          200: '#fef08a',
          300: '#fde047',
          400: '#facc15',
          500: '#eab308', // Primary yellow
          600: '#ca8a04',
          700: '#a16207',
          800: '#854d0e',
          900: '#713f12',
        }
      },
      fontSize: {
        'base': '20px', // tamaño base más grande
        'lg': '1.5rem', // 24px
        'xl': '2rem',   // 32px
        '2xl': '2.5rem', // 40px
        '3xl': '3rem',   // 48px
        '4xl': '3.5rem', // 56px
        '5xl': '4rem',   // 64px
      }
    },
  },
  plugins: [],
};