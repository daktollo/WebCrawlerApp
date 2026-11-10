import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Development server only; /api goes to the backend on port 1319, which also serves the built dist/ in production.
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5175,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:1319" },
  },
});
