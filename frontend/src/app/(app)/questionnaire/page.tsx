"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { recommend } from "@/lib/api";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

export default function QuestionnairePage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState({
        age: 30,
        gender: "",
        diet_type: "",
        fish_per_week: 2,
        dairy: "",
        sun_exposure: "",
        exercise: "",
        stress: 5,
        sleep_hours: 7,
        medications: "",
        complaints: "",
        health_goal: "",
    });

    async function handleSubmit() {
        setLoading(true);
        try {
            const data = await recommend(form);
            router.push(`/result/${data.session_id}`);
        } catch (error) {
            alert("Submit failed: " + error);
            setLoading(false);
        }
    }

    return (
        <div className="min-h-screen py-16 px-4">
            <div className="max-w-2xl mx-auto">
                {/* Hero */}
                <div className="text-center mb-10">
                    <div className="inline-block px-4 py-1.5 mb-4 text-xs font-semibold tracking-widest uppercase text-orange-700 bg-orange-100 rounded-full">
                        Personalized · Evidence-based
                    </div>
                    <h1 className="text-5xl font-bold text-stone-900 mb-3 tracking-tight">
                        Build your own wellness lab
                    </h1>
                    <p className="text-lg text-stone-600">
                        Answer a few questions and we&apos;ll craft your plan.
                    </p>
                </div>

                {/* Form */}
                <div className="bg-orange-50/100  rounded-3xl shadow-xl shadow-orange-100/40 border border-orange-100 overflow-hidden">
                    <div className="p-8 md:p-10 space-y-10">
                        {/* Section: About you */}
                        <Section title="About you" subtitle="The basics">
                            <Field label="Age" value={`${form.age} yrs`}>
                                <Slider
                                    value={[form.age]}
                                    onValueChange={(v) => setForm({ ...form, age: v[0] })}
                                    min={0}
                                    max={100}
                                    step={1}
                                />
                            </Field>

                            <Field label="Gender">
                                <OptionGroup
                                    value={form.gender}
                                    onChange={(v) => setForm({ ...form, gender: v })}
                                    options={[
                                        { value: "male", label: "Male" },
                                        { value: "female", label: "Female" },
                                        { value: "other", label: "Other" },
                                    ]}
                                />
                            </Field>
                        </Section>

                        {/* Section: Diet */}
                        <Section title="Diet & nutrition" subtitle="What you eat">
                            <Field label="Diet type">
                                <Select
                                    value={form.diet_type}
                                    onValueChange={(v) => setForm({ ...form, diet_type: v })}
                                >
                                    <SelectTrigger className="h-12 text-base">
                                        <SelectValue placeholder="Select your diet" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="omnivore">Omnivore</SelectItem>
                                        <SelectItem value="pescatarian">Pescatarian</SelectItem>
                                        <SelectItem value="vegetarian">Vegetarian</SelectItem>
                                        <SelectItem value="vegan">Vegan</SelectItem>
                                        <SelectItem value="keto">Keto</SelectItem>
                                    </SelectContent>
                                </Select>
                            </Field>

                            <Field label="Fish meals per week" value={`${form.fish_per_week} / week`}>
                                <Slider
                                    value={[form.fish_per_week]}
                                    onValueChange={(v) => setForm({ ...form, fish_per_week: v[0] })}
                                    min={0}
                                    max={7}
                                    step={1}
                                />
                            </Field>

                            <Field label="Dairy intake">
                                <OptionGroup
                                    value={form.dairy}
                                    onChange={(v) => setForm({ ...form, dairy: v })}
                                    options={[
                                        { value: "none", label: "None" },
                                        { value: "low", label: "Low" },
                                        { value: "moderate", label: "Moderate" },
                                        { value: "high", label: "High" },
                                    ]}
                                />
                            </Field>
                        </Section>

                        {/* Section: Lifestyle */}
                        <Section title="Lifestyle" subtitle="How you live">
                            <Field label="Sun exposure">
                                <OptionGroup
                                    value={form.sun_exposure}
                                    onChange={(v) => setForm({ ...form, sun_exposure: v })}
                                    options={[
                                        { value: "rarely", label: "Rarely" },
                                        { value: "sometimes", label: "Sometimes" },
                                        { value: "often", label: "Often" },
                                        { value: "daily", label: "Daily" },
                                    ]}
                                />
                            </Field>

                            <Field label="Exercise frequency">
                                <OptionGroup
                                    value={form.exercise}
                                    onChange={(v) => setForm({ ...form, exercise: v })}
                                    options={[
                                        { value: "none", label: "None" },
                                        { value: "1-2 times per week", label: "1–2 / wk" },
                                        { value: "3-4 times per week", label: "3–4 / wk" },
                                        { value: "daily", label: "Daily" },
                                    ]}
                                />
                            </Field>

                            <Field label="Stress level" value={`${form.stress} / 10`}>
                                <Slider
                                    value={[form.stress]}
                                    onValueChange={(v) => setForm({ ...form, stress: v[0] })}
                                    min={1}
                                    max={10}
                                    step={1}
                                />
                            </Field>

                            <Field label="Sleep per night" value={`${form.sleep_hours} h`}>
                                <Slider
                                    value={[form.sleep_hours]}
                                    onValueChange={(v) => setForm({ ...form, sleep_hours: v[0] })}
                                    min={3}
                                    max={12}
                                    step={0.5}
                                />
                            </Field>
                        </Section>

                        {/* Section: Health */}
                        <Section title="Health" subtitle="Your story">
                            <Field label="Current medications">
                                <Textarea
                                    value={form.medications}
                                    onChange={(e) => setForm({ ...form, medications: e.target.value })}
                                    placeholder="Enter 'none' if none, or list medications separated by commas"
                                    rows={2}
                                    className="text-base resize-none"
                                />
                            </Field>

                            <Field label="What's bothering you?">
                                <Textarea
                                    value={form.complaints}
                                    onChange={(e) => setForm({ ...form, complaints: e.target.value })}
                                    placeholder="e.g. frequent fatigue, poor sleep quality..."
                                    rows={3}
                                    className="text-base resize-none"
                                />
                            </Field>

                            <Field label="Your long-term goal">
                                <Select
                                    value={form.health_goal}
                                    onValueChange={(v) => setForm({ ...form, health_goal: v })}
                                >
                                    <SelectTrigger className="h-12 text-base">
                                        <SelectValue placeholder="What's your wellness goal?" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="immune_support">Immune support</SelectItem>
                                        <SelectItem value="cognitive_enhancement">Cognitive enhancement</SelectItem>
                                        <SelectItem value="sports_performance">Sports performance</SelectItem>
                                        <SelectItem value="cardiovascular_protection">Cardiovascular protection</SelectItem>
                                        <SelectItem value="anti_aging">Anti-aging</SelectItem>
                                        <SelectItem value="hormonal_balance">Hormonal balance</SelectItem>
                                    </SelectContent>
                                </Select>
                            </Field>
                        </Section>
                    </div>

                    {/* Submit bar */}
                    <div className="bg-gradient-to-r from-amber-100 to-rose-100 px-8 py-6 md:px-10 border-t border-orange-200">
                        <Button
                            onClick={handleSubmit}
                            disabled={loading}
                            size="lg"
                            className="w-full h-14 text-base font-semibold bg-stone-900 hover:bg-stone-800 text-white rounded-xl shadow-lg shadow-stone-900/20"
                        >
                            {loading ? "Analyzing your profile... (~25s)" : "Get My Recommendations →"}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// ── Helper components ─────────────────────────────────

function Section({
    title,
    subtitle,
    children,
}: {
    title: string;
    subtitle: string;
    children: React.ReactNode;
}) {
    return (
        <div>
            <div className="mb-6">
                <p className="text-xs font-semibold tracking-widest uppercase text-rose-800">
                    {subtitle}
                </p>
                <h2 className="text-xl font-bold text-stone-900">{title}</h2>
            </div>
            <div className="space-y-6">{children}</div>
        </div>
    );
}

function Field({
    label,
    value,
    children,
}: {
    label: string;
    value?: string;
    children: React.ReactNode;
}) {
    return (
        <div className="space-y-3">
            <div className="flex items-baseline justify-between">
                <Label className="text-base font-semibold text-stone-700">{label}</Label>
                {value && (
                    <span className="text-sm font-bold text-stone-900 tabular-nums">
                        {value}
                    </span>
                )}
            </div>
            {children}
        </div>
    );
}

function OptionGroup({
    value,
    onChange,
    options,
}: {
    value: string;
    onChange: (v: string) => void;
    options: { value: string; label: string }[];
}) {
    return (
        <div
            className="grid gap-2"
            style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}
        >
            {options.map((opt) => {
                const selected = value === opt.value;
                return (
                    <button
                        key={opt.value}
                        type="button"
                        onClick={() => onChange(opt.value)}
                        className={`
                            h-11 rounded-lg border-2 text-sm font-medium transition-all
                            ${selected
                                ? "border-amber-600 bg-amber-50 text-rose-900"
                                : "border-stone-200 bg-white text-stone-600 hover:border-orange-200 hover:bg-orange-50/30"
                            }
                        `}
                    >
                        {opt.label}
                    </button>
                );
            })}
        </div>
    );
}
