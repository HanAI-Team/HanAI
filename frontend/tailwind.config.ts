import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
      sans: ['Pretendard', '-apple-system', 'sans-serif'],
      serif: ['DM Serif Display', 'serif'],
      },
      colors: {
        orange: '#EF6600',
        brown: '#68413E',
      }
    },
  },
  plugins: [],
}

export default config
