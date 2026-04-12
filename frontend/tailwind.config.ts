import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "var(--color-bg-primary)",
          surface: "var(--color-bg-surface)",
          elevated: "var(--color-bg-elevated)",
        },
        border: {
          DEFAULT: "var(--color-border)",
          muted: "var(--color-border-muted)",
        },
        text: {
          primary: "var(--color-text-primary)",
          secondary: "var(--color-text-secondary)",
          muted: "var(--color-text-muted)",
        },
        accent: {
          DEFAULT: "#6366F1",
          hover: "#818CF8",
          muted: "rgba(99, 102, 241, 0.10)",
        },
        status: {
          success: "#22C55E",
          error: "#EF4444",
          warning: "#F59E0B",
        },
      },
      fontFamily: {
        sans: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', '"Fira Code"', "monospace"],
      },
      borderRadius: {
        card: "12px",
        input: "8px",
        pill: "50px",
      },
      boxShadow: {
        accent: "0 4px 24px rgba(99, 102, 241, 0.10)",
        card: "0 2px 12px rgba(0, 0, 0, 0.20)",
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      spacing: {
        sidebar: "240px",
        "right-panel": "320px",
        topbar: "48px",
        "input-area": "80px",
      },
      animation: {
        "progress-indeterminate": "progress-indeterminate 2s ease-in-out infinite",
        "cursor-blink": "cursor-blink 1s step-end infinite",
      },
      keyframes: {
        "progress-indeterminate": {
          "0%": { transform: "translateX(-100%)" },
          "50%": { transform: "translateX(0%)" },
          "100%": { transform: "translateX(100%)" },
        },
        "cursor-blink": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
