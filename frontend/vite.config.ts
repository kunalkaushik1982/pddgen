/**
 * Purpose: Placeholder Vite configuration for the frontend application.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\vite.config.ts
 */

import fs from "node:fs";
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const releaseManifestPath = path.resolve(__dirname, "../release.json");
const releaseManifest = (
  fs.existsSync(releaseManifestPath)
    ? JSON.parse(fs.readFileSync(releaseManifestPath, "utf-8"))
    : {
        release: "0.0.0-dev",
        frontend: "0.0.0-dev",
        backend: "0.0.0-dev",
        worker: "0.0.0-dev",
      }
) as {
  release: string;
  frontend: string;
  backend: string;
  worker: string;
};

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_RELEASE__: JSON.stringify(releaseManifest.release),
    __FRONTEND_VERSION__: JSON.stringify(releaseManifest.frontend),
    __BACKEND_VERSION__: JSON.stringify(releaseManifest.backend),
    __WORKER_VERSION__: JSON.stringify(releaseManifest.worker),
  },
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
