import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import Layout from "@/components/Layout";
import { useAuth } from "@/contexts/AuthContext";
import { ArrowRight, Code2, Database, Cpu, Network, Brain, Loader2, Sparkles, TrendingUp, Target, Timer, Flame, Zap, CheckCircle2, Globe, Server, Cloud, Terminal, AppWindow, ServerCog, Eye, Bot, FileUp } from "lucide-react";
import { toast } from "sonner";
import { SectionLabel, Skeleton } from "@/components/SharedUI";
import KeyboardHeatmap from "@/components/KeyboardHeatmap";

const DOMAIN_ICONS = {
    Programming: Code2,
    DBMS: Database,
    OS: Cpu,
    Networking: Network,
    "AI/ML": Brain,
    "Web Development": Globe,
    "System Design": Server,
    "Cloud & DevOps": Cloud,
    Golang: Terminal,
    Frontend: AppWindow,
    Backend: ServerCog,
    "Computer Vision": Eye,
    "Gen AI": Bot,
};

const LENGTH_LABELS = {
    short: "short · ~25-40 words",
    medium: "medium · ~50-80 words",
    long: "long · ~90-130 words",
};

export default function Dashboard() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [catalog, setCatalog] = useState({ domains: [], difficulties: [] });
    const [domain, setDomain] = useState("");
    const [topic, setTopic] = useState("");
    const [difficulty, setDifficulty] = useState("Intermediate");
    const [length, setLength] = useState("medium");
    const [includeCode, setIncludeCode] = useState(false);
    const [loading, setLoading] = useState(false);
    const [stats, setStats] = useState(null);

    useEffect(() => {
        api.get("/topics").then((r) => {
            setCatalog(r.data);
            if (r.data.domains?.length) {
                setDomain(r.data.domains[0].name);
                setTopic(r.data.domains[0].topics[0]);
            }
        });
        api.get("/sessions/stats/overview")
            .then((r) => setStats(r.data))
            .catch(() => {});
    }, []);

    const topics = useMemo(() => {
        return catalog.domains?.find((d) => d.name === domain)?.topics || [];
    }, [catalog, domain]);

    const onDomainChange = (name) => {
        setDomain(name);
        const d = catalog.domains.find((x) => x.name === name);
        setTopic(d?.topics?.[0] || "");
    };

    const startSession = async () => {
        if (!domain || !topic) {
            toast.error("pick a domain and topic.");
            return;
        }
        setLoading(true);
        try {
            const { data } = await api.post("/ai/generate", {
                domain,
                topic,
                difficulty,
                length,
                include_code: includeCode,
            });
            navigate("/practice", {
                state: {
                    question: data.question || null,
                    mode: data.mode || (data.question ? "qa" : "passage"),
                    text: data.text,
                    notes: data.notes,
                    domain,
                    topic,
                    difficulty,
                    length,
                    include_code: includeCode,
                },
            });
        } catch (e) {
            toast.error("AI failed to generate content. Try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Layout>
            <div className="max-w-6xl mx-auto px-6 py-12">
                <div className="flex flex-wrap items-end justify-between gap-4 mb-10 animate-fade-up">
                    <div>
                        <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono mb-2">
                            Welcome Back
                        </p>
                        <h1 className="font-mono text-3xl sm:text-4xl text-white tracking-tight">
                            {user?.name || "engineer"}, Ready to forge?
                        </h1>
                    </div>
                    {stats && stats.total_sessions > 0 && (
                        <div className="flex items-center gap-3 flex-wrap" data-testid="dashboard-stats-row">
                            <MiniStat icon={<TrendingUp className="h-3.5 w-3.5" />} label="Avg Wpm" value={stats.avg_wpm} />
                            <MiniStat icon={<Target className="h-3.5 w-3.5" />} label="Avg Acc" value={`${stats.avg_accuracy}%`} />
                            <MiniStat icon={<Timer className="h-3.5 w-3.5" />} label="Runs" value={stats.total_sessions} />
                        </div>
                    )}
                </div>

                {/* Streak + daily goal + AI recommendation */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10 animate-fade-up">
                    {stats ? (
                        <>
                            <StreakCard streak={stats.streak} />
                            <DailyGoalCard streak={stats.streak} />
                            <RecommendationCard
                                recommendation={stats.recommendation}
                                onApply={(r) => {
                                    if (r.difficulty) setDifficulty(r.difficulty);
                                    if (r.length) setLength(r.length);
                                    toast.success("auto-adapt applied.");
                                    document
                                        .querySelector("[data-testid=start-session-btn]")
                                        ?.scrollIntoView({ behavior: "smooth", block: "center" });
                                }}
                            />
                        </>
                    ) : (
                        <>
                            <Skeleton className="h-24 w-full" />
                            <Skeleton className="h-[136px] w-full" />
                            <Skeleton className="h-36 w-full" />
                        </>
                    )}
                </div>

                {stats && stats.heatmap && Object.keys(stats.heatmap).length > 0 && (
                    <div className="mb-10 animate-fade-up" style={{ animationDelay: "0.1s" }}>
                        <KeyboardHeatmap heatmapData={stats.heatmap} />
                    </div>
                )}

                {/* Domain selector */}
                <section className="mb-8">
                    <SectionLabel>1 · Choose Your Domain</SectionLabel>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                        {catalog.domains.map((d) => {
                            const Icon = DOMAIN_ICONS[d.name] || Sparkles;
                            const active = domain === d.name;
                            return (
                                <button
                                    key={d.name}
                                    type="button"
                                    onClick={() => onDomainChange(d.name)}
                                    data-testid={`domain-${d.name.toLowerCase().replace(/\W+/g, "-")}`}
                                    className={`tf-card p-4 text-left transition-all hover:border-white/15 ${
                                        active
                                            ? "border-blue-500/60 bg-blue-500/5 shadow-[0_0_30px_-10px_rgba(59,130,246,0.5)]"
                                            : ""
                                    }`}
                                >
                                    <Icon
                                        className={`h-4 w-4 mb-3 ${active ? "text-blue-400" : "text-zinc-400"}`}
                                    />
                                    <div className="font-mono text-sm text-white">{d.name}</div>
                                    <div className="text-[11px] text-zinc-500 mt-1 font-mono">
                                        {d.topics.length} Topics
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </section>

                {/* Document upload card */}
                <section className="mb-8">
                    <SectionLabel>Or · Type From Your Documents</SectionLabel>
                    <button
                        type="button"
                        onClick={() => navigate("/documents")}
                        data-testid="open-documents-btn"
                        className="tf-card p-5 w-full text-left hover:border-blue-500/40 hover:bg-blue-500/[0.02] transition-all group"
                    >
                        <div className="flex items-center gap-4">
                            <div className="h-11 w-11 rounded-xl grid place-items-center border border-white/10 bg-white/[0.03] group-hover:border-blue-500/30 group-hover:bg-blue-500/5 transition-colors">
                                <FileUp className="h-5 w-5 text-zinc-400 group-hover:text-blue-400 transition-colors" />
                            </div>
                            <div>
                                <div className="font-mono text-sm text-white font-medium">My Document Library</div>
                                <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
                                    Upload PDFs, notes, or source code · Practice custom typing passages or generate RAG drills
                                </div>
                            </div>
                            <ArrowRight className="h-4 w-4 text-zinc-500 ml-auto group-hover:text-blue-400 group-hover:translate-x-0.5 transition-all" />
                        </div>
                    </button>
                </section>

                {/* Topic + difficulty + length */}
                <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                    <div className="lg:col-span-2 tf-card p-6">
                        <SectionLabel>2 · Pick a Topic</SectionLabel>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[260px] overflow-y-auto pr-1">
                            {topics.map((t) => {
                                const active = topic === t;
                                return (
                                    <button
                                        type="button"
                                        key={t}
                                        onClick={() => setTopic(t)}
                                        data-testid={`topic-${t.toLowerCase().replace(/\W+/g, "-")}`}
                                        className={`text-left rounded-md border px-3 py-2 text-sm font-mono transition-colors ${
                                            active
                                                ? "border-blue-500/50 bg-blue-500/5 text-white"
                                                : "border-white/5 text-zinc-400 hover:border-white/15 hover:text-white"
                                        }`}
                                    >
                                        {t}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    <div className="tf-card p-6">
                        <SectionLabel>3 · Tune Your Run</SectionLabel>

                        <div className="space-y-5">
                            <div>
                                <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono mb-2">
                                    Difficulty
                                </div>
                                <div className="grid grid-cols-3 gap-2">
                                    {(catalog.difficulties || ["Beginner", "Intermediate", "Advanced"]).map((d) => (
                                        <button
                                            key={d}
                                            type="button"
                                            onClick={() => setDifficulty(d)}
                                            data-testid={`difficulty-${d.toLowerCase()}`}
                                            className={`w-full rounded-md border px-1 py-1.5 text-[11px] font-mono transition-colors truncate ${
                                                difficulty === d
                                                    ? "border-blue-500/50 bg-blue-500/5 text-white"
                                                    : "border-white/5 text-zinc-400 hover:text-white"
                                            }`}
                                        >
                                            {d.toLowerCase()}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono mb-2">
                                    Length
                                </div>
                                <div className="space-y-2">
                                    {Object.entries(LENGTH_LABELS).map(([k, label]) => (
                                        <button
                                            key={k}
                                            type="button"
                                            onClick={() => setLength(k)}
                                            data-testid={`length-${k}`}
                                            className={`w-full text-left rounded-md border px-3 py-2 text-xs font-mono transition-colors ${
                                                length === k
                                                    ? "border-blue-500/50 bg-blue-500/5 text-white"
                                                    : "border-white/5 text-zinc-400 hover:text-white"
                                            }`}
                                        >
                                            {label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <label className="flex items-center justify-between cursor-pointer">
                                <span className="text-xs font-mono text-zinc-400">
                                    Include Code Snippet
                                </span>
                                <span
                                    onClick={() => setIncludeCode((v) => !v)}
                                    data-testid="include-code-toggle"
                                    className={`relative h-5 w-9 rounded-full transition-colors ${
                                        includeCode ? "bg-blue-600" : "bg-zinc-700"
                                    }`}
                                >
                                    <span
                                        className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${
                                            includeCode ? "left-[18px]" : "left-0.5"
                                        }`}
                                    />
                                </span>
                            </label>
                        </div>
                    </div>
                </section>

                <div className="flex items-center justify-end">
                    <button
                        onClick={startSession}
                        disabled={loading || !domain || !topic}
                        data-testid="start-session-btn"
                        className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-6 py-3 font-mono text-sm glow-blue transition-colors"
                    >
                        {loading ? (
                            <>
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Forging your passage…
                            </>
                        ) : (
                            <>
                                Begin Run
                                <ArrowRight className="h-4 w-4" />
                            </>
                        )}
                    </button>
                </div>
            </div>
        </Layout>
    );
}



function MiniStat({ icon, label, value }) {
    return (
        <div className="tf-card px-4 py-2.5 flex items-center gap-3">
            <span className="text-blue-400">{icon}</span>
            <div>
                <div className="text-[9px] uppercase tracking-[0.2em] text-zinc-500 font-mono">
                    {label}
                </div>
                <div className="font-mono text-sm text-white">{value}</div>
            </div>
        </div>
    );
}

function StreakCard({ streak }) {
    const cur = streak?.current ?? 0;
    const longest = streak?.longest ?? 0;
    const hot = cur >= 3;
    return (
        <div className="tf-card p-5 flex items-center gap-4" data-testid="streak-card">
            <div
                className={`h-12 w-12 rounded-xl grid place-items-center border ${
                    hot
                        ? "bg-amber-500/10 border-amber-500/40 text-amber-400"
                        : cur > 0
                        ? "bg-blue-500/10 border-blue-500/30 text-blue-400"
                        : "bg-white/[0.03] border-white/10 text-zinc-500"
                }`}
            >
                <Flame className="h-5 w-5" />
            </div>
            <div className="flex-1">
                <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono">
                    Current Streak
                </div>
                <div className="font-mono text-2xl text-white mt-0.5" data-testid="streak-value">
                    {cur} <span className="text-zinc-500 text-sm">{cur === 1 ? "day" : "days"}</span>
                </div>
                <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
                    longest · {longest}d
                </div>
            </div>
        </div>
    );
}

function DailyGoalCard({ streak }) {
    const today = streak?.today ?? 0;
    const goal = streak?.goal ?? 3;
    const pct = Math.min(100, (today / goal) * 100);
    const met = streak?.goal_met;
    return (
        <div className="tf-card p-5" data-testid="daily-goal-card">
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <Target className="h-4 w-4 text-blue-400" />
                    <span className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono">
                        Daily Goal
                    </span>
                </div>
                {met && (
                    <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-mono" data-testid="goal-met-badge">
                        <CheckCircle2 className="h-3 w-3" />
                        Smashed
                    </span>
                )}
            </div>
            <div className="font-mono text-2xl text-white">
                {today} <span className="text-zinc-500 text-sm">/ {goal} runs today</span>
            </div>
            <div className="mt-3 h-1.5 rounded-full bg-white/5 overflow-hidden">
                <div
                    className={`h-full transition-all ${met ? "bg-emerald-500" : "bg-blue-500"}`}
                    style={{ width: `${pct}%` }}
                />
            </div>
            <div className="text-[11px] text-zinc-500 font-mono mt-2">
                {met
                    ? "great work. one more keeps the streak alive tomorrow."
                    : `${goal - today} more to keep your streak alive.`}
            </div>
        </div>
    );
}

function RecommendationCard({ recommendation, onApply }) {
    const r = recommendation;
    if (!r) return null;
    return (
        <div className="tf-card p-5 border-blue-500/30 bg-blue-500/[0.03] relative overflow-hidden" data-testid="recommendation-card">
            <div className="absolute -top-12 -right-12 h-32 w-32 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
            <div className="flex items-center gap-2 mb-2 relative">
                <Zap className="h-4 w-4 text-blue-400" />
                <span className="text-[10px] uppercase tracking-[0.2em] text-blue-400 font-mono">
                    Auto-adapt
                </span>
            </div>
            <div className="font-mono text-sm text-white leading-relaxed" data-testid="recommendation-reason">
                {r.reason}
            </div>
            <div className="flex items-center gap-2 mt-3 flex-wrap">
                <span className="px-2 py-1 rounded-md bg-white/5 border border-white/10 text-[11px] font-mono text-zinc-300">
                    {r.difficulty}
                </span>
                <span className="px-2 py-1 rounded-md bg-white/5 border border-white/10 text-[11px] font-mono text-zinc-300">
                    {r.length}
                </span>
                {r.based_on_sessions > 0 && (
                    <span className="text-[10px] font-mono text-zinc-500">
                        based on last {r.based_on_sessions}
                    </span>
                )}
            </div>
            <button
                onClick={() => onApply(r)}
                data-testid="apply-recommendation-btn"
                className="mt-4 w-full inline-flex items-center justify-center gap-1.5 rounded-md bg-blue-600/90 hover:bg-blue-500 text-white px-3 py-2 text-xs font-mono transition-colors"
            >
                Apply & Forge
                <ArrowRight className="h-3.5 w-3.5" />
            </button>
        </div>
    );
}
