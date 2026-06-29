"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listSaved, deleteSaved, getSession } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Pill, Trash2, Plus, ChevronDown } from "lucide-react";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

type SavedItem = {
    id: string;
    name: string;
    session_id: string;
    created_at: string;
};

type Recommendation = {
    name: string;
    reason: string;
    tip?: string;
};

type CachedSession = {
    gap_pack: Recommendation[];
    symptom_pack: Recommendation[];
    goal_pack: Recommendation[];
};

export default function ListPage() {
    const [items, setItems] = useState<SavedItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
    const [sessionCache, setSessionCache] = useState<Record<string, CachedSession>>({});

    useEffect(() => {
        load();
    }, []);

    async function load() {
        try {
            const data = await listSaved();
            setItems(data);
        } catch (err) {
            const error = err as Error;
            alert("Failed to load: " + error.message);
        } finally {
            setLoading(false);
        }
    }

    async function handleToggle(item: SavedItem) {
        // Toggle in/out of the set
        setExpandedIds((prev) => {
            const next = new Set(prev);
            if (next.has(item.id)) {
                next.delete(item.id);
            } else {
                next.add(item.id);
            }
            return next;
        });

        // Fetch session if not cached
        if (!sessionCache[item.session_id]) {
            try {
                const session = await getSession(item.session_id);
                setSessionCache((prev) => ({
                    ...prev,
                    [item.session_id]: {
                        gap_pack: session.gap_pack as Recommendation[],
                        symptom_pack: session.symptom_pack as Recommendation[],
                        goal_pack: session.goal_pack as Recommendation[],
                    },
                }));
            } catch {
                // ignore
            }
        }
    }

    async function handleDelete(id: string) {
        try {
            await deleteSaved(id);
            setItems((prev) => prev.filter((i) => i.id !== id));
            setExpandedIds((prev) => {
                const next = new Set(prev);
                next.delete(id);
                return next;
            });
        } catch (err) {
            const error = err as Error;
            alert("Delete failed: " + error.message);
        }
    }

    function findRecommendation(item: SavedItem): Recommendation | null {
        const session = sessionCache[item.session_id];
        if (!session) return null;
        const all = [
            ...session.gap_pack,
            ...session.symptom_pack,
            ...session.goal_pack,
        ];
        return all.find((r) => r.name === item.name) || null;
    }

    if (loading)
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-stone-500 text-lg">Loading your picks...</div>
            </div>
        );

    return (
        <div className="min-h-screen py-12 px-4">
            <div className="max-w-3xl mx-auto space-y-8">
                {/* Hero */}
                <div className="text-center">
                    <div className="inline-block px-4 py-1.5 mb-4 text-xs font-semibold tracking-widest uppercase text-orange-700 bg-orange-100 rounded-full">
                        Your Library
                    </div>

                    <p className="text-lg text-stone-600">
                        Supplements you&apos;ve made yours.
                    </p>
                </div>

                {/* Empty state */}
                {items.length === 0 && (
                    <div className="bg-white rounded-3xl border border-orange-100 shadow-xl shadow-orange-100/40 p-12 text-center">
                        <Pill className="w-16 h-16 mx-auto text-orange-300 mb-4" />
                        <h2 className="text-2xl font-bold text-stone-900 mb-2">
                            Nothing here yet
                        </h2>
                        <p className="text-stone-600 mb-6">
                            Build a plan and start picking supplements.
                        </p>
                        <Link href="/questionnaire">
                            <Button
                                size="lg"
                                className="bg-stone-900 hover:bg-stone-800 text-white"
                            >
                                <Plus className="w-4 h-4 mr-2" />
                                Build a new plan
                            </Button>
                        </Link>
                    </div>
                )}

                {/* Items list */}
                {items.length > 0 && (
                    <div className="bg-white rounded-3xl border border-orange-100 shadow-xl shadow-orange-100/40 overflow-hidden">
                        <div className="divide-y divide-orange-100">
                            {items.map((item) => {
                                const expanded = expandedIds.has(item.id);
                                const rec = expanded ? findRecommendation(item) : null;

                                return (
                                    <div key={item.id}>
                                        {/* Row */}
                                        <div
                                            onClick={() => handleToggle(item)}
                                            className="w-full p-6 flex items-center gap-4 hover:bg-orange-50/50 transition text-left cursor-pointer"
                                        >
                                            <div className="w-10 h-10 rounded-xl bg-orange-100 flex items-center justify-center flex-shrink-0">
                                                <Pill className="w-5 h-5 text-orange-600" />
                                            </div>

                                            <div className="flex-1 min-w-0">
                                                <h3 className="text-lg font-bold text-stone-900">
                                                    {item.name}
                                                </h3>
                                                <p className="text-xs text-stone-500 mt-0.5">
                                                    Picked on{" "}
                                                    {new Date(item.created_at).toLocaleDateString()}
                                                </p>
                                            </div>

                                            <ChevronDown
                                                className={`w-5 h-5 text-stone-400 transition-transform ${
                                                    expanded ? "rotate-180" : ""
                                                }`}
                                            />
                                            <AlertDialog>
                                                <AlertDialogTrigger asChild>
                                                    <button
                                                        type="button"
                                                        onClick={(e) => e.stopPropagation()}
                                                        className="text-stone-400 hover:text-rose-600 hover:bg-rose-50 p-2 rounded-md transition"
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                </AlertDialogTrigger>
                                                <AlertDialogContent>
                                                    <AlertDialogHeader>
                                                        <AlertDialogTitle>Remove this pick?</AlertDialogTitle>
                                                        <AlertDialogDescription>
                                                            <span className="font-semibold text-stone-900">{item.name}</span>
                                                            {" "}will be removed from your library. You can always pick it again from a plan.
                                                        </AlertDialogDescription>
                                                    </AlertDialogHeader>
                                                    <AlertDialogFooter>
                                                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                                                        <AlertDialogAction
                                                            onClick={() => handleDelete(item.id)}
                                                            className="bg-rose-600 hover:bg-rose-700 text-white"
                                                        >
                                                            Remove
                                                        </AlertDialogAction>
                                                    </AlertDialogFooter>
                                                </AlertDialogContent>
                                            </AlertDialog>
                                                                                        
                                        </div>

                                        {/* Expanded content */}
                                        {expanded && (
                                            <div className="px-6 pb-6 bg-orange-50/30">
                                                {!rec && (
                                                    <p className="text-sm text-stone-400 italic">
                                                        Loading details...
                                                    </p>
                                                )}
                                                {rec && (
                                                    <div className="space-y-4">
                                                        <p className="text-base text-stone-700 leading-relaxed">
                                                            {rec.reason}
                                                        </p>
                                                        {rec.tip && (
                                                            <p className="text-sm text-orange-800 bg-orange-100 px-4 py-3 rounded-xl">
                                                                💡 {rec.tip}
                                                            </p>
                                                        )}
                                                        <Link href={`/result/${item.session_id}`}>
                                                            <Button
                                                                variant="outline"
                                                                className="border-orange-300 text-orange-700 hover:bg-orange-100 hover:text-orange-800"
                                                            >
                                                                View plan
                                                            </Button>
                                                        </Link>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
