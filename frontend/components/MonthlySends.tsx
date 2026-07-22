"use client";

import { useState } from "react";
import type { ProgressPoint } from "@/lib/types";

const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function monthLabel(month: string): string {
  const idx = Number(month.slice(5, 7)) - 1;
  return MONTH_NAMES[idx] ?? month;
}

/**
 * Sends per month as a column chart. Hairline gridlines on clean tick values,
 * 4px rounded caps square at the baseline, and a per-column hover tooltip.
 */
export default function MonthlySends({ data }: { data: ProgressPoint[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(...data.map((d) => d.sends), 1);
  // Clean y ticks: 0, half, max rounded up to an even value
  const top = Math.max(2, Math.ceil(max / 2) * 2);
  const ticks = [0, top / 2, top];

  return (
    <div>
      <div className="relative h-40">
        {/* Gridlines */}
        {ticks.map((t) => (
          <div
            key={t}
            className="absolute inset-x-0 flex items-center gap-2"
            style={{ bottom: `${(t / top) * 100}%` }}
          >
            <span className="w-5 -translate-y-px text-right text-[10px] tabular-nums text-stone-400">
              {t}
            </span>
            <div
              className={`h-px flex-1 ${t === 0 ? "bg-stone-300" : "bg-stone-200"}`}
            />
          </div>
        ))}
        {/* Columns */}
        <div className="absolute inset-y-0 left-7 right-0 flex items-end gap-[2px]">
          {data.map((point, i) => (
            <div
              key={point.month}
              className="relative flex h-full flex-1 items-end justify-center"
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
            >
              <div
                className={`w-full max-w-6 rounded-t ${
                  hover === i ? "bg-emerald-800" : "bg-emerald-700"
                }`}
                style={{ height: `${(point.sends / top) * 100}%` }}
              />
              {hover === i && (
                <div className="pointer-events-none absolute bottom-full z-10 mb-1 whitespace-nowrap rounded-md bg-stone-900 px-2 py-1 text-xs text-white">
                  {monthLabel(point.month)} {point.month.slice(0, 4)}:{" "}
                  <span className="font-semibold">{point.sends}</span> sends
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      {/* X labels */}
      <div className="ml-7 mt-1 flex gap-[2px]">
        {data.map((point) => (
          <span
            key={point.month}
            className="flex-1 text-center text-[10px] text-stone-400"
          >
            {monthLabel(point.month)}
          </span>
        ))}
      </div>
    </div>
  );
}
