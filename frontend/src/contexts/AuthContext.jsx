import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import api, { setAuthToken } from "@/lib/api";

const AuthContext = createContext({ user: null, loading: true });

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    const refresh = useCallback(async () => {
        try {
            const { data } = await api.get("/auth/me");
            setUser(data);
        } catch (e) {
            setUser(false);
            setAuthToken(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        refresh();
    }, [refresh]);

    const login = async (email, password) => {
        const { data } = await api.post("/auth/login", { email, password });
        if (data.token) setAuthToken(data.token);
        setUser(data.user);
        return data.user;
    };

    const register = async (email, password, name) => {
        const { data } = await api.post("/auth/register", { email, password, name });
        if (data.token) setAuthToken(data.token);
        setUser(data.user);
        return data.user;
    };

    const logout = async () => {
        try {
            await api.post("/auth/logout");
        } catch (e) {
            /* ignore */
        }
        setAuthToken(null);
        setUser(false);
    };

    const googleLogin = async (credential) => {
        const { data } = await api.post("/auth/google", { credential });
        if (data.token) setAuthToken(data.token);
        setUser(data.user);
        return data.user;
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout, googleLogin, refresh }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}

export function formatApiErrorDetail(detail) {
    if (detail == null) return "Something went wrong. Please try again.";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail))
        return detail
            .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
            .filter(Boolean)
            .join(" ");
    if (detail && typeof detail.msg === "string") return detail.msg;
    return String(detail);
}
