import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Cpu, Sparkles, Gauge, BookOpen, Keyboard, Activity } from "lucide-react";

const SAMPLE_LINES = [
    'An INNER JOIN returns rows that match in both tables.',
    'A process is an instance of a program in execution.',
    'The OSI model defines seven distinct layers of network abstraction.',
    'Gradient descent updates weights along the negative gradient of the loss.',
];

export default function Landing() {
    return (
        <div className="tf-shell">
            <header className="border-b border-white/5">
                <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <span className="h-7 w-7 rounded-md bg-blue-600/15 border border-blue-500/30 grid place-items-center">
                            <Keyboard className="h-4 w-4 text-blue-400" />
                        </span>
                        <span className="font-mono text-sm tracking-tight">
                            <span className="text-white">Type</span>
                            <span className="text-blue-400">Forge</span>
                        </span>
                    </div>
                    <div className="flex items-center gap-3">
                        <Link
                            to="/login"
                            data-testid="landing-login"
                            className="text-sm font-mono text-zinc-400 hover:text-white px-3 py-1.5 rounded-md hover:bg-white/5"
                        >
                            Sign In
                        </Link>
                        <Link
                            to="/register"
                            data-testid="landing-register"
                            className="text-sm font-mono bg-blue-600 hover:bg-blue-500 text-white px-4 py-1.5 rounded-md transition-colors glow-blue"
                        >
                            Get Started
                        </Link>
                    </div>
                </div>
            </header>

            <section className="relative overflow-hidden">
                <div className="absolute inset-0 bg-grid-faint opacity-40 pointer-events-none" />
                <div className="absolute inset-0 bg-grid-fade pointer-events-none" />
                <div className="max-w-6xl mx-auto px-6 pt-24 pb-20 relative">
                    <div className="flex items-center gap-2 text-xs font-mono text-blue-400/80 mb-6">
                        <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
                        AI-CURATED CONTENT · POWERED BY GROQ
                    </div>
                    <h1 className="font-mono tracking-tighter text-4xl sm:text-5xl lg:text-6xl text-white leading-[1.05] max-w-3xl">
                        Type The Concepts.
                        <br />
                        <span className="text-zinc-500">Learn At The Speed Of Light.</span>
                    </h1>
                    <p className="mt-6 max-w-xl text-zinc-400 text-base leading-relaxed">
                        Typeforge is a focused arena for engineers. Pick a domain — Programming,
                        DBMS, OS, Networking, AI/ML — and an AI generates technically precise,
                        typing-friendly passages tailored to your level. Type. Learn. Repeat.
                    </p>
                    <div className="mt-10 flex flex-col sm:flex-row gap-3">
                        <Link
                            to="/register"
                            data-testid="hero-cta"
                            className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white px-5 py-3 text-sm font-mono glow-blue transition-colors"
                        >
                            Start Practicing
                            <ArrowRight className="h-4 w-4" />
                        </Link>
                        <Link
                            to="/login"
                            className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] text-zinc-200 px-5 py-3 text-sm font-mono transition-colors"
                        >
                            I Have An Account
                        </Link>
                    </div>

                    {/* Sample arena card */}
                    <div className="mt-16 tf-card p-8 sm:p-10 relative">
                        <div className="absolute top-4 right-4 flex items-center gap-1.5">
                            <span className="h-2 w-2 rounded-full bg-rose-500/60" />
                            <span className="h-2 w-2 rounded-full bg-amber-500/60" />
                            <span className="h-2 w-2 rounded-full bg-emerald-500/60" />
                        </div>
                        <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono mb-4">
                            <span className="text-blue-400">DBMS</span>
                            <span>/</span>
                            <span>SQL Joins</span>
                            <span>/</span>
                            <span>Intermediate</span>
                        </div>
                        <p className="font-mono text-xl sm:text-2xl leading-relaxed text-zinc-500">
                            <span className="text-white">An INNER JOIN returns rows that match</span>
                            <span className="text-zinc-500"> In Both Tables Based On The Join Condition. It Is The Most Common Type Of Join In SQL.</span>
                        </p>
                        <div className="mt-8 grid grid-cols-3 gap-4">
                            <Stat label="WPM" value="64" />
                            <Stat label="ACC" value="97%" accent="green" />
                            <Stat label="ERR" value="03" accent="rose" />
                        </div>
                    </div>
                </div>
            </section>

            <section className="border-t border-white/5">
                <div className="max-w-6xl mx-auto px-6 py-24 grid grid-cols-1 md:grid-cols-3 gap-6">
                    <Feature
                        icon={<Cpu className="h-4 w-4 text-blue-400" />}
                        title="AI concept generator"
                        body="Pick a topic. The model produces technically precise, ASCII-clean prose at your difficulty."
                    />
                    <Feature
                        icon={<Gauge className="h-4 w-4 text-blue-400" />}
                        title="Adaptive difficulty"
                        body="Length and complexity adjust to your accuracy and WPM, so the next round is always one step ahead."
                    />
                    <Feature
                        icon={<Activity className="h-4 w-4 text-blue-400" />}
                        title="Mistake analysis"
                        body="Post-session AI report on weak keys, error patterns and a personalised drill plan."
                    />
                    <Feature
                        icon={<BookOpen className="h-4 w-4 text-blue-400" />}
                        title="Concept summary"
                        body="Every passage you type is distilled into bullets and memory hooks for instant reinforcement."
                    />
                    <Feature
                        icon={<Sparkles className="h-4 w-4 text-blue-400" />}
                        title="Premium arena"
                        body="Distraction-free Monkeytype-grade arena with character-level feedback and a caret that glides."
                    />
                    <Feature
                        icon={<Activity className="h-4 w-4 text-blue-400" />}
                        title="Progress charts"
                        body="WPM and accuracy over time, by domain. Watch yourself level up — for real."
                    />
                </div>
            </section>

            <section className="border-t border-white/5 bg-zinc-950/50">
                <div className="max-w-3xl mx-auto px-6 py-20 text-center">
                    <h2 className="font-mono text-2xl sm:text-3xl text-white mb-3">
                        A Thousand Random Words Taught Me Nothing.
                    </h2>
                    <p className="text-zinc-400 max-w-xl mx-auto">
                        With Typeforge, every line you type is something an engineer should know.
                    </p>
                    <Link
                        to="/register"
                        className="inline-flex mt-8 items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white px-5 py-3 text-sm font-mono glow-blue transition-colors"
                    >
                        Forge Your Speed
                        <ArrowRight className="h-4 w-4" />
                    </Link>
                </div>
            </section>

            <footer className="border-t border-white/5 py-8">
                <div className="max-w-6xl mx-auto px-6 flex items-center justify-between text-xs font-mono text-zinc-600">
                    <span>Typeforge · 2026</span>
                    <span>Built For Engineers Who Type Faster Than They Think</span>
                </div>
            </footer>

            {/* Hidden marquee not used; keep SAMPLE_LINES referenced */}
            <span className="sr-only">{SAMPLE_LINES.join(" ")}</span>
        </div>
    );
}

function Stat({ label, value, accent }) {
    const colorMap = {
        green: "text-emerald-400",
        rose: "text-rose-400",
    };
    return (
        <div className="tf-card p-4">
            <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono">
                {label}
            </div>
            <div className={`mt-1 font-mono text-2xl ${colorMap[accent] || "text-white"}`}>
                {value}
            </div>
        </div>
    );
}

function Feature({ icon, title, body }) {
    return (
        <div className="tf-card p-6 hover:border-white/10 transition-colors">
            <div className="h-8 w-8 rounded-md bg-blue-500/10 border border-blue-500/20 grid place-items-center mb-4">
                {icon}
            </div>
            <div className="font-mono text-white text-base">{title}</div>
            <p className="mt-2 text-sm text-zinc-400 leading-relaxed">{body}</p>
        </div>
    );
}
