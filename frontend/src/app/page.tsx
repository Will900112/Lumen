import Link from "next/link";
import { Button } from "@/components/ui/button";
import { LumenLogo } from "@/components/LumenLogo";
import { Brain, BookOpen, ShieldCheck, Sparkles, ArrowRight } from "lucide-react";

export default function Home() {
    return (
        <div className="min-h-screen">
            {/* Top bar — sticky */}
            <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-stone-200/60">
                <div className="max-w-6xl mx-auto flex items-center justify-between px-6 py-4">
                    <Link
                        href="/"
                        className="flex items-center gap-3 font-bold text-stone-900 text-2xl tracking-tight"
                    >
                        <LumenLogo />
                        Lumen
                    </Link>
                    <div className="flex items-center gap-3">
                        <Link href="/login">
                            <Button variant="ghost" className="text-stone-700">
                                Sign in
                            </Button>
                        </Link>
                        <Link href="/register">
                            <Button className="bg-stone-900 hover:bg-stone-800 text-white">
                                Get started
                            </Button>
                        </Link>
                    </div>
                </div>
            </header>

            {/* Hero */}
            <section className="pt-24 pb-24 px-6">
                <div className="max-w-3xl mx-auto text-center">
                    <div className="inline-block px-4 py-1.5 mb-6 text-xs font-semibold tracking-widest uppercase text-orange-700 bg-orange-100 rounded-full">
                        AI nutritionist · Evidence-based · Personalized
                    </div>
                    <h1 className="text-6xl md:text-7xl font-bold text-stone-900 mb-6 tracking-tight leading-[1.05]">
                        Your wellness stack,
                        <br />
                        <span className="text-orange-600">backed by science.</span>
                    </h1>
                    <p className="text-xl text-stone-600 mb-10 max-w-2xl mx-auto leading-relaxed">
                        An AI nutritionist powered by clinical textbooks. Personalized
                        supplement recommendations in 30 seconds.
                    </p>
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                        <Link href="/register">
                            <Button
                                size="lg"
                                className="h-14 px-8 text-base bg-stone-900 hover:bg-stone-800 text-white"
                            >
                                Build my plan
                                <ArrowRight className="w-5 h-5 ml-2" />
                            </Button>
                        </Link>
                        <Link href="/login">
                            <Button
                                size="lg"
                                variant="outline"
                                className="h-14 px-8 text-base border-orange-200 hover:bg-orange-50"
                            >
                                I have an account
                            </Button>
                        </Link>
                    </div>
                </div>
            </section>

            {/* Features */}
            <section className="pb-24 px-6">
                <div className="max-w-5xl mx-auto">
                    <div className="text-center mb-12">
                        <p className="text-xs font-bold tracking-widest uppercase text-orange-600 mb-2">
                            Why we&apos;re different
                        </p>
                        <h2 className="text-4xl font-bold text-stone-900 tracking-tight">
                            Not just another supplement quiz.
                        </h2>
                    </div>

                    <div className="grid md:grid-cols-3 gap-6">
                        <FeatureCard
                            icon={<Brain className="w-6 h-6" />}
                            title="Multi-agent AI"
                            description="Five specialized AI agents analyze your profile — from nutritional gaps to clinical evidence to drug safety."
                        />
                        <FeatureCard
                            icon={<BookOpen className="w-6 h-6" />}
                            title="Evidence-grounded"
                            description="Every recommendation is verified against nutritional medicine textbooks using RAG retrieval. No hallucinations."
                        />
                        <FeatureCard
                            icon={<ShieldCheck className="w-6 h-6" />}
                            title="Safety first"
                            description="Cross-checks your medications and conditions against herb-drug interactions before suggesting anything."
                        />
                    </div>
                </div>
            </section>

            {/* How it works */}
            <section className="pb-24 px-6">
                <div className="max-w-3xl mx-auto">
                    <div className="text-center mb-12">
                        <p className="text-xs font-bold tracking-widest uppercase text-orange-600 mb-2">
                            How it works
                        </p>
                        <h2 className="text-4xl font-bold text-stone-900 tracking-tight">
                            Three steps to your stack.
                        </h2>
                    </div>

                    <div className="space-y-6">
                        <Step
                            num="01"
                            title="Tell us about you"
                            description="Diet, lifestyle, symptoms, goals, medications. Takes 2 minutes."
                        />
                        <Step
                            num="02"
                            title="Our AI agents analyze"
                            description="Five agents work together: profile analysis → clinical proposal → RAG grounding → safety check."
                        />
                        <Step
                            num="03"
                            title="Get your personalized plan"
                            description="A foundation pack, symptom pack, and goal pack — each supplement explained and safety-checked. Ask follow-up questions anytime."
                        />
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="pb-32 px-6">
                <div className="max-w-2xl mx-auto bg-gradient-to-br from-orange-100 via-amber-100 to-rose-100 rounded-3xl p-12 text-center border border-orange-200">
                    <Sparkles className="w-10 h-10 text-orange-600 mx-auto mb-4" />
                    <h2 className="text-3xl font-bold text-stone-900 mb-3 tracking-tight">
                        Ready to build your stack?
                    </h2>
                    <p className="text-base text-stone-700 mb-6">
                        Free to start. No credit card required.
                    </p>
                    <Link href="/register">
                        <Button
                            size="lg"
                            className="h-14 px-8 text-base bg-stone-900 hover:bg-stone-800 text-white"
                        >
                            Get started
                            <ArrowRight className="w-5 h-5 ml-2" />
                        </Button>
                    </Link>
                </div>
            </section>

            {/* Footer */}
            <footer className="border-t border-orange-100 py-8 px-6">
                <div className="max-w-6xl mx-auto text-center text-sm text-stone-500">
                    Built with AI · Grounded in research
                </div>
            </footer>
        </div>
    );
}

function FeatureCard({
    icon,
    title,
    description,
}: {
    icon: React.ReactNode;
    title: string;
    description: string;
}) {
    return (
        <div className="bg-white rounded-3xl border border-orange-100 shadow-lg shadow-orange-100/40 p-6">
            <div className="w-12 h-12 rounded-2xl bg-orange-100 flex items-center justify-center text-orange-600 mb-4">
                {icon}
            </div>
            <h3 className="text-xl font-bold text-stone-900 mb-2">{title}</h3>
            <p className="text-sm text-stone-600 leading-relaxed">{description}</p>
        </div>
    );
}

function Step({
    num,
    title,
    description,
}: {
    num: string;
    title: string;
    description: string;
}) {
    return (
        <div className="bg-white rounded-3xl border border-orange-100 shadow-lg shadow-orange-100/40 p-6 flex gap-5">
            <div className="text-5xl font-bold text-orange-300 leading-none">{num}</div>
            <div className="flex-1">
                <h3 className="text-xl font-bold text-stone-900 mb-1">{title}</h3>
                <p className="text-base text-stone-600 leading-relaxed">{description}</p>
            </div>
        </div>
    );
}
