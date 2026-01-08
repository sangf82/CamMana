/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export for packaging with PyInstaller
  output: 'export',
  
  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },
  
  // Disable strict mode to prevent double rendering in dev
  reactStrictMode: false,
  
  // Trailing slash for static export
  trailingSlash: false,
}

export default nextConfig
