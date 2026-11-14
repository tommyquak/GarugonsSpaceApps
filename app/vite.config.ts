// Written with Super Intelligence (SI) assistance.
import { defineConfig } from "vite";

// The site is served from https://tommyquak.github.io/GarugonsSpaceApps/
export default defineConfig({
  base: "/GarugonsSpaceApps/",
  // Lets the app import docs/LIMITS.md and the root README.md as text at build time.
  server: { fs: { allow: [".."] } },
  build: { target: "es2022", chunkSizeWarningLimit: 1500 },
});
