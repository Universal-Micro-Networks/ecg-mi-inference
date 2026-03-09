import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
	const env = loadEnv(mode, process.cwd(), "");
	const rawTarget =
		env.VITE_PROXY_TARGET || env.VITE_API_URL || "http://localhost:8000";
	const proxyTarget = rawTarget.replace(/\/api\/?$/, "");

	return {
		plugins: [react()],
		server: {
			proxy: {
				"/api": {
					target: proxyTarget,
					changeOrigin: true,
				},
			},
		},
	};
});
