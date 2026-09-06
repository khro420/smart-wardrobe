import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  distDir: process.env.SMART_WARDROBE_BUILD_DIR ?? ".next",
  turbopack: { root: __dirname },
  async rewrites() {
    const backend = process.env.SMART_WARDROBE_BACKEND_URL ?? "http://127.0.0.1:8000";
    return [{ source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*` }];
  },
};

export default nextConfig;
