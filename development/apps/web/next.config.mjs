/** @type {import('next').NextConfig} */
const config = {
  distDir: process.env.FLAME_NEXT_DIST_DIR || ".next",
  async headers() {
    return [{source:"/:path*",headers:[{
      key:"Content-Security-Policy",
      value:"frame-src 'self' https://www.youtube.com https://player.vimeo.com; object-src 'none'; base-uri 'self'"
    }]}];
  }
};
export default config;
