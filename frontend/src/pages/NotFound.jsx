import React from "react";
import { Link } from "react-router-dom";
import Layout from "@/components/Layout";
import { ArrowLeft, TerminalSquare } from "lucide-react";

export default function NotFound() {
    return (
        <Layout hideNav>
            <div className="min-h-[80vh] flex flex-col items-center justify-center p-6 text-center animate-fade-up">
                <div className="w-20 h-20 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-8 text-zinc-400">
                    <TerminalSquare className="h-10 w-10" />
                </div>
                
                <h1 className="font-mono text-6xl text-white tracking-tighter mb-4">
                    404
                </h1>
                
                <div className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono mb-4">
                    File Not Found
                </div>
                
                <p className="text-sm text-zinc-400 font-mono max-w-sm mb-10 leading-relaxed">
                    The requested path does not exist in this directory. It may have been moved, deleted, or you might have mistyped the URL.
                </p>
                
                <Link
                    to="/"
                    className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 font-mono text-sm glow-blue transition-colors"
                >
                    <ArrowLeft className="h-4 w-4" />
                    Return To Base
                </Link>
            </div>
        </Layout>
    );
}
