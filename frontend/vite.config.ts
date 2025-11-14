import path from "node:path";
import { TanStackRouterVite } from "@tanstack/router-vite-plugin";
import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vite";

// https://vitejs.dev/config/
export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  plugins: [react(), TanStackRouterVite()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Split React/React-DOM into separate chunk
          "react-vendor": ["react", "react-dom"],
          // Split Chakra UI into separate chunk (large dependency)
          "chakra-ui": ["@chakra-ui/react", "@emotion/react"],
          // Split TanStack packages (Query + Router)
          tanstack: ["@tanstack/react-query", "@tanstack/react-router"],
        },
      },
    },
  },
});
