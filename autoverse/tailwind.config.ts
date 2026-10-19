import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#080a0f",
        surface: {
          DEFAULT: "#0f131c",
          50: "#182030",
          100: "#131824",
          200: "#0f131c",
          300: "#0b0e15",
          border: "#1e2638",
          hover: "#1a2235",
        },
        cyan: {
          glow: "#00f0ff",
          DEFAULT: "#00d2ff",
          muted: "rgba(0, 240, 255, 0.15)",
        },
        neon: {
          blue: "#3b82f6",
          cyan: "#00f0ff",
          amber: "#f59e0b",
          green: "#10b981",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        display: ["Cabinet Grotesk", "Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "radial-highlight": "radial-gradient(circle at 50% 0%, rgba(0, 240, 255, 0.12) 0%, transparent 65%)",
        "radial-card": "radial-gradient(circle at 50% 0%, rgba(30, 41, 59, 0.4) 0%, transparent 100%)",
      },
      boxShadow: {
        "cyan-glow": "0 0 25px -5px rgba(0, 240, 255, 0.3)",
        "cyan-glow-lg": "0 0 40px -5px rgba(0, 240, 255, 0.45)",
        "glass": "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
      },
    },
  },
  plugins: [],
};

export default config;
