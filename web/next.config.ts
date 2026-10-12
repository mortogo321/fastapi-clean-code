import type { NextConfig } from "next";

// script-src is left out on purpose: Next.js injects inline bootstrap scripts, and a
// nonce-based policy is more machinery than this small BFF needs.
const contentSecurityPolicy =
  "base-uri 'self'; object-src 'none'; form-action 'self'; frame-ancestors 'none'";

const nextConfig: NextConfig = {
  output: "standalone",
  typedRoutes: true,
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: contentSecurityPolicy },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
