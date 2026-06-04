tailwind.config = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // DJI Mavic Pro-inspired palette
        base: "#0F1419",
        surface: "#1A2332",
        panel: "#1A2332",
        accent: "#00E5FF",
        accentSoft: "#4CAF50",
        success: "#10B981",
        warning: "#F59E0B",
        warningSoft: "#FBBF24",
        critical: "#EF4444",
        maintenance: "#A78BFA",
        main: "#FFFFFF",
        muted: "#9CA3AF",
        mutedSoft: "#6B7280",
        borderPrimary: "#2D3E52",
        borderSecondary: "#3F5268",
        // aliases used in templates
        baseBg: "#0F1419",
        surfaceBg: "#1A2332",
        panelBg: "#1A2332",
      },
      borderRadius: {
        lgpanel: "0.5rem",
        xllarge: "0.75rem",
        button: "0.25rem",
      },
      boxShadow: {
        "soft-3xl": "0 10px 30px rgba(0,0,0,0.6)",
        "panel": "0 4px 12px rgba(0,0,0,0.4)",
      },
      fontFamily: {
        heading: ["Inter", "SF Pro Display", "Segoe UI", "sans-serif"],
        body: ["Inter", "SF Pro Display", "Segoe UI", "sans-serif"],
        sans: ["Inter", "SF Pro Display", "Segoe UI", "sans-serif"],
        mono: ["Courier New", "SF Mono", "Consolas", "monospace"],
      },
    },
  },
};
