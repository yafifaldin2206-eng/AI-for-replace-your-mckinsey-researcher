/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // SSE proxy ke backend supaya tidak ada CORS issue
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
