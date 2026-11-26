import React from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useSound } from "@/hooks/useSound";
import { LogOut, Keyboard, BarChart3, Sparkles, Volume2, VolumeX, Settings, BookOpen } from "lucide-react";

export default function Layout({ children, hideNav = false }) {
    const { user, logout } = useAuth();
    const { enabled, toggle } = useSound();
    const navigate = useNavigate();

    const onLogout = async () => {
        await logout();
        navigate("/login");
    };

    return (
        <div className="tf-shell">
            {!hideNav && (
                <header
                    data-testid="app-header"
                    className="sticky top-0 z-40 border-b border-white/5 bg-[#09090b]/80 backdrop-blur-xl"
                >
                    <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
                        <Link
                            to="/dashboard"
                            data-testid="nav-logo"
                            className="flex items-center gap-2 group"
                        >
                            <span className="h-7 w-7 rounded-md bg-blue-600/15 border border-blue-500/30 grid place-items-center">
                                <Keyboard className="h-4 w-4 text-blue-400" />
                            </span>
                            <span className="font-mono text-sm tracking-tight">
                                <span className="text-white">Type</span>
                                <span className="text-blue-400">Forge</span>
                            </span>
                        </Link>
                        <nav className="hidden md:flex items-center gap-1 text-sm font-mono">
                            <NavItem to="/dashboard" testid="nav-dashboard" icon={<Sparkles className="h-3.5 w-3.5" />}>
                                Practice
                            </NavItem>
                            <NavItem to="/documents" testid="nav-documents" icon={<BookOpen className="h-3.5 w-3.5" />}>
                                Documents
                            </NavItem>
                            <NavItem to="/history" testid="nav-history" icon={<BarChart3 className="h-3.5 w-3.5" />}>
                                History
                            </NavItem>
                        </nav>
                        <div className="flex items-center gap-3">
                            <span
                                data-testid="user-email"
                                className="hidden sm:inline text-xs text-zinc-500 font-mono border-r border-white/10 pr-3 mr-1"
                            >
                                {user?.email}
                            </span>
                            <button
                                onClick={toggle}
                                title={enabled ? "Mute typing sounds" : "Enable typing sounds"}
                                className="text-zinc-400 hover:text-white px-2 py-1.5 rounded-md hover:bg-white/5 transition-colors"
                            >
                                {enabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
                            </button>
                            <Link
                                to="/settings"
                                data-testid="nav-settings"
                                className="text-zinc-400 hover:text-white px-2 py-1.5 rounded-md hover:bg-white/5 transition-colors"
                            >
                                <Settings className="h-4 w-4" />
                            </Link>
                            <button
                                data-testid="logout-btn"
                                onClick={onLogout}
                                className="flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-white px-3 py-1.5 rounded-md hover:bg-white/5 transition-colors"
                            >
                                <LogOut className="h-3.5 w-3.5" />
                                Sign Out
                            </button>
                        </div>
                    </div>
                </header>
            )}
            <main>{children}</main>
        </div>
    );
}

function NavItem({ to, children, icon, testid }) {
    return (
        <NavLink
            to={to}
            data-testid={testid}
            className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors ${
                    isActive ? "text-white bg-white/5" : "text-zinc-500 hover:text-zinc-200"
                }`
            }
        >
            {icon}
            {children}
        </NavLink>
    );
}
