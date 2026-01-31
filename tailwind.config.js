/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        neon: {
          blue: "#00F3FF",
          cyan: "#00E5FF",
          purple: "#BC00FF",
        },
        glass: {
          DEFAULT: "rgba(255, 255, 255, 0.1)",
          dark: "rgba(0, 0, 0, 0.3)",
        }
      },
      backgroundImage: {
        "liquid-gradient": "linear-gradient(135deg, rgba(0, 243, 255, 0.15) 0%, rgba(188, 0, 255, 0.15) 100%)",
        "mesh-gradient": "radial-gradient(at 0% 0%, rgba(0, 243, 255, 0.15) 0, transparent 50%), radial-gradient(at 100% 100%, rgba(188, 0, 255, 0.15) 0, transparent 50%)",
      },
      backdropBlur: {
        xs: "2px",
      },
      animation: {
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        }
      }
    },
  },
  plugins: [],
};
