/** @type {import('next').NextConfig} */
const config = {
  serverExternalPackages: ["esbuild"],
  outputFileTracingIncludes: { "/api/simulations/compile": ["./src/simulation-runtime/**/*", "./src/lib/simulations/compiler.cjs", "./node_modules/@rive-app/canvas-lite/**/*", "./node_modules/phaser/dist/phaser.min.js", "./node_modules/@esbuild/**/*"] },
  turbopack: { resolveAlias: { "use-resize-observer": "./src/lib/mafs-resize-observer.ts" } },
  distDir: process.env.FLAME_NEXT_DIST_DIR || ".next",
  async headers() {
    return [{source:"/:path*",headers:[{
      key:"Content-Security-Policy",
      value:"frame-src 'self' https://www.youtube.com https://player.vimeo.com; object-src 'none'; base-uri 'self'"
    }]}];
  }
};
export default config;
