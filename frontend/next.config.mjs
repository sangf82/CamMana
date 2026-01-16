/** @type {import('next').NextConfig} */
const nextConfig = {
  // Asset prefix for standalone builds
  assetPrefix: process.env.NODE_ENV === 'production' ? '' : undefined,
  
  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },
  
  // Disable strict mode to prevent double rendering in dev
  reactStrictMode: false,
  
  // Trailing slash for static export
  trailingSlash: false,
}

// Only add output: export for production builds
// In development, we need rewrites to proxy API calls
if (process.env.NODE_ENV === 'production') {
  nextConfig.output = 'export'
} else {
  // Rewrites only work in dev mode (no static export)
  nextConfig.rewrites = async () => {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
    ]
  }
}

export default nextConfig
