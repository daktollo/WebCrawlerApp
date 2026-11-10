import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Development server; /api goes to the local backend. In production nginx (frontend/docker) serves dist/ on 1319.
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5175,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:1320" },
  },
});
