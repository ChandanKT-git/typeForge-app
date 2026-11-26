/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
    theme: {
        extend: {
            fontFamily: {
                sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
                mono: ["'IBM Plex Mono'", "'JetBrains Mono'", "ui-monospace", "monospace"],
                display: ["'IBM Plex Mono'", "ui-monospace", "monospace"],
            },
            colors: {
                background: "hsl(var(--background))",
                foreground: "hsl(var(--foreground))",
                card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
                popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
                primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
                secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
                muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
                accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
                destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
                border: "hsl(var(--border))",
                input: "hsl(var(--input))",
                ring: "hsl(var(--ring))",
                forge: {
                    bg: "#09090B",
                    surface: "#18181B",
                    elev: "#27272A",
                    line: "rgba(255,255,255,0.06)",
                    text: "#FAFAFA",
                    muted: "#A1A1AA",
                    dim: "#52525B",
                    blue: "#3B82F6",
                    blueHi: "#60A5FA",
                    green: "#10B981",
                    rose: "#F43F5E",
                    amber: "#F59E0B",
                },
                chart: {
                    "1": "hsl(var(--chart-1))",
                    "2": "hsl(var(--chart-2))",
                    "3": "hsl(var(--chart-3))",
                    "4": "hsl(var(--chart-4))",
                    "5": "hsl(var(--chart-5))",
                },
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
            keyframes: {
                "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
                "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
                caretBlink: { "0%,49%": { opacity: 1 }, "50%,100%": { opacity: 0.15 } },
                fadeUp: { from: { opacity: 0, transform: "translateY(10px)" }, to: { opacity: 1, transform: "translateY(0)" } },
                shimmer: { "100%": { transform: "translateX(100%)" } },
                gridPulse: { "0%,100%": { opacity: 0.18 }, "50%": { opacity: 0.32 } },
            },
            animation: {
                "accordion-down": "accordion-down 0.2s ease-out",
                "accordion-up": "accordion-up 0.2s ease-out",
                "caret-blink": "caretBlink 1s steps(2, end) infinite",
                "fade-up": "fadeUp 0.4s ease-out both",
                "grid-pulse": "gridPulse 5s ease-in-out infinite",
            },
            backgroundImage: {
                "grid-fade":
                    "radial-gradient(circle at 50% 0%, rgba(59,130,246,0.12), transparent 60%)",
            },
        },
    },
    plugins: [require("tailwindcss-animate")],
};
