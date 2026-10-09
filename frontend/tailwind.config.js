/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        aqi: {
          good: '#2ca02c',
          satisfactory: '#7ac143',
          moderate: '#ffbf00',
          poor: '#ff7f0e',
          veryPoor: '#d62728',
          severe: '#8b0000',
        },
        ink: '#1a2b3c',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
