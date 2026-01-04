/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            },
            colors: {
                background: '#0f172a', // Slate 900
                surface: '#1e293b',    // Slate 800
                surfaceHighlight: '#334155', // Slate 700
                primary: '#3b82f6',    // Blue 500
                secondary: '#64748b',  // Slate 500
                accent: '#8b5cf6',     // Violet 500
                success: '#10b981',    // Emerald 500
                danger: '#ef4444',     // Red 500
                warning: '#f59e0b',    // Amber 500
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
                'hero-glow': 'conic-gradient(from 180deg at 50% 50%, #2a8af6 0deg, #a853ba 180deg, #e92a67 360deg)',
            },
            animation: {
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            }
        },
    },
    plugins: [],
}
