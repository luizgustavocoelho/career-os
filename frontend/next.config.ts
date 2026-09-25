import type { NextConfig } from "next";

const config: NextConfig = {
  output: "standalone",

  allowedDevOrigins: (process.env.NEXT_ALLOWED_DEV_ORIGINS || "")
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean),

  distDir: process.env.NEXT_DIST_DIR || ".next",

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_INTERNAL_URL || "http://127.0.0.1:8000"}/api/:path*`,
      },
    ];
  },

  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "same-origin" },
        ],
      },
    ];
  },
};

export default config;
