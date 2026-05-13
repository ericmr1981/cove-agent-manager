/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'cove-bg': '#0d1117',
        'cove-surface': '#161b22',
        'cove-border': '#30363d',
        'cove-text': '#e6edf3',
        'cove-muted': '#8b949e',
        'cove-accent': '#58a6ff',
        'cove-success': '#3fb950',
        'cove-danger': '#f85149',
        'cove-warning': '#d29922',
      },
    },
  },
  plugins: [],
}
