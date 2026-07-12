"use client";

import { useEffect, useState, useRef  } from "react";
import { useParams } from "next/navigation";
import { getSession, chat, saveSupplement, listSaved } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import ReactMarkdown from "react-markdown";

const markdownComponents = {
    strong: ({ children }: { children?: React.ReactNode }) => (
        <strong className="font-bold text-stone-900">{children}</strong>
    ),
    em: ({ children }: { children?: React.ReactNode }) => (
        <em className="italic">{children}</em>
    ),
    ol: ({ children }: { children?: React.ReactNode }) => (
        <ol className="list-decimal list-inside space-y-1 my-2">{children}</ol>
    ),
    ul: ({ children }: { children?: React.ReactNode }) => (
        <ul className="list-disc list-inside space-y-1 my-2">{children}</ul>
    ),
    li: ({ children }: { children?: React.ReactNode }) => (
        <li className="leading-loose">{children}</li>
    ),
    p: ({ children }: { children?: React.ReactNode }) => (
        <p className="leading-loose">{children}</p>
    ),
    code: ({ children }: { children?: React.ReactNode }) => (
        <code className="bg-orange-100 text-orange-900 px-1.5 py-0.5 rounded text-sm font-mono">
            {children}
        </code>
    ),
    a: ({ children, href }: { children?: React.ReactNode; href?: string }) => (
        <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-orange-700 hover:text-orange-800 underline"
        >
            {children}
        </a>
    ),
};


type Recommendation = {
    name: string;
    reason: string;
    tip?: string;
    evidence_snippet?: string;
};

type Message = {
    role: string;
    content: string;
    created_at?: string;
};

type SessionData = {
    id: string;
    created_at: string;
    gap_pack: Recommendation[];
    symptom_pack: Recommendation[];
    goal_pack: Recommendation[];
    safety_warnings: string[];
    narrative: string;
    messages: Message[];
};

export default function ResultPage() {
    const params = useParams();
    const sessionId = params.sessionId as string;
    const [data, setData] = useState<SessionData | null>(null);
    const [loading, setLoading] = useState(true);
    const [message, setMessage] = useState("");
    const [sending, setSending] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [savedNames, setSavedNames] = useState<Set<string>>(new Set());   
    const messagesContainerRef = useRef<HTMLDivElement>(null); 

    useEffect(() => {
        getSession(sessionId)
            .then((res) => {
                setData(res as SessionData);
                setMessages((res as SessionData).messages || []);
            })
            .catch((err) => alert("Failed to load: " + err.message))
            .finally(() => setLoading(false));

        listSaved()
            .then((items) => {
                setSavedNames(new Set(items.map((i) => i.name)));
            })
            .catch(() => {
                // ignore
            });
    }, [sessionId]);

    useEffect(() => {
        if (messages.length === 0) return;
        const el = messagesContainerRef.current;
        if (el) {
            el.scrollTop = el.scrollHeight;
        }
    }, [messages, sending]);

    async function handleSend() {
        // guard `sending` too: the button is disabled but Enter is not
        if (sending || !message.trim()) return;
        const userMsg = message;
        setMessage("");
        setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
        setSending(true);

        try {
            const res = await chat(sessionId, userMsg);
            setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
        } catch (err) {
            const error = err as Error;
            alert("Chat failed: " + error.message);
        } finally {
            setSending(false);
        }
    }

    async function handleSave(name: string) {
        if (savedNames.has(name)) return;
        try {
            await saveSupplement(sessionId, name);
            setSavedNames((prev) => new Set(prev).add(name));
        } catch (err) {
            const error = err as Error;
            alert("Save failed: " + error.message);
        }
    }

    if (loading)
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-stone-500 text-lg">Loading your wellness plan...</div>
            </div>
        );

    if (!data) return <div className="p-8">No data</div>;

    return (
        <div className="min-h-screen py-12 px-4">
            <div className="max-w-3xl mx-auto space-y-8">
                {/* Hero */}
                <div className="text-center">
                    <div className="inline-block px-4 py-1.5 mb-4 text-xs font-semibold tracking-widest uppercase text-orange-700 bg-orange-100 rounded-full">
                        Your Personalized Plan
                    </div>
                    <h1 className="text-5xl font-bold text-stone-900 mb-3 tracking-tight">
                        Build your own wellness lab
                    </h1>
                </div>

                {/* Narrative card */}
                <div className="relative bg-white rounded-3xl border border-orange-100 shadow-xl shadow-orange-100/40 overflow-hidden">
                    {/* Quote marks pinned to card corners */}
                    <div className="absolute top-4 left-6 text-7xl font-serif text-orange-200 leading-none select-none pointer-events-none">
                        “
                    </div>
                    <div className="absolute bottom-0 right-6 text-7xl font-serif text-orange-200 leading-none select-none pointer-events-none">
                        ”
                    </div>

                    {/* Content centered */}
                    <div className="px-16 py-12">
                        <div className="flex items-center gap-3 mb-5">
                            <div className="h-8 w-1 bg-orange-500 rounded-full" />
                            <p className="text-sm font-bold tracking-widest uppercase text-orange-600">
                                Summary
                            </p>
                        </div>
                        <div className="text-lg text-stone-800 leading-relaxed font-medium italic">
                            <ReactMarkdown components={markdownComponents}>
                                {data.narrative}
                            </ReactMarkdown>
                        </div>
                    </div>
                </div>

                {/* Safety warnings */}
                {data.safety_warnings && data.safety_warnings.length > 0 && (
                    <div className="bg-rose-50 border-2 border-rose-200 rounded-2xl p-5">
                        <h3 className="font-bold text-rose-900 mb-2 flex items-center gap-2">
                            ⚠️ Safety notes
                        </h3>
                        <ul className="space-y-1">
                            {data.safety_warnings.map((w, i) => (
                                <li key={i} className="text-sm text-rose-800">
                                    {w}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {/* Foundation Pack */}
                {data.gap_pack && data.gap_pack.length > 0 && (
                    <Pack
                        title="Foundation"
                        subtitle="Fill nutritional gaps"
                        items={data.gap_pack}
                        onSave={handleSave}
                        savedNames={savedNames}
                    />
                )}

                {/* Symptom Pack */}
                {data.symptom_pack && data.symptom_pack.length > 0 && (
                    <Pack
                        title="Symptom relief"
                        subtitle="Address what's bothering you"
                        items={data.symptom_pack}
                        onSave={handleSave}
                        savedNames={savedNames}
                    />
                )}

                {/* Goal Pack */}
                {data.goal_pack && data.goal_pack.length > 0 && (
                    <Pack
                        title="Long-term goal"
                        subtitle="Optimize for what you're chasing"
                        items={data.goal_pack}
                        onSave={handleSave}
                        savedNames={savedNames}
                    />
                )}

                {/* Chat */}
                <div className="bg-white rounded-3xl shadow-xl shadow-orange-100/40 border border-orange-100 overflow-hidden">
                    <div className="p-6 border-b border-orange-100">
                        <h2 className="text-xl font-bold text-stone-900">
                            💬 Ask your AI nutritionist
                        </h2>
                        <p className="text-sm text-stone-500 mt-1">
                            Questions about your plan? Just ask.
                        </p>
                    </div>

                    {/* Messages */}
                    <div ref={messagesContainerRef} className="p-6 space-y-4 min-h-[200px] max-h-[500px] overflow-y-auto">
                        {messages.length === 0 && (
                            <p className="text-center text-stone-400 text-sm">
                                No messages yet. Start the conversation below.
                            </p>
                        )}
                        {messages.map((m, i) => (
                            <div
                                key={i}
                                className={`flex ${
                                    m.role === "user" ? "justify-end" : "justify-start"
                                }`}
                            >
                                <div
                                    className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                                        m.role === "user"
                                            ? "bg-orange-500 text-white"
                                            : "bg-orange-50 text-stone-800 border border-orange-100"
                                    }`}
                                >
                                    {m.role === "user" ? (
                                        m.content
                                    ) : (
                                        <ReactMarkdown components={markdownComponents}>
                                            {m.content}
                                        </ReactMarkdown>
                                    )}
                                </div>
                            </div>
                        ))}
                        {sending && (
                            <div className="flex justify-start">
                                <div className="max-w-[80%] px-4 py-3 rounded-2xl text-sm bg-orange-50 text-stone-500 border border-orange-100">
                                    Thinking...
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Input */}
                    <div className="bg-gradient-to-r from-amber-100 to-rose-100 p-4 border-t border-orange-200">
                        <div className="flex gap-2 items-start"> 
                            <Textarea
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                placeholder="e.g. When should I take Vitamin D?"
                                rows={2}
                                className="resize-none bg-white max-h-48" 
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSend();
                                    }
                                }}
                            />
                            <Button
                                onClick={handleSend}
                                disabled={sending || !message.trim()}
                                className="h-12 px-6 bg-stone-900 hover:bg-stone-800 text-white"
                            >
                                Send
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

// ── Helper components ─────────────────────────────────

function Pack({
    title,
    subtitle,
    items,
    onSave,
    savedNames,
}: {
    title: string;
    subtitle: string;
    items: Recommendation[];
    onSave: (name: string) => void;
    savedNames: Set<string>;
}) {
    return (
        <div className="bg-white rounded-3xl shadow-xl shadow-orange-100/40 border border-orange-100 overflow-hidden">
            <div className="p-6 border-b border-orange-100">
                <p className="text-xs font-semibold tracking-widest uppercase text-orange-600">
                    {subtitle}
                </p>
                <h2 className="text-2xl font-bold text-stone-900">{title}</h2>
            </div>
            <div className="divide-y divide-orange-100">
                {items.map((item, i) => (
                    <div key={i} className="p-6 flex gap-4">
                        <div className="flex-1">
                            <h3 className="text-xl font-bold text-stone-900 mb-1">
                                {item.name}
                            </h3>
                            <p className="text-base text-stone-600 leading-relaxed">
                                {item.reason}
                            </p>
                            {item.tip && (
                                <p className="mt-2 text-sm text-orange-700 bg-orange-50 px-3 py-2 rounded-lg">
                                    💡 {item.tip}
                                </p>
                            )}
                        </div>
                        <Button
                            variant="outline"
                            size="lg"
                            onClick={() => onSave(item.name)}
                            disabled={savedNames.has(item.name)}
                            className={`self-start ${
                                savedNames.has(item.name)
                                    ? "border-orange-500 bg-orange-500 text-white hover:bg-orange-500 hover:text-white disabled:opacity-100"
                                    : "border-orange-300 text-orange-700 hover:bg-orange-50 hover:text-orange-800"
                            }`}
                        >
                            {savedNames.has(item.name) ? "✓ Mine" : "Make it mine"}
                        </Button>
                    </div>
                ))}
            </div>
        </div>
    );
}
