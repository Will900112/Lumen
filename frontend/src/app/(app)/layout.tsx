"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { listSessions, logout, getToken } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet";
import { Menu, Plus, LogOut, PanelLeftClose, PanelLeft, Pill } from "lucide-react";
import { LumenLogo } from "@/components/LumenLogo";

type Session = {
    id: string;
    created_at: string;
    narrative: string;
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const [sessions, setSessions] = useState<Session[]>([]);
    const [mobileOpen, setMobileOpen] = useState(false);
    const [desktopOpen, setDesktopOpen] = useState(true);
    const pathname = usePathname();

    useEffect(() => {
        if (!getToken()) {
            router.push("/login");
            return;
        }
        loadSessions();
    }, [pathname]);

    async function loadSessions() {
        try {
            const data = await listSessions();
            setSessions(data);
        } catch {
            // ignore
        }
    }

    function handleLogout() {
        logout();
        router.push("/login");
    }

    return (
        <div className="min-h-screen flex">
            {/* ── Desktop sidebar ────────────────────────── */}
            <aside
                className={`
                    hidden md:flex flex-col
                    bg-white border-r border-orange-100
                    transition-all duration-300 overflow-hidden
                    ${desktopOpen ? "w-72" : "w-0"}
                `}
            >
                <SidebarContent
                    sessions={sessions}
                    onLinkClick={() => {}}
                    onLogout={handleLogout}
                />
            </aside>

            {/* ── Main area ──────────────────────────────── */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Top bar */}
                <header className="sticky top-0 z-30 bg-white/80 backdrop-blur border-b border-orange-100">
                    <div className="flex items-center justify-between px-4 py-3">
                        <div className="flex items-center gap-2">
                            {/* Mobile: open Sheet */}
                            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
                                <SheetTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="md:hidden"
                                        onClick={() => loadSessions()}
                                    >
                                        <Menu className="w-5 h-5" />
                                    </Button>
                                </SheetTrigger>
                                <SheetContent side="left" className="w-72 p-0">
                                    <SidebarContent
                                        sessions={sessions}
                                        onLinkClick={() => setMobileOpen(false)}
                                        onLogout={handleLogout}
                                    />
                                </SheetContent>
                            </Sheet>

                            {/* Desktop: toggle sidebar */}
                            <Button
                                variant="ghost"
                                size="icon"
                                className="hidden md:inline-flex"
                                onClick={() => {
                                    setDesktopOpen(!desktopOpen);
                                    if (!desktopOpen) loadSessions();
                                }}
                            >
                                {desktopOpen ? (
                                    <PanelLeftClose className="w-5 h-5" />
                                ) : (
                                    <PanelLeft className="w-5 h-5" />
                                )}
                            </Button>

                            <Link
                                href="/questionnaire"
                                className="flex items-center gap-3 font-bold text-stone-900 text-2xl tracking-tight"
                            >
                                <LumenLogo />
                                Lumen
                            </Link>
                        </div>

                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleLogout}
                            className="text-stone-600"
                        >
                            <LogOut className="w-4 h-4 mr-2" />
                            <span className="hidden sm:inline">Logout</span>
                        </Button>
                    </div>
                </header>

                {children}
            </div>
        </div>
    );
}

// ── Shared sidebar content ──────────────────────────────
function SidebarContent({
    sessions,
    onLinkClick,
    onLogout,
}: {
    sessions: Session[];
    onLinkClick: () => void;
    onLogout: () => void;
}) {
    return (
        <div className="flex flex-col h-full">
            {/* New plan button */}
            <div className="p-4 border-b border-orange-100">
                <Link href="/questionnaire" onClick={onLinkClick}>
                    <Button className="w-full justify-center bg-stone-900 hover:bg-stone-800 text-white">
                        <Plus className="w-4 h-4 mr-2" />
                        Build a new plan
                    </Button>
                </Link>
            </div>

            {/* My picks */}
            <div className="px-3 pt-4 pb-2">
                <p className="px-2 mb-2 text-sm font-bold tracking-widest uppercase text-stone-900">
                    My picks
                </p>
                <Link
                    href="/list"
                    onClick={onLinkClick}
                    className="flex items-center gap-3 p-3 rounded-xl hover:bg-orange-50 transition"
                >
                    <Pill className="w-4 h-4 text-orange-600" />
                    <span className="text-sm font-medium text-stone-800">
                        Picked supplements
                    </span>
                </Link>
            </div>

            {/* Past plans */}
            <div className="px-3 pt-4 pb-2 flex-1 flex flex-col min-h-0">
                <p className="px-2 mb-2 text-sm font-bold tracking-widest uppercase text-stone-900">
                    Past plans
                </p>
                <div className="flex-1 space-y-2 overflow-y-auto">
                    {sessions.length === 0 && (
                        <p className="text-sm text-stone-400 text-center py-8">
                            No plans yet.
                        </p>
                    )}
                    {sessions.map((s) => (
                        <Link
                            key={s.id}
                            href={`/result/${s.id}`}
                            onClick={onLinkClick}
                            className="block p-3 rounded-xl border border-orange-100 hover:bg-orange-50 transition"
                        >
                            <p className="text-xs text-orange-600 font-semibold">
                                {new Date(s.created_at).toLocaleDateString()}
                            </p>
                            <p className="text-sm text-stone-700 line-clamp-2 mt-1">
                                {s.narrative}
                            </p>
                        </Link>
                    ))}
                </div>
            </div>

            {/* Logout */}
            <div className="p-3 border-t border-orange-100">
                <Button
                    variant="ghost"
                    onClick={onLogout}
                    className="w-full justify-start text-stone-600"
                >
                    <LogOut className="w-4 h-4 mr-2" />
                    Logout
                </Button>
            </div>
        </div>
    );
}
