/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        sand: '#f8f4ec',
        ink: '#201713',
        muted: '#6d6258',
        copper: '#9f4b1d',
        copperSoft: '#ead7c5',
        line: 'rgba(74, 55, 40, 0.12)',
      },
      boxShadow: {
        panel: '0 24px 60px rgba(80, 58, 40, 0.12)',
      },
      fontFamily: {
        sans: ['Space Grotesk', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      backgroundImage: {
        parchment: 'radial-gradient(circle at 12% 14%, rgba(255, 177, 66, 0.16), transparent 26%), radial-gradient(circle at 88% 82%, rgba(159, 75, 29, 0.12), transparent 24%), linear-gradient(135deg, #f8f4ec, #efe3d1)',
      },
    },
  },
  plugins: [],
};
