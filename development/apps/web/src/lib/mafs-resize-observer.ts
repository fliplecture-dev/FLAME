// Mafs 0.21 expects the v9 default export. v10 supports React 19 and keeps the
// same options/result contract, but exposes a named export. The pinned override
// and this narrow bundler alias avoid modifying installed package files.
export { useResizeObserver as default } from "../../node_modules/use-resize-observer/dist/index.mjs";
