/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',

  // Allow backend API calls
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_URL
          ? `${process.env.NEXT_PUBLIC_API_URL}/:path*`
          : 'http://localhost:8082/:path*',
      },
    ];
  },

  // Redirects: legacy routes → canonical routes
  async redirects() {
    return [
      { source: '/join', destination: '/connect', permanent: true },
      { source: '/terminal', destination: '/connect', permanent: false },
    ];
  },
};

export default nextConfig;
