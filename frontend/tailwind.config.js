/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        neo: {
          bg: '#FAF7F2',
          canvas: '#F4F0EA',
          dark: '#121212',
          yellow: '#FFE600',
          'yellow-light': '#FFF480',
          lime: '#CCFF00',
          'lime-light': '#E5FF80',
          cyan: '#00F0FF',
          'cyan-light': '#80F8FF',
          pink: '#FF3399',
          'pink-light': '#FF80BF',
          orange: '#FF6B00',
          'orange-light': '#FFA34D',
          purple: '#B388FF',
          'purple-light': '#D6BFFF',
          cream: '#FFFDF5',
          paper: '#FFFFFF',
        },
      },
      boxShadow: {
        'neo-sm': '2px 2px 0px 0px #000000',
        'neo': '4px 4px 0px 0px #000000',
        'neo-lg': '6px 6px 0px 0px #000000',
        'neo-xl': '8px 8px 0px 0px #000000',
        'neo-white': '4px 4px 0px 0px #FFFFFF',
        'neo-yellow': '4px 4px 0px 0px #FFE600',
        'neo-cyan': '4px 4px 0px 0px #00F0FF',
        'neo-pink': '4px 4px 0px 0px #FF3399',
      },
      fontFamily: {
        display: ['"Impact"', '"Arial Black"', '"PingFang SC"', 'sans-serif'],
        mono: ['"Courier New"', 'Courier', 'monospace', 'ui-monospace'],
      },
    },
  },
  plugins: [],
}
