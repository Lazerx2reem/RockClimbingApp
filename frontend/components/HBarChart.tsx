"use client";

/**
 * Horizontal bar chart (single series). Used for the grade pyramid and
 * wall-angle volume. Bars: ≤24px thick, 4px rounded data-end, square at the
 * baseline; values ride the bar tips in text ink, never the series color.
 */
export interface HBarDatum {
  label: string;
  value: number;
}

export default function HBarChart({
  data,
  ariaLabel,
}: {
  data: HBarDatum[];
  ariaLabel: string;
}) {
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <div role="img" aria-label={ariaLabel} className="space-y-1.5">
      {data.map(({ label, value }) => (
        <div key={label} className="flex items-center gap-3">
          <span className="w-12 shrink-0 text-right text-xs font-medium text-stone-500">
            {label}
          </span>
          <div className="relative h-5 flex-1">
            <div
              className="absolute inset-y-0.5 left-0 rounded-r bg-emerald-700"
              style={{ width: `${(value / max) * 100}%`, minWidth: "2px" }}
            />
            <span
              className="absolute inset-y-0 flex items-center pl-2 text-xs font-medium text-stone-700"
              style={{ left: `${(value / max) * 100}%` }}
            >
              {value}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
