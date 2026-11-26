import React, { useState } from "react";
import Layout from "@/components/Layout";
import { useAuth, formatApiErrorDetail } from "@/contexts/AuthContext";
import { toast } from "sonner";
import api from "@/lib/api";
import { SectionLabel } from "@/components/SharedUI";
import { Save, User, Target, Lock, Loader2 } from "lucide-react";

export default function Settings() {
    const { user, refresh } = useAuth();
    
    const [name, setName] = useState(user?.name || "");
    const [goal, setGoal] = useState(user?.daily_goal || 3);
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);

    const onSave = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const payload = {};
            if (name.trim() !== user?.name) payload.name = name;
            if (Number(goal) !== user?.daily_goal) payload.daily_goal = Number(goal);
            if (password) payload.password = password;
            
            if (Object.keys(payload).length === 0) {
                toast("No changes to save.");
                setLoading(false);
                return;
            }
            
            await api.put("/auth/me", payload);
            await refresh();
            toast.success("Profile updated successfully.");
            setPassword("");
        } catch (e) {
            toast.error(formatApiErrorDetail(e.response?.data?.detail));
        } finally {
            setLoading(false);
        }
    };

    return (
        <Layout>
            <div className="max-w-xl mx-auto px-6 py-12 animate-fade-up">
                <div className="mb-10">
                    <p className="text-[10px] uppercase tracking-[0.25em] text-zinc-500 font-mono mb-2">
                        Preferences
                    </p>
                    <h1 className="font-mono text-3xl sm:text-4xl text-white tracking-tight">
                        User Settings
                    </h1>
                </div>

                <form onSubmit={onSave} className="space-y-8">
                    <div className="tf-card p-6">
                        <SectionLabel icon={<User className="h-4 w-4" />}>Profile Info</SectionLabel>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs font-mono text-zinc-400 mb-1.5">
                                    Display Name
                                </label>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="Your Name"
                                    className="w-full rounded-md border border-white/10 bg-white/5 px-4 py-2.5 font-mono text-sm text-white placeholder-zinc-600 focus:border-blue-500/50 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-colors"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-mono text-zinc-400 mb-1.5">
                                    Email Address
                                </label>
                                <input
                                    type="text"
                                    value={user?.email || ""}
                                    disabled
                                    className="w-full rounded-md border border-white/5 bg-white/[0.02] px-4 py-2.5 font-mono text-sm text-zinc-500 cursor-not-allowed"
                                />
                                <p className="text-[10px] text-zinc-500 mt-1 font-mono">
                                    Email Cannot Be Changed At This Time.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="tf-card p-6">
                        <SectionLabel icon={<Target className="h-4 w-4" />}>Training Goals</SectionLabel>
                        <div>
                            <label className="block text-xs font-mono text-zinc-400 mb-1.5">
                                Daily Runs Goal
                            </label>
                            <input
                                type="number"
                                min="1"
                                max="100"
                                value={goal}
                                onChange={(e) => setGoal(e.target.value)}
                                className="w-full rounded-md border border-white/10 bg-white/5 px-4 py-2.5 font-mono text-sm text-white focus:border-blue-500/50 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-colors"
                            />
                            <p className="text-[10px] text-zinc-500 mt-1.5 font-mono">
                                Recommended: 3-5 Runs Per Day To Maintain Streak.
                            </p>
                        </div>
                    </div>

                    <div className="tf-card p-6">
                        <SectionLabel icon={<Lock className="h-4 w-4" />}>Security</SectionLabel>
                        <div>
                            <label className="block text-xs font-mono text-zinc-400 mb-1.5">
                                New Password
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Leave blank to keep current"
                                className="w-full rounded-md border border-white/10 bg-white/5 px-4 py-2.5 font-mono text-sm text-white placeholder-zinc-600 focus:border-blue-500/50 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-colors"
                            />
                        </div>
                    </div>

                    <div className="flex justify-end pt-4">
                        <button
                            type="submit"
                            disabled={loading}
                            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-6 py-2.5 font-mono text-sm glow-blue transition-colors"
                        >
                            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                            save changes
                        </button>
                    </div>
                </form>
            </div>
        </Layout>
    );
}
