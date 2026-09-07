import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  test: {
    // jsdom ships no `dialog` behaviour; `testSetup.ts` supplies the three
    // methods the dialogs call on themselves.
    setupFiles: ["./src/testSetup.ts"],
  },
});
