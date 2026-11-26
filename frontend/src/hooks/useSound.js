import { useState, useCallback, useEffect } from "react";

let audioCtx = null;

const getAudioContext = () => {
    if (typeof window !== "undefined" && !audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx?.state === "suspended") {
        audioCtx.resume();
    }
    return audioCtx;
};

export function useSound() {
    const [enabled, setEnabled] = useState(() => {
        return localStorage.getItem("tf_sound") === "true";
    });

    const toggle = useCallback(() => {
        setEnabled((prev) => {
            const next = !prev;
            localStorage.setItem("tf_sound", next);
            if (next) getAudioContext();
            return next;
        });
    }, []);

    const playClick = useCallback(() => {
        if (!enabled) return;
        const ctx = getAudioContext();
        if (!ctx) return;

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        // A pleasant, short "thock" sound
        osc.type = "sine";
        osc.frequency.setValueAtTime(150, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(40, ctx.currentTime + 0.04);

        gain.gain.setValueAtTime(0.15, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.04);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start();
        osc.stop(ctx.currentTime + 0.04);
    }, [enabled]);

    const playError = useCallback(() => {
        if (!enabled) return;
        const ctx = getAudioContext();
        if (!ctx) return;

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        // A dull error "thud/buzz"
        osc.type = "triangle";
        osc.frequency.setValueAtTime(120, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(80, ctx.currentTime + 0.1);

        gain.gain.setValueAtTime(0.2, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start();
        osc.stop(ctx.currentTime + 0.1);
    }, [enabled]);

    return { enabled, toggle, playClick, playError };
}
