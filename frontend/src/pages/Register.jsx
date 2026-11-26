import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth, formatApiErrorDetail } from "@/contexts/AuthContext";
import { Keyboard, ArrowRight, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { GoogleLogin } from "@react-oauth/google";

export default function Register() {
    const { register, googleLogin } = useAuth();
    const navigate = useNavigate();
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [err, setErr] = useState("");

    const onSubmit = async (e) => {
        e.preventDefault();
        setErr("");
        setLoading(true);
        try {
            await register(email.trim(), password, name.trim());
            toast.success("account created.");
            navigate("/dashboard", { replace: true });
        } catch (ex) {
            setErr(formatApiErrorDetail(ex.response?.data?.detail) || ex.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="tf-shell min-h-screen grid lg:grid-cols-2">
            <div className="flex items-center justify-center p-8 order-2 lg:order-1">
                <form
                    onSubmit={onSubmit}
                    data-testid="register-form"
                    className="w-full max-w-sm space-y-6"
                >
                    <div>
                        <h1 className="font-mono text-3xl text-white tracking-tight">
                            Create Account
                        </h1>
                        <p className="mt-2 text-sm text-zinc-500">
                            Forge Your Typing Skills With AI-curated Content.
                        </p>
                    </div>

                    <div className="space-y-3">
                        <Field
                            id="name"
                            label="Display Name"
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            testid="register-name"
                            autoComplete="name"
                            placeholder="Optional"
                        />
                        <Field
                            id="email"
                            label="Email"
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            testid="register-email"
                            autoComplete="email"
                        />
                        <Field
                            id="password"
                            label="Password (min 6 Chars)"
                            type="password"
                            required
                            minLength={6}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            testid="register-password"
                            autoComplete="new-password"
                        />
                    </div>

                    {err && (
                        <div
                            data-testid="register-error"
                            className="text-xs font-mono text-rose-400 border border-rose-500/30 bg-rose-500/5 rounded-md px-3 py-2"
                        >
                            {err}
                        </div>
                    )}

                    <button
                        type="submit"
                        data-testid="register-submit"
                        disabled={loading}
                        className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-4 py-3 font-mono text-sm glow-blue transition-colors"
                    >
                        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                        create account
                    </button>

                    <div className="flex items-center gap-4 py-2">
                        <div className="h-px bg-white/10 flex-1"></div>
                        <span className="text-xs font-mono text-zinc-500">Or Continue With</span>
                        <div className="h-px bg-white/10 flex-1"></div>
                    </div>

                    <div className="flex justify-center">
                        <GoogleLogin
                            onSuccess={async (res) => {
                                try {
                                    await googleLogin(res.credential);
                                    toast.success("Account created.");
                                    navigate("/dashboard", { replace: true });
                                } catch (e) {
                                    toast.error("Google login failed");
                                }
                            }}
                            onError={() => toast.error("Google login failed")}
                            theme="filled_black"
                            shape="pill"
                            text="signup_with"
                        />
                    </div>

                    <p className="text-xs font-mono text-zinc-500 text-center">
                        already registered?{" "}
                        <Link to="/login" data-testid="register-to-login" className="text-blue-400 hover:text-blue-300">
                            Sign In
                        </Link>
                    </p>
                </form>
            </div>

            <div className="hidden lg:flex relative overflow-hidden border-l border-white/5 order-1 lg:order-2">
                <div className="absolute inset-0 bg-grid-faint opacity-40" />
                <div className="absolute inset-0 bg-grid-fade" />
                <div className="relative p-12 flex flex-col justify-between w-full">
                    <Link to="/" className="flex items-center gap-2">
                        <span className="h-7 w-7 rounded-md bg-blue-600/15 border border-blue-500/30 grid place-items-center">
                            <Keyboard className="h-4 w-4 text-blue-400" />
                        </span>
                        <span className="font-mono text-sm">
                            <span className="text-white">Type</span>
                            <span className="text-blue-400">Forge</span>
                        </span>
                    </Link>
                    <div>
                        <p className="font-mono text-2xl text-white leading-relaxed max-w-md">
                            "Gradient descent updates weights along the negative gradient of the loss."
                        </p>
                        <p className="mt-4 text-zinc-500 text-sm font-mono">
                            AI/ML · Gradient Descent · Advanced
                        </p>
                    </div>
                    <div className="text-xs font-mono text-zinc-600">
                        Join Engineers Who Type Faster Than They Think.
                    </div>
                </div>
            </div>
        </div>
    );
}

function Field({ id, label, testid, ...props }) {
    return (
        <div>
            <label
                htmlFor={id}
                className="block text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono mb-2"
            >
                {label}
            </label>
            <input
                id={id}
                data-testid={testid}
                className="w-full bg-zinc-900/60 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/50 transition-all font-mono text-sm"
                {...props}
            />
        </div>
    );
}
