/**
 * Purpose: Placeholder Vite configuration for the frontend application.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\vite.config.ts
 */

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: true,
    globals: true,
  },
});
