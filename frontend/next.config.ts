import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for the production Docker / Render runner image
  output: "standalone",
};

export default nextConfig;
