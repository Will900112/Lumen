"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login, googleAuthorize, getToken } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LumenLogo } from "@/components/LumenLogo";

export default function LoginPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [notice, setNotice] = useState("");

    useEffect(() => {
        if (getToken()) {
            router.replace("/questionnaire");
            return;
        }
        const params = new URLSearchParams(window.location.search);
        if (params.get("expired")) {
            setNotice("Your session has expired. Please sign in again.");
        }
    }, [router]);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setLoading(true);
        setError("");
        try {
            await login(email, password);
            router.push("/questionnaire");
        } catch {
            setError("Invalid email or password.");
            setLoading(false);
        }
    }

    async function handleGoogle() {
        try {
            const url = await googleAuthorize();
            window.location.href = url;
        } catch {
            setError("Google login failed. Please try again.");
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center px-4">
            <header className="absolute top-0 left-0 right-0 z-30 bg-white/80 backdrop-blur-md border-b border-stone-200/60">
                <div className="max-w-6xl mx-auto flex items-center px-6 py-4">
                    <Link href="/" className="flex items-center gap-3 font-bold text-stone-900 text-2xl tracking-tight">
                        <LumenLogo />
                        Lumen
                    </Link>
                </div>
            </header>
            <div className="w-full max-w-md">
                {/* Hero */}
                <div className="text-center mb-8">
                    <div className="inline-block px-4 py-1.5 mb-4 text-xs font-semibold tracking-widest uppercase text-orange-700 bg-orange-100 rounded-full">
                        Welcome back
                    </div>
                    <h1 className="text-4xl font-bold text-stone-900 mb-3 tracking-tight">
                        Sign in
                    </h1>
                    <p className="text-base text-stone-600 mb-3">
                        Pick up where your personalized plan left off.
                    </p>
                    <div className="flex justify-center flex-wrap gap-x-3 gap-y-1 text-xs font-semibold text-stone-500 uppercase tracking-wider">
                        <span>AI nutritionist</span>
                        <span className="text-orange-400">·</span>
                        <span>Evidence-based</span>
                        <span className="text-orange-400">·</span>
                        <span>Personalized</span>
                    </div>
                </div>

                {/* Card */}
                <div className="bg-white rounded-3xl shadow-xl shadow-orange-100/40 border border-orange-100 p-8 space-y-5">
                    {notice && (
                        <p className="text-sm text-amber-700 bg-amber-50 px-3 py-2 rounded-lg">
                            {notice}
                        </p>
                    )}
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <Label className="text-sm font-semibold text-stone-700">
                                Email
                            </Label>
                            <Input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@example.com"
                                required
                                className="h-12 text-base"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label className="text-sm font-semibold text-stone-700">
                                Password
                            </Label>
                            <Input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                                className="h-12 text-base"
                            />
                        </div>

                        {error && (
                            <p className="text-sm text-rose-600 bg-rose-50 px-3 py-2 rounded-lg">
                                {error}
                            </p>
                        )}

                        <Button
                            type="submit"
                            disabled={loading}
                            size="lg"
                            className="w-full h-12 text-base bg-stone-900 hover:bg-stone-800 text-white"
                        >
                            {loading ? "Signing in..." : "Sign in →"}
                        </Button>
                    </form>

                    {/* Divider */}
                    <div className="flex items-center gap-3">
                        <div className="flex-1 h-px bg-orange-100" />
                        <span className="text-xs text-stone-400 uppercase tracking-widest">
                            or
                        </span>
                        <div className="flex-1 h-px bg-orange-100" />
                    </div>

                    {/* Google */}
                    <Button
                        type="button"
                        onClick={handleGoogle}
                        variant="outline"
                        size="lg"
                        className="w-full h-12 text-base border-orange-200 hover:bg-orange-50"
                    >
                        <GoogleIcon />
                        <span className="ml-2">Continue with Google</span>
                    </Button>
                </div>

                {/* Footer */}
                <p className="text-center text-sm text-stone-600 mt-6">
                    Don&apos;t have an account?{" "}
                    <Link
                        href="/register"
                        className="font-semibold text-orange-700 hover:text-orange-800 hover:underline"
                    >
                        Create one
                    </Link>
                </p>
            </div>
        </div>
    );
}

function GoogleIcon() {
    return (
        <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
        </svg>
    );
}
