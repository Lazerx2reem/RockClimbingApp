import type { FeedbackSeverity, VideoStatus } from "./types";

/** Map a 0-100 score to a severity band. */
export function scoreBand(score: number): FeedbackSeverity {
  if (score >= 80) return "good";
  if (score >= 60) return "warn";
  return "poor";
}

/**
 * Severity palette. Good stays on-brand sage; warn/poor use restrained warm
 * semantic accents so coaching priorities read at a glance (the app chrome
 * stays alpine).
 */
export const SEVERITY: Record<
  FeedbackSeverity,
  { label: string; badge: string; bar: string; ring: string; text: string }
> = {
  good: {
    label: "Strong",
    badge: "bg-sage-200 text-sage-800",
    bar: "bg-sage-500",
    ring: "text-sage-500",
    text: "text-sage-700",
  },
  warn: {
    label: "Refine",
    badge: "bg-amber-100 text-amber-800",
    bar: "bg-amber-500",
    ring: "text-amber-500",
    text: "text-amber-700",
  },
  poor: {
    label: "Focus",
    badge: "bg-rose-100 text-rose-700",
    bar: "bg-rose-500",
    ring: "text-rose-500",
    text: "text-rose-700",
  },
};

export const STATUS_STYLES: Record<VideoStatus, { label: string; badge: string }> = {
  uploaded: { label: "Queued", badge: "bg-steel-100 text-steel-600" },
  processing: { label: "Analyzing…", badge: "bg-lake-100 text-lake-700" },
  analyzed: { label: "Analyzed", badge: "bg-sage-200 text-sage-800" },
  failed: { label: "Failed", badge: "bg-rose-100 text-rose-700" },
};

/** Whether a video's status is still settling and should be polled. */
export function isPending(status: VideoStatus): boolean {
  return status === "uploaded" || status === "processing";
}
