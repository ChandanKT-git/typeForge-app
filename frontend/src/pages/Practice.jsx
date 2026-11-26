import React, { useEffect, useState, useCallback, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import Layout from "@/components/Layout";
import TypingArena from "@/components/TypingArena";
import { ArrowLeft, RotateCcw, Loader2, HelpCircle, Eye, Sparkles } from "lucide-react";
import { toast } from "sonner";

export default function Practice() {
    const location = useLocation();
    const navigate = useNavigate();
    const initial = location.state || {};
    const [text, setText] = useState(initial.text || "");
    const [question, setQuestion] = useState(initial.question || null);
    const [mode, setMode] = useState(initial.mode || (initial.question ? "qa" : "passage"));
    const [domain] = useState(initial.domain || "Programming");
    const [topic] = useState(initial.topic || "");
    const [difficulty] = useState(initial.difficulty || "Intermediate");
    const [length] = useState(initial.length || "medium");
    const [includeCode] = useState(!!initial.include_code);

    // "recall" phase shows only the question until user reveals the answer
    const [phase, setPhase] = useState(initial.question ? "recall" : "typing");
    const recallStartedAtRef = useRef(Date.now());
    const [recallMs, setRecallMs] = useState(null);

    const [live, setLive] = useState({ wpm: 0, accuracy: 100, elapsedSec: 0, progress: 0 });
    const [submitting, setSubmitting] = useState(false);
    const [loadingNew, setLoadingNew] = useState(false);
    const [arenaKey, setArenaKey] = useState(0);

    const handleLiveStats = useCallback((s) => {
        setLive({
            wpm: s.wpm,
            accuracy: s.accuracy,
            elapsedSec: s.elapsedSec,
            progress: s.progress,
        });
    }, []);

    useEffect(() => {
        if (!initial.text) {
            navigate("/dashboard");
        }
    }, [initial.text, navigate]);

    const revealAnswer = useCallback(() => {
        if (phase !== "recall") return;
        const elapsed = Math.max(0, Math.round(Date.now() - recallStartedAtRef.current));
        setRecallMs(elapsed);
        setPhase("typing");
    }, [phase]);

    // Allow pressing Enter or Space to reveal the answer during the recall phase
    useEffect(() => {
        if (phase !== "recall") return;
        const onKeyDown = (e) => {
            if (e.target?.tagName === "INPUT" || e.target?.tagName === "TEXTAREA") return;
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                revealAnswer();
            }
        };
        window.addEventListener("keydown", onKeyDown);
        return () => window.removeEventListener("keydown", onKeyDown);
    }, [phase, revealAnswer]);

    const onComplete = useCallback(
        async (result) => {
            if (submitting) return;
            setSubmitting(true);
            try {
                const payload = {
                    domain,
                    topic,
                    difficulty,
                    source_type: initial.source_type || (domain === "Custom Document" ? "document" : "ai"),
                    source_document_id: initial.source_document_id || null,
                    question: question || null,
                    recall_ms: recallMs,
                    target_text: text,
                    typed_text: result.typed,
                    duration_seconds: Number(result.durationSeconds.toFixed(2)),
                    wpm: Number(result.wpm.toFixed(1)),
                    raw_wpm: Number(result.rawWpm.toFixed(1)),
                    accuracy: Number(result.accuracy.toFixed(1)),
                    correct_chars: result.correctChars,
                    incorrect_chars: result.incorrectChars,
                    total_chars: result.totalChars,
                    error_chars: result.errorChars,
                    keystrokes: (result.keystrokes || []).map((k) => ({
                        t: Math.round(k.t),
                        correct: !!k.correct,
                    })),
                };
                const { data } = await api.post("/sessions", payload);
                navigate(`/results/${data.id}`, { replace: true });
            } catch (e) {
                toast.error("could not save your run.");
                setSubmitting(false);
            }
        },
        [submitting, domain, topic, difficulty, question, recallMs, text, navigate, initial.source_type, initial.source_document_id]
    );

    const restart = useCallback(() => {
        setArenaKey((k) => k + 1);
        setLive({ wpm: 0, accuracy: 100, elapsedSec: 0, progress: 0 });
    }, []);

    const newPassage = async () => {
        if (loadingNew) return;
        setLoadingNew(true);
        try {
            if (initial.source_document_id) {
                const { data } = await api.post("/documents/generate-drill", {
                    document_id: initial.source_document_id,
                    difficulty,
                    length,
                    bypass_cache: true,
                });
                setText(data.text);
                setQuestion(data.question || null);
                setMode(data.mode || (data.question ? "qa" : "passage"));
                recallStartedAtRef.current = Date.now();
                setRecallMs(null);
                setPhase(data.question ? "recall" : "typing");
                setLive({ wpm: 0, accuracy: 100, elapsedSec: 0, progress: 0 });
                setArenaKey((k) => k + 1);
            } else {
                const { data } = await api.post("/ai/generate", {
                    domain,
                    topic,
                    difficulty,
                    length,
                    include_code: includeCode,
                    bypass_cache: true,
                });
                setText(data.text);
                setQuestion(data.question || null);
                setMode(data.mode || (data.question ? "qa" : "passage"));
                recallStartedAtRef.current = Date.now();
                setRecallMs(null);
                setPhase(data.question ? "recall" : "typing");
                setLive({ wpm: 0, accuracy: 100, elapsedSec: 0, progress: 0 });
                setArenaKey((k) => k + 1);
            }
        } catch (e) {
            toast.error("Could not generate a new question.");
        } finally {
            setLoadingNew(false);
        }
    };

    if (!text) {
        return (
            <Layout hideNav>
                <div className="min-h-screen grid place-items-center text-zinc-500 font-mono">
                    <Loader2 className="h-5 w-5 animate-spin" />
                </div>
            </Layout>
        );
    }

    const isQaMode = mode === "qa" || Boolean(question);

    return (
        <Layout hideNav>
            <div className="min-h-screen flex flex-col">
                {/* Top bar */}
                <div className="border-b border-white/5">
                    <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
                        <button
                            onClick={() => navigate(initial.source_type === "document" ? "/documents" : "/dashboard")}
                            data-testid="practice-back"
                            className="flex items-center gap-2 text-xs font-mono text-zinc-400 hover:text-white"
                        >
                            <ArrowLeft className="h-3.5 w-3.5" />
                            Back
                        </button>
                        <div className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono flex items-center">
                            <span className={domain === "Custom Document" ? "text-emerald-400 font-medium" : "text-blue-400"}>
                                {domain}
                            </span>
                            <span className="mx-2 text-zinc-600">/</span>
                            <span className="text-white truncate max-w-[220px] inline-block" title={topic}>
                                {topic}
                            </span>
                            <span className="mx-2 text-zinc-600">/</span>
                            <span>{difficulty}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            {phase === "typing" && (
                                <button
                                    onClick={restart}
                                    data-testid="practice-restart"
                                    className="flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-white px-3 py-1.5 rounded-md hover:bg-white/5"
                                >
                                    <RotateCcw className="h-3.5 w-3.5" />
                                    Restart
                                </button>
                            )}
                            <button
                                onClick={newPassage}
                                disabled={loadingNew}
                                data-testid="practice-new-passage"
                                className="flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-white disabled:opacity-50 px-3 py-1.5 rounded-md hover:bg-white/5"
                            >
                                {loadingNew && <Loader2 className="h-3 w-3 animate-spin" />}
                                {isQaMode ? "New Question" : "New Passage"}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Live HUD */}
                <div className="max-w-5xl w-full mx-auto px-6 pt-8">
                    <div className="flex items-center gap-6 text-xs font-mono text-zinc-500">
                        <Hud label="WPM" value={Math.round(live.wpm || 0)} accent="blue" />
                        <Hud label="ACC" value={`${Math.round(live.accuracy || 0)}%`} accent={live.accuracy >= 95 ? "green" : "white"} />
                        <Hud label="TIME" value={`${(live.elapsedSec || 0).toFixed(1)}s`} />
                        <div className="flex-1">
                            <div className="h-1 rounded-full bg-white/5 overflow-hidden">
                                <div
                                    className="h-full bg-blue-500 transition-all"
                                    style={{ width: `${Math.min(100, (live.progress || 0) * 100)}%` }}
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Main Practice Area: Recall Phase vs Typing Phase */}
                <div className="flex-1 grid place-items-center px-6 py-10">
                    <div className="max-w-4xl w-full space-y-6">
                        {phase === "recall" && question ? (
                            <div
                                data-testid="qa-recall-card"
                                className="tf-card p-8 border-blue-500/30 bg-blue-500/[0.03] space-y-6"
                            >
                                <div className="flex items-center justify-between gap-3">
                                    <span className="inline-flex items-center gap-2 text-[10px] uppercase tracking-[0.25em] font-mono text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2.5 py-1 rounded-md">
                                        <Sparkles className="h-3 w-3" />
                                        Step 1 of 2 · Think First (Active Recall)
                                    </span>
                                    <span className="text-[11px] font-mono text-zinc-500">
                                        {text.split(/\s+/).filter(Boolean).length} words in model answer
                                    </span>
                                </div>

                                <div className="space-y-2">
                                    <div className="text-xs font-mono uppercase tracking-wider text-zinc-500">
                                        Concept Question
                                    </div>
                                    <h2
                                        data-testid="qa-question-text"
                                        className="font-mono text-xl sm:text-2xl text-white leading-relaxed"
                                    >
                                        {question}
                                    </h2>
                                </div>

                                {/* Non-leaking answer placeholder skeleton */}
                                <div className="rounded-xl border border-white/10 bg-[#09090b]/70 p-6 space-y-4">
                                    <div className="space-y-2.5" aria-hidden="true">
                                        <div className="h-3.5 w-11/12 rounded bg-white/[0.06]" />
                                        <div className="h-3.5 w-full rounded bg-white/[0.05]" />
                                        <div className="h-3.5 w-4/5 rounded bg-white/[0.04]" />
                                    </div>

                                    <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-t border-white/5">
                                        <p className="text-xs font-mono text-zinc-400">
                                            Formulate your answer mentally, then reveal the model answer to type it.
                                        </p>
                                        <button
                                            type="button"
                                            onClick={revealAnswer}
                                            data-testid="reveal-answer-btn"
                                            className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 font-mono text-xs glow-blue transition-colors shrink-0"
                                        >
                                            <Eye className="h-3.5 w-3.5" />
                                            Reveal Answer & Type
                                            <kbd className="ml-1 rounded border border-white/20 bg-black/20 px-1.5 py-0.5 text-[10px]">
                                                Enter
                                            </kbd>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <>
                                {question && (
                                    <div
                                        data-testid="qa-pinned-question"
                                        className="tf-card px-5 py-4 border-blue-500/20 bg-blue-500/[0.02] flex items-start gap-3"
                                    >
                                        <HelpCircle className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />
                                        <div className="space-y-1">
                                            <div className="text-[10px] uppercase tracking-[0.2em] font-mono text-blue-400">
                                                Question Prompt
                                            </div>
                                            <div
                                                data-testid="qa-question-text"
                                                className="font-mono text-sm sm:text-base text-zinc-100 leading-snug"
                                            >
                                                {question}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                <TypingArena
                                    key={arenaKey}
                                    text={text}
                                    onLiveStats={handleLiveStats}
                                    onComplete={onComplete}
                                    onRestartRequest={restart}
                                    finished={submitting}
                                />
                            </>
                        )}
                    </div>
                </div>

                <div className="pb-10 text-center text-[11px] font-mono text-zinc-600">
                    {phase === "recall"
                        ? "Think First · Press Enter Or Space To Reveal Answer"
                        : "Just Start Typing · Esc To Restart"}
                </div>
            </div>
        </Layout>
    );
}

function Hud({ label, value, accent }) {
    const colorMap = {
        blue: "text-blue-400",
        green: "text-emerald-400",
        white: "text-white",
    };
    return (
        <div className="flex items-baseline gap-2">
            <span className="text-[10px] uppercase tracking-[0.2em] text-zinc-500">{label}</span>
            <span className={`font-mono text-2xl ${colorMap[accent] || "text-white"}`}>
                {value}
            </span>
        </div>
    );
}
