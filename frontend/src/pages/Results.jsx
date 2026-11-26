import React, { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import api from "@/lib/api";
import Layout from "@/components/Layout";
import { ArrowRight, RotateCcw, Sparkles, ListOrdered, AlertTriangle, Lightbulb, Loader2, BarChart3 } from "lucide-react";
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { toast } from "sonner";
import { SectionLabel, BigStat, Skeleton } from "@/components/SharedUI";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function Results() {
    const { sessionId } = useParams();
    const navigate = useNavigate();
    const [session, setSession] = useState(null);
    const [analysis, setAnalysis] = useState(null);
    const [summary, setSummary] = useState(null);
    const [loadingAi, setLoadingAi] = useState(true);

    useEffect(() => {
        api.get(`/sessions/${sessionId}`).then((r) => setSession(r.data)).catch(() => {
            toast.error("session not found");
            navigate("/dashboard");
        });
    }, [sessionId, navigate]);

    useEffect(() => {
        if (!session) return;
        const run = async () => {
            try {
                const [aRes, sRes] = await Promise.all([
                    api.post("/ai/analyze", {
                        target: session.target_text,
                        typed: session.typed_text,
                        duration_seconds: session.duration_seconds,
                        wpm: session.wpm,
                        accuracy: session.accuracy,
                        domain: session.domain,
                        topic: session.topic,
                        question: session.question || null,
                    }),
                    api.post("/ai/summary", {
                        text: session.target_text,
                        domain: session.domain,
                        topic: session.topic,
                        question: session.question || null,
                    }),
                ]);
                setAnalysis(aRes.data);
                setSummary(sRes.data);
            } catch (e) {
                toast.error("AI feedback failed to load.");
            } finally {
                setLoadingAi(false);
            }
        };
        run();
    }, [session]);

    if (!session) {
        return (
            <Layout>
                <div className="max-w-6xl mx-auto px-6 py-12 animate-pulse">
                    <div className="flex flex-wrap items-end justify-between gap-4 mb-10">
                        <div>
                            <Skeleton className="h-3 w-24 mb-3" />
                            <Skeleton className="h-10 w-64 mb-2" />
                            <Skeleton className="h-4 w-32" />
                        </div>
                        <div className="flex gap-2">
                            <Skeleton className="h-[42px] w-24" />
                            <Skeleton className="h-[42px] w-28" />
                            <Skeleton className="h-[42px] w-28" />
                        </div>
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                        <Skeleton className="h-[104px] w-full" />
                        <Skeleton className="h-[104px] w-full" />
                        <Skeleton className="h-[104px] w-full" />
                        <Skeleton className="h-[104px] w-full" />
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="lg:col-span-2">
                            <Skeleton className="h-[280px] w-full" />
                        </div>
                        <div>
                            <Skeleton className="h-[280px] w-full" />
                        </div>
                    </div>
                </div>
            </Layout>
        );
    }

    // Build a synthetic chart of WPM progression by character buckets (visual flair)
    const sparkData = buildSparkData(session);

    return (
        <Layout>
            <div className="max-w-6xl mx-auto px-6 py-12 animate-fade-up">
                <div className="flex flex-wrap items-end justify-between gap-4 mb-10">
                    <div>
                        <p className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono mb-2">
                            Run Complete
                        </p>
                        <h1 className="font-mono text-3xl sm:text-4xl text-white tracking-tight">
                            <span className="text-blue-400">{session.domain}</span>
                            <span className="text-zinc-600"> / </span>
                            {session.topic}
                        </h1>
                        <p className="text-zinc-500 mt-1 text-sm font-mono">{session.difficulty}</p>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                        <Link
                            to="/dashboard"
                            data-testid="results-new-run"
                            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white px-4 py-2.5 font-mono text-sm glow-blue transition-colors"
                        >
                            New Run
                            <ArrowRight className="h-4 w-4" />
                        </Link>
                        <Link
                            to="/history"
                            data-testid="results-view-history"
                            className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] text-zinc-200 px-4 py-2.5 font-mono text-sm transition-colors"
                        >
                            <BarChart3 className="h-4 w-4" />
                            History
                        </Link>
                    </div>
                </div>

                {/* Question Card (when session was a Concept Q&A run) */}
                {session.question && (
                    <div
                        data-testid="results-question-card"
                        className="tf-card p-5 mb-6 border-blue-500/20 bg-blue-500/[0.02] flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                    >
                        <div className="space-y-1">
                            <div className="text-[10px] uppercase tracking-[0.2em] text-blue-400 font-mono">
                                Question Answered
                            </div>
                            <div className="font-mono text-base text-white leading-snug">
                                {session.question}
                            </div>
                        </div>
                        {typeof session.recall_ms === "number" && (
                            <div className="shrink-0 rounded-lg border border-white/10 bg-white/[0.02] px-3.5 py-2 text-right font-mono">
                                <div className="text-[9px] uppercase tracking-[0.2em] text-zinc-500">
                                    Think Time
                                </div>
                                <div className="text-sm text-blue-400">
                                    {(session.recall_ms / 1000).toFixed(1)}s
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Stats grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                    <BigStat label="WPM" value={session.wpm.toFixed(1)} accent="blue" />
                    <BigStat label="RAW WPM" value={session.raw_wpm.toFixed(1)} />
                    <BigStat
                        label="ACCURACY"
                        value={`${session.accuracy.toFixed(1)}%`}
                        accent={session.accuracy >= 95 ? "green" : session.accuracy >= 85 ? "amber" : "rose"}
                    />
                    <BigStat label="TIME" value={`${session.duration_seconds.toFixed(1)}s`} />
                </div>

                <div className="flex flex-col lg:flex-row gap-6">
                    {/* Left Column */}
                    <div className="flex flex-col gap-6 w-full lg:w-2/3">
                    {/* Chart card */}
                    <div className="tf-card p-6 h-fit">
                        <SectionLabel>Typing Trace</SectionLabel>
                        <div className="w-full" style={{ height: 180 }}>
                            <ResponsiveContainer width="100%" height={180}>
                                <LineChart data={sparkData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                                    <XAxis 
                                        dataKey="time" 
                                        stroke="#52525B" 
                                        fontSize={10} 
                                        tickLine={false} 
                                        axisLine={false}
                                        tickFormatter={(v) => `${v}s`}
                                    />
                                    <YAxis 
                                        domain={['dataMin - 5', 'dataMax + 5']} 
                                        stroke="#52525B" 
                                        fontSize={10} 
                                        tickLine={false} 
                                        axisLine={false} 
                                        width={35}
                                        tickFormatter={(v) => Math.round(v)}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            background: "#18181B",
                                            border: "1px solid rgba(255,255,255,0.1)",
                                            borderRadius: 8,
                                            fontFamily: "IBM Plex Mono, monospace",
                                            fontSize: 12,
                                            color: "#fff",
                                        }}
                                        formatter={(v) => [`${v} wpm`, "wpm"]}
                                        labelFormatter={() => ""}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="wpm"
                                        stroke="#3B82F6"
                                        strokeWidth={2}
                                        dot={false}
                                        isAnimationActive={true}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="grid grid-cols-3 gap-3 mt-4">
                            <Mini label="Correct" value={session.correct_chars} color="text-emerald-400" />
                            <Mini label="Errors" value={session.incorrect_chars} color="text-rose-400" />
                            <Mini label="Chars" value={session.total_chars} color="text-zinc-300" />
                        </div>
                    </div>

                    {/* AI Mistake Analysis */}
                    <div className="tf-card p-6">
                        <SectionLabel icon={<AlertTriangle className="h-3 w-3" />}>Mistake Analysis</SectionLabel>
                        {loadingAi ? (
                            <SkeletonLines lines={6} />
                        ) : analysis ? (
                            <div data-testid="results-analysis" className="space-y-5">
                                <p className="font-mono text-sm text-zinc-200 leading-relaxed">
                                    {analysis.summary}
                                </p>

                                {analysis.weak_keys?.length > 0 && (
                                    <div>
                                        <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono mb-2">
                                            Weak Keys
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            {analysis.weak_keys.map((k, i) => (
                                                <kbd
                                                    key={i}
                                                    className="rounded border border-rose-500/30 bg-rose-500/5 px-2.5 py-1 text-sm font-mono text-rose-300"
                                                >
                                                    {k === " " ? "␣" : k}
                                                </kbd>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {analysis.error_patterns?.length > 0 && (
                                    <div>
                                        <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono mb-2">
                                            Error Patterns
                                        </div>
                                        <ul className="space-y-1">
                                            {analysis.error_patterns.map((p, i) => (
                                                <li key={i} className="text-sm text-zinc-300 font-mono">
                                                    <span className="text-rose-400 mr-2">▸</span>
                                                    {p}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {analysis.recommendations?.length > 0 && (
                                    <div>
                                        <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono mb-2">
                                            Recommendations
                                        </div>
                                        <ul className="space-y-1.5">
                                            {analysis.recommendations.map((r, i) => (
                                                <li key={i} className="text-sm text-zinc-200 flex gap-2">
                                                    <span className="text-emerald-400 mt-0.5">+</span>
                                                    <span>{r}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <p className="text-xs text-zinc-500 font-mono">No Analysis Available.</p>
                        )}
                    </div>

                    </div>

                    {/* Right Column */}
                    <div className="flex flex-col gap-6 w-full lg:w-1/3">
                    {/* AI Concept Summary */}
                    <div className="tf-card p-6">
                        <SectionLabel icon={<Sparkles className="h-3 w-3" />}>Concept Recap</SectionLabel>
                        {loadingAi ? (
                            <SkeletonLines lines={4} />
                        ) : summary ? (
                            <div data-testid="results-summary">
                                <div className="font-mono text-base text-white leading-relaxed">
                                    {summary.headline}
                                </div>
                                <ul className="mt-4 space-y-2">
                                    {summary.bullets.map((b, i) => (
                                        <li key={i} className="text-sm text-zinc-300 flex gap-2">
                                            <span className="text-blue-400 mt-1">·</span>
                                            <span>{b}</span>
                                        </li>
                                    ))}
                                </ul>
                                {summary.memory_hooks?.length > 0 && (
                                    <div className="mt-4 pt-4 border-t border-white/5">
                                        <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono mb-2 flex items-center gap-1.5">
                                            <Lightbulb className="h-3 w-3" />
                                            Memory Hooks
                                        </div>
                                        <ul className="space-y-1.5">
                                            {summary.memory_hooks.map((m, i) => (
                                                <li key={i} className="text-xs text-zinc-400 italic">
                                                    "{m}"
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <p className="text-xs text-zinc-500 font-mono">No Summary Available.</p>
                        )}
                    </div>

                    {/* Recommended next */}
                    <div className="tf-card p-6">
                        <SectionLabel icon={<ListOrdered className="h-3 w-3" />}>Next Topics</SectionLabel>
                        {loadingAi ? (
                            <SkeletonLines lines={4} />
                        ) : analysis?.next_topics?.length ? (
                            <ul className="space-y-2" data-testid="results-next-topics">
                                {analysis.next_topics.map((t, i) => (
                                    <li
                                        key={i}
                                        className="flex items-center gap-2 text-sm text-zinc-200 font-mono border border-white/5 rounded-md px-3 py-2 hover:border-blue-500/40 hover:bg-blue-500/5 transition-colors cursor-default"
                                    >
                                        <span className="text-blue-400 text-xs">{String(i + 1).padStart(2, "0")}</span>
                                        {t}
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p className="text-xs text-zinc-500 font-mono">Come Back Tomorrow For Fresh Picks.</p>
                        )}
                        <button
                            onClick={() => navigate("/dashboard")}
                            data-testid="results-pick-next"
                            className="mt-5 w-full inline-flex items-center justify-center gap-2 rounded-md bg-white/[0.03] hover:bg-white/[0.07] border border-white/10 text-zinc-200 px-3 py-2 text-xs font-mono"
                        >
                            <RotateCcw className="h-3.5 w-3.5" />
                            Pick Another
                        </button>
                    </div>
                    </div>
                </div>
            </div>
        </Layout>
    );
}

function buildSparkData(session) {
    const ks = session.keystrokes || [];
    const buckets = 16;
    if (ks.length >= 8 && session.duration_seconds > 0) {
        // Real WPM curve from per-keystroke timestamps using a rolling window.
        const totalMs = Math.max(1, session.duration_seconds * 1000);
        const windowMs = Math.max(1500, totalMs / 6); // ~6-second window or 1/6 of run
        const data = [];
        for (let b = 0; b < buckets; b++) {
            const tEnd = ((b + 1) / buckets) * totalMs;
            const tStart = Math.max(0, tEnd - windowMs);
            let correct = 0;
            for (const k of ks) {
                if (k.t >= tStart && k.t <= tEnd && k.correct) correct++;
            }
            const minutes = (tEnd - tStart) / 1000 / 60;
            const wpm = minutes > 0 ? correct / 5 / minutes : 0;
            data.push({ i: b, wpm: Number(wpm.toFixed(1)), time: Math.round(tEnd / 1000) });
        }
        // Snap last bucket to final WPM for accuracy
        data[data.length - 1].wpm = Number(session.wpm.toFixed(1));
        return data;
    }
    // Fallback synthetic curve (back-compat for sessions without keystrokes)
    const final = Math.max(1, session.wpm);
    const data = [];
    for (let i = 0; i < buckets; i++) {
        const t = i / (buckets - 1);
        const ease = 1 / (1 + Math.exp(-10 * (t - 0.45)));
        const wpm = Math.max(0, final * ease + (Math.random() - 0.5) * (final * 0.06));
        data.push({ i, wpm: Number(wpm.toFixed(1)), time: Math.round(((i + 1) / buckets) * session.duration_seconds) });
    }
    data[data.length - 1].wpm = Number(final.toFixed(1));
    return data;
}



function Mini({ label, value, color }) {
    return (
        <div className="text-center">
            <div className={`font-mono text-xl ${color}`}>{value}</div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono mt-1">
                {label}
            </div>
        </div>
    );
}



function SkeletonLines({ lines = 3 }) {
    return (
        <div className="space-y-2 animate-pulse">
            {Array.from({ length: lines }).map((_, i) => (
                <div
                    key={i}
                    className="h-3 rounded bg-white/5"
                    style={{ width: `${60 + Math.random() * 40}%` }}
                />
            ))}
        </div>
    );
}
