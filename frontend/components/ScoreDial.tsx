import { scoreBand, SEVERITY } from "@/lib/analysis";

/** Circular 0-100 score gauge, colored by severity band. */
export default function ScoreDial({
  score,
  size = 96,
  label = "Overall",
}: {
  score: number;
  size?: number;
  label?: string;
}) {
  const stroke = size <= 72 ? 6 : 8;
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const dash = (Math.max(0, Math.min(100, score)) / 100) * circumference;
  const color = SEVERITY[scoreBand(score)].ring;

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          className="stroke-steel-200"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference - dash}`}
          className={`${color} transition-[stroke-dasharray] duration-700`}
          stroke="currentColor"
        />
      </svg>
      <div
        className="flex flex-col items-center"
        style={{ marginTop: -size / 2 - 14, height: size / 2 }}
      >
        <span className="text-2xl font-bold text-ink">{Math.round(score)}</span>
        <span className="text-[10px] font-medium uppercase tracking-wide text-steel-500">
          {label}
        </span>
      </div>
    </div>
  );
}
