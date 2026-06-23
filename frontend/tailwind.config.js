/** @type {import('tailwindcss').Config} */
const token = (v) => `rgb(var(${v}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Semantic tokens — flip in dark mode via CSS variables (see index.css)
        canvas: token("--canvas"),
        surface: token("--surface"),
        elevated: token("--elevated"),
        muted: token("--muted"),
        line: token("--line"),
        ink: {
          DEFAULT: token("--ink"),
          soft: token("--ink-soft"),
          muted: token("--ink-muted"),
        },
        // Primary brand — refined indigo, full tonal scale
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
        },
        // Amber accent for highlights / success-rate / CTAs
        accent: {
          50: "#fffbeb",
          100: "#fef3c7",
          400: "#fbbf24",
          500: "#f59e0b",
          600: "#d97706",
        },
      },
      fontFamily: {
        sans: [
          "Inter var",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.125rem",
      },
      boxShadow: {
        // Soft, layered elevation (Linear/Stripe-style) instead of harsh shadows
        xs: "0 1px 2px 0 rgb(15 23 42 / 0.04)",
        soft: "0 1px 3px 0 rgb(15 23 42 / 0.06), 0 1px 2px -1px rgb(15 23 42 / 0.06)",
        card: "0 2px 8px -2px rgb(15 23 42 / 0.06), 0 1px 2px -1px rgb(15 23 42 / 0.04)",
        lift: "0 12px 28px -8px rgb(79 70 229 / 0.18), 0 4px 10px -4px rgb(15 23 42 / 0.08)",
        focus: "0 0 0 3px rgb(99 102 241 / 0.25)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          from: { opacity: "0", transform: "scale(0.97)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.3s ease-out both",
        "fade-up": "fade-up 0.35s cubic-bezier(0.16,1,0.3,1) both",
        "scale-in": "scale-in 0.2s ease-out both",
      },
    },
  },
  plugins: [],
};
