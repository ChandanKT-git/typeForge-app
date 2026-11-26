import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

export default function ProtectedRoute({ children }) {
    const { user, loading } = useAuth();
    const location = useLocation();

    if (loading || user === null) {
        return (
            <div
                data-testid="auth-loading"
                className="min-h-screen flex items-center justify-center text-zinc-500 font-mono"
            >
                <div className="flex items-center gap-3">
                    <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                Booting your arena....
                </div>
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/login" replace state={{ from: location }} />;
    }

    return children;
}
