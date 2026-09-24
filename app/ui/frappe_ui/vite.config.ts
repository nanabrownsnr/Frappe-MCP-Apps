// Build the React App as one self-contained HTML resource for MCP clients.
// Change outDir only together with resource.py's VIEW_PATH.
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";
import path from "path";

export default defineConfig({
  // The React plugin compiles JSX with the automatic runtime, so the bundle
  // does not depend on a global `React` variable in MCP sandboxes.
  plugins: [react(), tailwindcss(), viteSingleFile()],
  build: { outDir: "dist" },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
