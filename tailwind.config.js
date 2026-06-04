module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js",
  ],
  safelist: [
    "bg-teal-500",
    "shadow-[0_0_8px_rgba(20,184,166,0.45)]",
    "max-[820px]:translate-y-0",
    "max-[820px]:opacity-100",
    "max-[820px]:pointer-events-auto",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["DM Sans", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
};
