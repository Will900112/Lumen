"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { setToken } from "@/lib/api";
import { LumenLogo } from "@/components/LumenLogo";

export default function GoogleCallbackPage() {
    const router = useRouter();

    useEffect(() => {
        const hash = window.location.hash;
        const params = new URLSearchParams(hash.startsWith("#") ? hash.substring(1) : hash);
        const token = params.get("token");

        if (token) {
            setToken(token);
            router.replace("/questionnaire");
        } else {
            router.replace("/login?error=oauth");
        }
    }, [router]);

    return (
        <div className="min-h-screen flex items-center justify-center px-4">
            <div className="flex flex-col items-center gap-4">
                <LumenLogo size="lg" />
                <p className="text-stone-600 text-lg">Signing you in...</p>
            </div>
        </div>
    );
}
