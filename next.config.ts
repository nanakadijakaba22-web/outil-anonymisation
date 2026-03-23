import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Disable React strict mode for dev stability (can enable in prod)
  reactStrictMode: false,

  // Webpack configuration for Windows compatibility
  webpack: (config, { dev }) => {
    if (dev) {
      // Reduce file watching issues on Windows
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
        ignored: ['**/node_modules', '**/.git', '**/.next'],
      };
    }
    return config;
  },

  // Proxy API requests to backend
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://backend:8000/api/:path*',
      },
    ];
  },

  // Logging configuration
  logging: {
    fetches: {
      fullUrl: false,
    },
  },
};

export default nextConfig;
