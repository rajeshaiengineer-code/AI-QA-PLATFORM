import path from "node:path";
import type { NextConfig } from "next";

/**
 * Backend origin for same-origin /api/v1 proxy (no browser CORS needed).
 * Local default: http://127.0.0.1:8000
 * Render: set BACKEND_URL=https://aiqa-api.onrender.com
 */
const backendUrl = (
  process.env.BACKEND_URL ||
  process.env.API_PROXY_TARGET ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

const nextConfig: NextConfig = {
  // Required for the production Docker / Render runner image
  output: "standalone",
  // Allow both localhost and 127.0.0.1 during local Next.js development
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  // Avoid wrong workspace-root inference when a nested clone exists nearby
  turbopack: {
    root: path.join(__dirname),
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
