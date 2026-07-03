import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 3000 },
  preview: { port: 3000 },
  test: {
    environment: "jsdom",
    // jsdom only exposes localStorage when the page has a real origin.
    environmentOptions: { jsdom: { url: "http://localhost:3000" } },
    globals: true,
    setupFiles: ["./src/test/setup.js"],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Long-cached vendor chunk: changes to app code don't invalidate it.
          "react-vendor": [
            "react",
            "react-dom",
            "react-router-dom",
            "react-redux",
            "@reduxjs/toolkit",
            "axios",
          ],
        },
      },
    },
  },
});
