import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import Layout from "@/components/Layout";
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, BarChart, Bar, CartesianGrid } from "recharts";
import { ArrowRight, Download } from "lucide-react";
import { toast } from "sonner";
import { SectionLabel, BigStat, Skeleton } from "@/components/SharedUI";

export default function History() {
    const [stats, setStats] = useState(null);
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        Promise.all([
            api.get("/sessions/stats/overview").then((r) => r.data),
            api.get("/sessions").then((r) => r.data),
        ])
            .then(([s, ss]) => {
                setStats(s);
                setSessions(ss);
            })
            .finally(() => setLoading(false));
    }, []);



    const empty = !stats || stats.total_sessions === 0;

    const handleExport = async () => {
        try {
            const response = await api.get("/sessions/export", { responseType: "blob" });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement("a");
            link.href = url;
            link.setAttribute("download", "typeforge_export.csv");
            document.body.appendChild(link);
            link.click();
            link.remove();
            toast.success("Export successful.");
        } catch (e) {
            toast.error("Failed to export history.");
        }
    };

    return (
        <Layout>
            <div className="max-w-6xl mx-auto px-6 py-12 animate-fade-up">
                <div className="flex flex-wrap items-end justify-between gap-4 mb-10">
                    <div>
                        <p className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono mb-2">
                            Your Forge
                        </p>
                        <h1 className="font-mono text-3xl sm:text-4xl text-white tracking-tight">
                            history & progress
                        </h1>
                    </div>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={handleExport}
                            className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-white px-4 py-2.5 font-mono text-sm transition-colors"
                        >
                            <Download className="h-4 w-4" />
                            Export Csv
                        </button>
                        <Link
                            to="/dashboard"
                            data-testid="history-new-run"
                            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white px-4 py-2.5 font-mono text-sm glow-blue transition-colors"
                        >
                            New Run
                            <ArrowRight className="h-4 w-4" />
                        </Link>
                    </div>
                </div>

                {loading ? (
                    <>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                            <Skeleton className="h-[104px] w-full" />
                            <Skeleton className="h-[104px] w-full" />
                            <Skeleton className="h-[104px] w-full" />
                            <Skeleton className="h-[104px] w-full" />
                        </div>
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            <div className="lg:col-span-2">
                                <Skeleton className="h-[340px] w-full" />
                            </div>
                            <div>
                                <Skeleton className="h-[340px] w-full" />
                            </div>
                            <div className="lg:col-span-3">
                                <Skeleton className="h-64 w-full" />
                            </div>
                        </div>
                    </>
                ) : empty ? (
                    <div className="tf-card p-12 text-center">
                        <p className="font-mono text-xl text-white">No Runs Yet.</p>
                        <p className="text-sm text-zinc-500 mt-2">
                            Kick Off Your First AI-curated Typing Run To Start Tracking Progress.
                        </p>
                        <Link
                            to="/dashboard"
                            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 text-sm font-mono glow-blue"
                        >
                            Start Now
                            <ArrowRight className="h-4 w-4" />
                        </Link>
                    </div>
                ) : (
                    <>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                            <BigStat label="TOTAL RUNS" value={stats.total_sessions} />
                            <BigStat label="AVG WPM" value={stats.avg_wpm} accent="blue" />
                            <BigStat label="BEST WPM" value={stats.best_wpm} accent="green" />
                            <BigStat label="AVG ACC" value={`${stats.avg_accuracy}%`} />
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            <div className="tf-card p-6 lg:col-span-2">
                                <SectionLabel>Wpm Over Time</SectionLabel>
                                <div className="w-full" style={{ height: 256 }}>
                                    <ResponsiveContainer width="100%" height={256}>
                                        <LineChart data={stats.last_30}>
                                            <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                                            <XAxis
                                                dataKey="date"
                                                stroke="#52525B"
                                                fontSize={10}
                                                tickLine={false}
                                                axisLine={false}
                                                tick={{ fontFamily: "IBM Plex Mono" }}
                                            />
                                            <YAxis
                                                stroke="#52525B"
                                                fontSize={10}
                                                tickLine={false}
                                                axisLine={false}
                                                tick={{ fontFamily: "IBM Plex Mono" }}
                                            />
                                            <Tooltip
                                                contentStyle={{
                                                    background: "#18181B",
                                                    border: "1px solid rgba(255,255,255,0.1)",
                                                    borderRadius: 8,
                                                    fontFamily: "IBM Plex Mono",
                                                    fontSize: 12,
                                                    color: "#fff",
                                                }}
                                            />
                                            <Line
                                                type="monotone"
                                                dataKey="avg_wpm"
                                                stroke="#3B82F6"
                                                strokeWidth={2}
                                                dot={{ r: 3, fill: "#3B82F6" }}
                                                activeDot={{ r: 5 }}
                                                name="avg wpm"
                                            />
                                            <Line
                                                type="monotone"
                                                dataKey="avg_accuracy"
                                                stroke="#10B981"
                                                strokeWidth={2}
                                                dot={false}
                                                name="avg accuracy"
                                            />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            <div className="tf-card p-6">
                                <SectionLabel>By Domain</SectionLabel>
                                <div className="w-full" style={{ height: 256 }}>
                                    <ResponsiveContainer width="100%" height={256}>
                                        <BarChart data={stats.by_domain} layout="vertical">
                                            <XAxis type="number" hide />
                                            <YAxis
                                                type="category"
                                                dataKey="domain"
                                                stroke="#52525B"
                                                fontSize={10}
                                                axisLine={false}
                                                tickLine={false}
                                                width={70}
                                                tick={{ fontFamily: "IBM Plex Mono" }}
                                            />
                                            <Tooltip
                                                contentStyle={{
                                                    background: "#18181B",
                                                    border: "1px solid rgba(255,255,255,0.1)",
                                                    borderRadius: 8,
                                                    fontFamily: "IBM Plex Mono",
                                                    fontSize: 12,
                                                    color: "#fff",
                                                }}
                                            />
                                            <Bar dataKey="avg_wpm" fill="#3B82F6" radius={[0, 4, 4, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            <div className="tf-card p-6 lg:col-span-3">
                                <SectionLabel>Recent Runs</SectionLabel>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left font-mono text-sm" data-testid="history-table">
                                        <thead>
                                            <tr className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 border-b border-white/5">
                                                <th className="py-3 pr-4">Date</th>
                                                <th className="py-3 pr-4">Domain</th>
                                                <th className="py-3 pr-4">Topic</th>
                                                <th className="py-3 pr-4">Diff</th>
                                                <th className="py-3 pr-4 text-right">Wpm</th>
                                                <th className="py-3 pr-4 text-right">Acc</th>
                                                <th className="py-3 pr-4 text-right">Time</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {sessions.map((s) => (
                                                <tr
                                                    key={s.id}
                                                    onClick={() => navigate(`/results/${s.id}`)}
                                                    className="border-b border-white/5 hover:bg-white/[0.04] transition-colors cursor-pointer"
                                                >
                                                    <td className="py-3 pr-4 text-zinc-400">
                                                        {new Date(s.created_at).toLocaleString(undefined, {
                                                            month: "short",
                                                            day: "numeric",
                                                            hour: "2-digit",
                                                            minute: "2-digit",
                                                        })}
                                                    </td>
                                                    <td className="py-3 pr-4 text-blue-400">{s.domain}</td>
                                                    <td className="py-3 pr-4 text-zinc-200">
                                                        <div>{s.topic}</div>
                                                        {s.question && (
                                                            <div
                                                                title={s.question}
                                                                className="text-[11px] text-zinc-500 truncate max-w-[260px] mt-0.5"
                                                            >
                                                                Q: {s.question}
                                                            </div>
                                                        )}
                                                    </td>
                                                    <td className="py-3 pr-4 text-zinc-500">{s.difficulty}</td>
                                                    <td className="py-3 pr-4 text-right text-white">{s.wpm.toFixed(1)}</td>
                                                    <td className={`py-3 pr-4 text-right ${s.accuracy >= 95 ? "text-emerald-400" : "text-zinc-300"}`}>
                                                        {s.accuracy.toFixed(1)}%
                                                    </td>
                                                    <td className="py-3 pr-4 text-right text-zinc-500">
                                                        {s.duration_seconds.toFixed(1)}s
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </Layout>
    );
}


