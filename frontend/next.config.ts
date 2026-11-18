import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

export default function nextConfig(phase: string): NextConfig {
  const backend = process.env.SMART_WARDROBE_BACKEND_URL ?? "http://127.0.0.1:8000";
  const localVerification = phase === PHASE_DEVELOPMENT_SERVER
    && process.env.SMART_WARDROBE_LOCAL_PROXY_PROFILE === "verified_mixed_v1";
  if (localVerification) {
    const url = new URL(backend);
    if (!["http:", "https:"].includes(url.protocol)
      || !["127.0.0.1", "localhost", "[::1]"].includes(url.hostname)) {
      throw new Error("The verified local proxy profile requires a loopback backend.");
    }
  }
  return {
    distDir: process.env.SMART_WARDROBE_BUILD_DIR ?? ".next",
    turbopack: { root: __dirname },
    // A bounded transport window for slow, fully verified local workflows.
    // Default and production behavior stay unchanged; this is not an NFR target.
    ...(localVerification ? { experimental: { proxyTimeout: 300_000 } } : {}),
    async rewrites() {
      return [{ source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*` }];
    },
  };
}
