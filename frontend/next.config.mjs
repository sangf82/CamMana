/** @type {import('next').NextConfig} */
const nextConfig = {
  // Output export disabled for dev proxy support
  // output: 'export',
  
  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },
  
  // Disable strict mode to prevent double rendering in dev
  reactStrictMode: false,
  
  // Trailing slash for static export
  trailingSlash: false,

  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
    ]
  },
}

export default nextConfig
