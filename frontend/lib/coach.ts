import type { CoachToolCall } from "./types";

/** Backend tool name -> what to tell the user the coach looked at. */
export const TOOL_LABELS: Record<string, string> = {
  get_training_summary: "your training summary",
  get_recent_climbs: "your logbook",
  get_grade_pyramid: "your grade pyramid",
  get_recent_sessions: "your training sessions",
  list_video_analyses: "your video analyses",
  get_video_analysis: "a video analysis",
};

export function toolLabel(name: string): string {
  return TOOL_LABELS[name] ?? name;
}

/** "Checked your logbook, your grade pyramid" — null when nothing was read. */
export function toolSummary(calls: CoachToolCall[] | null): string | null {
  if (!calls?.length) return null;
  const labels = Array.from(new Set(calls.map((c) => toolLabel(c.name))));
  return `Checked ${labels.join(", ")}`;
}

/** Openers for an empty conversation — each one needs the logbook to answer. */
export const STARTER_PROMPTS = [
  "What should I focus on over the next month?",
  "Am I ready to try my next grade?",
  "Is my training load sustainable right now?",
  "What do my videos say about my technique?",
];
