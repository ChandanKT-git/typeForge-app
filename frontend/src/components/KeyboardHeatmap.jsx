import React from "react";

const KEYBOARD_ROWS = [
    ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
    ["a", "s", "d", "f", "g", "h", "j", "k", "l"],
    ["z", "x", "c", "v", "b", "n", "m"]
];

export default function KeyboardHeatmap({ heatmapData = {} }) {
    // Find the highest error count to normalize our colors
    const maxErrors = Math.max(0, ...Object.values(heatmapData));

    return (
        <div className="tf-card p-6 w-full overflow-hidden">
            <h3 className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono mb-4">
                Error Heatmap (Weak Keys)
            </h3>
            
            <div className="flex flex-col gap-2 items-center">
                {KEYBOARD_ROWS.map((row, rowIndex) => (
                    <div key={rowIndex} className="flex gap-2">
                        {row.map((keyChar) => {
                            const errors = heatmapData[keyChar] || 0;
                            // Calculate intensity from 0.0 to 1.0
                            const intensity = maxErrors > 0 ? errors / maxErrors : 0;
                            
                            // Base color is a dark zinc. As intensity goes up, we blend in the rose-500 color.
                            // We use rgba for the background color to utilize the intensity as opacity.
                            const bgColor = errors > 0 
                                ? `rgba(244, 63, 94, ${Math.max(0.15, intensity)})` // Rose-500 with varying opacity
                                : "rgba(255, 255, 255, 0.03)"; // Default faint white

                            return (
                                <div
                                    key={keyChar}
                                    title={`${errors} errors`}
                                    className="w-8 h-10 sm:w-10 sm:h-12 rounded-md flex items-center justify-center font-mono text-sm sm:text-base transition-colors border border-white/5"
                                    style={{ 
                                        backgroundColor: bgColor,
                                        color: errors > 0 ? "#fff" : "#71717a" 
                                    }}
                                >
                                    {keyChar}
                                </div>
                            );
                        })}
                    </div>
                ))}
            </div>
            
            <div className="mt-4 flex justify-between text-[10px] font-mono text-zinc-500">
                <span>0 errors</span>
                <span className="text-rose-400">High error rate</span>
            </div>
        </div>
    );
}
