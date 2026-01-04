import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
    // Load env variables from parent directory
    const env = loadEnv(mode, path.resolve(__dirname, '..'), '')
    const FRONTEND_PORT = parseInt(env.FRONTEND_PORT) || 5110
    const BACKEND_PORT = parseInt(env.BACKEND_PORT) || 5111

    return {
        plugins: [react()],
        envDir: '..',
        server: {
            port: FRONTEND_PORT,
            strictPort: true,
            proxy: {
                '/ws': {
                    target: `ws://localhost:${BACKEND_PORT}`,
                    ws: true,
                    changeOrigin: true
                },
                '/api': {
                    target: `http://localhost:${BACKEND_PORT}`,
                    changeOrigin: true
                }
            }
        },
        build: {
            outDir: 'dist',
            emptyOutDir: true
        }
    }
})
