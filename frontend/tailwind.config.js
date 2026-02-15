/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#1a1a1a',
        secondary: '#2d2d2d',
        dark: '#1a1a1a',
        light: '#ffffff',
        border: '#404040',
        surface: '#2d2d2d',
        'surface-light': '#3a3a3a',
        'text-primary': '#ffffff',
        'text-secondary': '#808080',
        'text-tertiary': '#666666',
        hover: '#3a3a3a',
        error: '#ef4444',
      },
    },
  },
  plugins: [],
}
