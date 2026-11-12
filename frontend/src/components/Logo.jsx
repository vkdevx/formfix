import React from "react";

/**
 * FormFix Brand Logo
 * Minimal, modern SVG emblem representing document verification, security, and accuracy.
 */
export default function Logo({ size = "md", theme = "light", withTagline = false }) {
  const sizeMap = {
    sm: { icon: 24, font: "text-lg", sub: "text-[10px]" },
    md: { icon: 32, font: "text-xl", sub: "text-xs" },
    lg: { icon: 44, font: "text-2xl", sub: "text-sm" },
    xl: { icon: 56, font: "text-3xl", sub: "text-base" }
  };

  const current = sizeMap[size] || sizeMap.md;
  const isDark = theme === "dark";

  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: "10px", textDecoration: "none" }}>
      {/* SVG Emblem: Document Shield with Precision Verification Check */}
      <svg
        width={current.icon}
        height={current.icon}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ flexShrink: 0 }}
      >
        <defs>
          <linearGradient id="formfix_gradient" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
            <stop stopColor="#2563eb" />
            <stop offset="1" stopColor="#1d4ed8" />
          </linearGradient>
          <filter id="shadow" x="-2" y="-1" width="44" height="44" filterUnits="userSpaceOnUse">
            <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#2563eb" floodOpacity="0.25" />
          </filter>
        </defs>

        {/* Shield Document Base */}
        <path
          d="M8 8C8 5.79086 9.79086 4 12 4H24L32 12V30C32 34.4183 24 37 20 37C16 37 8 34.4183 8 30V8Z"
          fill="url(#formfix_gradient)"
          filter="url(#shadow)"
        />

        {/* Document Fold Accent */}
        <path
          d="M24 4V10C24 11.1046 24.8954 12 26 12H32L24 4Z"
          fill="#93c5fd"
          opacity="0.9"
        />

        {/* Verification Checkmark */}
        <path
          d="M14 21L18 25L26 17"
          stroke="#ffffff"
          strokeWidth="2.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>

      {/* Typography */}
      <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1 }}>
        <div style={{
          fontWeight: 800,
          letterSpacing: "-0.03em",
          fontFamily: "'Inter', sans-serif",
          fontSize: size === "sm" ? "1.15rem" : size === "lg" ? "1.6rem" : size === "xl" ? "2.1rem" : "1.35rem",
          color: isDark ? "#ffffff" : "#0f172a"
        }}>
          Form<span style={{ color: "#2563eb" }}>Fix</span>
        </div>
        {withTagline && (
          <span style={{
            fontSize: "0.7rem",
            fontWeight: 500,
            letterSpacing: "0.02em",
            color: isDark ? "#94a3b8" : "#64748b",
            marginTop: "2px"
          }}>
            Smart Verification Engine
          </span>
        )}
      </div>
    </div>
  );
}
