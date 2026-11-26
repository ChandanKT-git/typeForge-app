import React from "react";

export function SectionLabel({ children, icon, className = "" }) {
    return (
        <div className={`text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono mb-4 flex items-center gap-1.5 ${className}`}>
            {icon && <span className="text-blue-400">{icon}</span>}
            {children}
        </div>
    );
}

export function BigStat({ label, value, accent }) {
    const colorMap = {
        blue: "text-blue-400",
        green: "text-emerald-400",
        amber: "text-amber-400",
        rose: "text-rose-400",
    };
    return (
        <div className="tf-card p-5">
            <div className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono">
                {label}
            </div>
            <div className={`mt-2 font-mono text-3xl tracking-tight ${colorMap[accent] || "text-white"}`}>
                {value}
            </div>
        </div>
    );
}

export function Skeleton({ className = "" }) {
    return (
        <div className={`animate-pulse rounded-md bg-white/5 ${className}`} />
    );
}
