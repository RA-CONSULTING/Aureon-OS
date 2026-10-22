/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      backgroundImage: {
        "cosmic-mesh":
          "radial-gradient(circle at 20% 20%, rgba(166,124,82,0.35), transparent 45%), radial-gradient(circle at 80% 30%, rgba(79,107,64,0.28), transparent 55%), radial-gradient(circle at 40% 80%, rgba(217,180,143,0.25), transparent 52%)",
      },
      boxShadow: {
        cosmic: "0 0 80px rgba(140,98,57,0.25)",
        nebula: "0 0 120px rgba(79,107,64,0.22)",
      },
      animation: {
        "cosmic-drift": "cosmic-drift 26s ease-in-out infinite",
        "stellar-pulse": "stellar-pulse 18s ease-in-out infinite",
        "orbital-glow": "orbital-glow 32s linear infinite",
      },
      keyframes: {
        "cosmic-drift": {
          "0%": { transform: "translate3d(-10%, -8%, 0) scale(0.9)" },
          "50%": { transform: "translate3d(12%, 10%, 0) scale(1.08)" },
          "100%": { transform: "translate3d(-10%, -8%, 0) scale(0.9)" },
        },
        "stellar-pulse": {
          "0%, 100%": { opacity: "0.2" },
          "50%": { opacity: "0.75" },
        },
        "orbital-glow": {
          "0%": { transform: "rotate(0deg) scale(1)" },
          "50%": { transform: "rotate(180deg) scale(1.12)" },
          "100%": { transform: "rotate(360deg) scale(1)" },
        },
      },
    },
  },
  plugins: [],
};
