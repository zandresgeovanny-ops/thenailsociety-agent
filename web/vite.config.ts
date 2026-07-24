import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo, las llamadas a /reservar/api/* se redirigen al backend FastAPI
// (uvicorn en :8000), así el front no necesita CORS ni VITE_API_URL en local.
// En producción se usa VITE_API_URL (dominio público de Railway).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/reservar": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
