// esbuild resolves these packages dynamically inside the native compiler worker.
// Include their installed sources as well as the application's server bundles.
const simulationCompilerPackages = [
  "matter-js", "three", "@react-three/fiber", "react", "react-dom",
  "@babel/runtime", "@types/react-reconciler", "@types/webxr", "base64-js",
  "buffer", "ieee754", "its-fine", "react-use-measure", "scheduler",
  "suspend-react", "use-sync-external-store", "zustand",
];

/** @type {import('next').NextConfig} */
const config = {
  serverExternalPackages: ["esbuild"],
  outputFileTracingIncludes: { "/api/simulations/compile": ["./src/simulation-runtime/**/*", "./src/lib/simulations/compiler.cjs", "./node_modules/@rive-app/canvas-lite/**/*", "./node_modules/phaser/dist/phaser.min.js", "./node_modules/@esbuild/**/*", ...simulationCompilerPackages.map(name => `./node_modules/${name}/**/*`)] },
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
