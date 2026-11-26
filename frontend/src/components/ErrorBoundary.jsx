import React from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import Layout from "./Layout";

export default class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        console.error("ErrorBoundary caught an error", error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }
            return (
                <Layout hideNav>
                    <div className="min-h-[80vh] flex flex-col items-center justify-center p-6 text-center">
                        <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mb-6 text-rose-400">
                            <AlertTriangle className="h-8 w-8" />
                        </div>
                        <h1 className="text-2xl font-mono text-white mb-2 tracking-tight">
                            System Failure
                        </h1>
                        <p className="text-zinc-500 font-mono text-sm max-w-md mb-8">
                            {this.state.error?.message || "An unexpected error occurred in the Typeforge matrix."}
                        </p>
                        <button
                            onClick={() => window.location.href = "/dashboard"}
                            className="flex items-center gap-2 bg-white/5 hover:bg-white/10 text-white px-4 py-2 rounded-lg font-mono text-sm transition-colors"
                        >
                            <RotateCcw className="h-4 w-4" />
                            Restart Matrix
                        </button>
                    </div>
                </Layout>
            );
        }
        return this.props.children;
    }
}
