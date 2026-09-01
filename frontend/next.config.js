/** @type {import('next').NextConfig} */
const nextConfig = {
  // In local dev, proxy /api/* to the FastAPI backend running on 8000.
  // In Vercel production, vercel.json handles the routing — no rewrites needed.
  async rewrites() {
    if (process.env.NODE_ENV !== 'development') return [];
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [{ source: '/api/:path*', destination: `${apiUrl}/api/:path*` }];
  },
};

module.exports = nextConfig;
