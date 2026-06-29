export function LumenLogo({ size = "default" }: { size?: "default" | "lg" }) {
    const box = size === "lg" ? "w-10 h-10" : "w-8 h-8";
    const dot = size === "lg" ? "w-4 h-4" : "w-3 h-3";
    return (
        <div
            className={`${box} rounded-xl bg-gradient-to-br from-amber-400 via-orange-500 to-rose-500 flex items-center justify-center shadow-lg shadow-orange-200`}
        >
            <div className={`${dot} rounded-full bg-white`} />
        </div>
    );
}
