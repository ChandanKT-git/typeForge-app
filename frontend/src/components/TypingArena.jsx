import React, { useEffect, useMemo, useRef, useState, useCallback, useLayoutEffect } from "react";
import { motion } from "framer-motion";
import { useSound } from "@/hooks/useSound";

/**
 * TypingArena
 * - Tracks typed string against target word-by-word.
 * - Renders character classes (correct/incorrect/untyped/current) and a caret.
 * - Emits onComplete({ typed, durationSeconds, wpm, rawWpm, accuracy, ... }) when finished.
 * - Live stats via onLiveStats callback.
 */
export default function TypingArena({
    text,
    onComplete,
    onLiveStats,
    onRestartRequest,
    finished = false,
}) {
    const [typed, setTyped] = useState("");
    const [startedAt, setStartedAt] = useState(null);
    const [now, setNow] = useState(Date.now());
    const containerRef = useRef(null);
    const inputRef = useRef(null);
    const completedRef = useRef(false);
    const keystrokesRef = useRef([]);
    const mistypedIndices = useRef(new Set());
    const { playClick, playError } = useSound();

    useEffect(() => {
        setTyped("");
        setStartedAt(null);
        setNow(Date.now());
        completedRef.current = false;
        keystrokesRef.current = [];
        mistypedIndices.current.clear();
        setTimeout(() => inputRef.current?.focus(), 50);
    }, [text]);

    // Tick live stats
    useEffect(() => {
        if (!startedAt || finished) return;
        const id = setInterval(() => setNow(Date.now()), 200);
        return () => clearInterval(id);
    }, [startedAt, finished]);

    const stats = useMemo(() => {
        let correct = 0; 
        let strictCorrect = 0;
        let incorrect = 0;
        const errorChars = [];
        for (let i = 0; i < typed.length; i++) {
            const t = typed[i];
            const target = text[i];
            if (t === target) {
                correct++;
                if (!mistypedIndices.current.has(i)) {
                    strictCorrect++;
                }
            }
            else {
                incorrect++;
                if (target) errorChars.push(target);
            }
        }
        const total = typed.length;
        const elapsedSec = startedAt ? Math.max(0.001, (now - startedAt) / 1000) : 0;
        const wpm = elapsedSec > 0 ? (correct / 5) / (elapsedSec / 60) : 0;
        const rawWpm = elapsedSec > 0 ? (total / 5) / (elapsedSec / 60) : 0;
        const accuracy = total > 0 ? (strictCorrect / total) * 100 : 100;
        return {
            correct,
            incorrect,
            total,
            elapsedSec,
            wpm,
            rawWpm,
            accuracy,
            errorChars,
            progress: total / text.length,
        };
    }, [typed, text, startedAt, now]);

    useEffect(() => {
        if (onLiveStats) onLiveStats(stats);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [stats.wpm, stats.accuracy, stats.elapsedSec, stats.progress, stats.total]);

    // Detect finish
    useEffect(() => {
        if (
            !completedRef.current &&
            typed.length >= text.length &&
            text.length > 0 &&
            startedAt
        ) {
            completedRef.current = true;
            const finalStats = stats;
            onComplete?.({
                typed,
                durationSeconds: finalStats.elapsedSec,
                wpm: finalStats.wpm,
                rawWpm: finalStats.rawWpm,
                accuracy: finalStats.accuracy,
                correctChars: finalStats.correct,
                incorrectChars: finalStats.incorrect,
                totalChars: finalStats.total,
                errorChars: finalStats.errorChars,
                keystrokes: keystrokesRef.current.slice(0, 2000),
            });
        }
    }, [typed, text, startedAt, stats, onComplete]);

    const handleChange = useCallback(
        (e) => {
            if (finished) return;
            const start = startedAt || Date.now();
            if (!startedAt) setStartedAt(start);

            const newVal = e.target.value;
            if (newVal.length < typed.length) {
                setTyped(newVal);
            } else if (newVal.length > typed.length) {
                const added = newVal.slice(typed.length);
                let current = typed;
                for (let i = 0; i < added.length; i++) {
                    if (current.length >= text.length) break;
                    const char = added[i];
                    const expected = text[current.length];
                    const correct = char === expected;
                    
                    if (correct) {
                        playClick();
                    } else {
                        playError();
                        mistypedIndices.current.add(current.length);
                    }
                    
                    keystrokesRef.current.push({
                        t: Math.max(0, Date.now() - start),
                        correct,
                    });
                    current += char;
                }
                setTyped(current);
            }
        },
        [finished, startedAt, typed, text, playClick, playError]
    );

    const handleKeyDown = useCallback(
        (e) => {
            if (finished) return;
            if (e.key === "Escape") {
                e.preventDefault();
                onRestartRequest?.();
                return;
            }
        },
        [finished, onRestartRequest]
    );

    return (
        <div
            ref={containerRef}
            data-testid="typing-arena"
            className="relative w-full select-none"
            onClick={() => inputRef.current?.focus()}
        >
            {/* Hidden focusable to capture keystrokes reliably on desktop and mobile */}
            <textarea
                ref={inputRef}
                value={typed}
                onChange={handleChange}
                onKeyDown={handleKeyDown}
                aria-label="Typing Input"
                data-testid="typing-input"
                autoFocus
                autoCapitalize="none"
                autoComplete="off"
                autoCorrect="off"
                spellCheck="false"
                className="absolute opacity-0 pointer-events-none w-px h-px overflow-hidden -z-10"
            />

            <TypingText text={text} typed={typed} finished={finished} mistypedIndices={mistypedIndices.current} />

            <div className="mt-8 flex items-center justify-between text-xs font-mono text-zinc-500">
                <span data-testid="typing-progress">
                    {Math.min(typed.length, text.length)} / {text.length} chars
                </span>
                <span className="hidden sm:flex items-center gap-2">
                    <Kbd>Esc</Kbd> Restart
                </span>
            </div>
        </div>
    );
}

function Kbd({ children }) {
    return (
        <kbd className="rounded border border-white/10 bg-white/[0.03] px-1.5 py-0.5 text-[10px] font-mono text-zinc-400">
            {children}
        </kbd>
    );
}

function TypingText({ text, typed, finished, mistypedIndices }) {
    const chars = useMemo(() => text.split(""), [text]);

    return (
        <div
            className="relative font-mono text-2xl sm:text-3xl leading-[1.7] tracking-normal text-zinc-500 whitespace-pre-wrap"
            data-testid="typing-text"
        >
            <AnimatedCaret typed={typed} text={text} finished={finished} />
            {chars.map((ch, i) => {
                const t = typed[i];
                let cls = "tf-letter tf-letter--untyped";
                if (i < typed.length) {
                    if (t !== ch) {
                        cls = "tf-letter tf-letter--incorrect";
                    } else if (mistypedIndices && mistypedIndices.has(i)) {
                        cls = "tf-letter tf-letter--corrected";
                    } else {
                        cls = "tf-letter tf-letter--correct";
                    }
                }
                return (
                    <span key={i} className={cls} data-testid={`char-${i}`}>
                        {ch}
                    </span>
                );
            })}
        </div>
    );
}

function AnimatedCaret({ typed, text, finished }) {
    const [pos, setPos] = useState({ x: 0, y: 0 });
    const isFirstRender = useRef(true);

    useLayoutEffect(() => {
        if (finished) return;
        
        const updatePos = () => {
            const charId = Math.min(typed.length, text.length - 1);
            const el = document.querySelector(`[data-testid="char-${charId}"]`);
            if (el) {
                let x = el.offsetLeft;
                let y = el.offsetTop;
                if (typed.length >= text.length) {
                    x += el.offsetWidth;
                }
                setPos({ x: x - 1, y: y + 2 });
            }
        };

        if (isFirstRender.current) {
            isFirstRender.current = false;
            // Let the browser paint first to get accurate offset measurements
            setTimeout(updatePos, 10);
        } else {
            updatePos();
        }

        window.addEventListener("resize", updatePos);
        return () => window.removeEventListener("resize", updatePos);
    }, [typed.length, text.length, finished]);

    if (finished) return null;

    return (
        <motion.span
            className="tf-caret"
            initial={false}
            animate={{ x: pos.x, y: pos.y }}
            transition={{ type: "spring", stiffness: 800, damping: 50, mass: 0.5 }}
        />
    );
}
