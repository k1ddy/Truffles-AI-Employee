module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "var(--color-ink)",
        mist: "var(--color-mist)",
        accent: "var(--color-accent)",
        glow: "var(--color-glow)",
      },
      boxShadow: {
        soft: "0 18px 40px rgba(15, 23, 42, 0.18)",
      },
    },
  },
  plugins: [],
};
