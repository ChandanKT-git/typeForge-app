import React, { Suspense, lazy } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { Loader2 } from "lucide-react";

import { AuthProvider } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import ErrorBoundary from "@/components/ErrorBoundary";

const Landing = lazy(() => import("@/pages/Landing"));
const Login = lazy(() => import("@/pages/Login"));
const Register = lazy(() => import("@/pages/Register"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Practice = lazy(() => import("@/pages/Practice"));
const Results = lazy(() => import("@/pages/Results"));
const History = lazy(() => import("@/pages/History"));
const NotFound = lazy(() => import("@/pages/NotFound"));
const Settings = lazy(() => import("@/pages/Settings"));
const DocumentLibrary = lazy(() => import("@/pages/DocumentLibrary"));

function App() {
    return (
        <div className="dark">
            <AuthProvider>
                <BrowserRouter>
                    <ErrorBoundary>
                        <Suspense
                            fallback={
                                <div className="min-h-screen bg-[#09090B] flex items-center justify-center">
                                    <Loader2 className="h-6 w-6 text-zinc-500 animate-spin" />
                                </div>
                            }
                        >
                            <Routes>
                                <Route path="/" element={<Landing />} />
                                <Route path="/login" element={<Login />} />
                                <Route path="/register" element={<Register />} />
                                <Route
                                    path="/dashboard"
                                    element={
                                        <ProtectedRoute>
                                            <Dashboard />
                                        </ProtectedRoute>
                                    }
                                />
                                <Route
                                    path="/practice"
                                    element={
                                        <ProtectedRoute>
                                            <Practice />
                                        </ProtectedRoute>
                                    }
                                />
                                <Route
                                    path="/results/:sessionId"
                                    element={
                                        <ProtectedRoute>
                                            <Results />
                                        </ProtectedRoute>
                                    }
                                />
                                <Route
                                    path="/history"
                                    element={
                                        <ProtectedRoute>
                                            <History />
                                        </ProtectedRoute>
                                    }
                                />
                                <Route
                                    path="/settings"
                                    element={
                                        <ProtectedRoute>
                                            <Settings />
                                        </ProtectedRoute>
                                    }
                                />
                                <Route
                                    path="/documents"
                                    element={
                                        <ProtectedRoute>
                                            <DocumentLibrary />
                                        </ProtectedRoute>
                                    }
                                />
                                <Route
                                    path="/documents/:docId"
                                    element={
                                        <ProtectedRoute>
                                            <DocumentLibrary />
                                        </ProtectedRoute>
                                    }
                                />
                                <Route path="*" element={<NotFound />} />
                            </Routes>
                        </Suspense>
                    </ErrorBoundary>
                </BrowserRouter>
                <Toaster
                    theme="dark"
                    position="bottom-right"
                    toastOptions={{
                        style: {
                            background: "#18181B",
                            border: "1px solid rgba(255,255,255,0.08)",
                            color: "#FAFAFA",
                            fontFamily: "Inter, sans-serif",
                        },
                    }}
                />
            </AuthProvider>
        </div>
    );
}

export default App;
