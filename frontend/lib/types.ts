export interface UserProfile {
  id: number;
  email: string;
  display_name: string;
  climbing_style: string | null;
  home_gym: string | null;
  grade_range_boulder: string | null;
  grade_range_route: string | null;
  goals: string | null;
  created_at: string;
}

export type GradeSystem = "v_scale" | "yds";
export type ClimbType = "boulder" | "sport" | "trad";
export type WallAngle = "slab" | "vertical" | "overhang" | "roof";
export type SendType = "flash" | "onsight" | "redpoint" | "repeat" | "project";
export type SessionType = "gym" | "board" | "outdoor" | "hangboard" | "other";

export interface Climb {
  id: number;
  name: string;
  grade: string;
  grade_system: GradeSystem;
  climb_type: ClimbType;
  wall_angle: WallAngle | null;
  location: string | null;
  send_type: SendType;
  attempt_count: number;
  notes: string | null;
  climbed_on: string;
  created_at: string;
}

export type ClimbCreate = Omit<Climb, "id" | "created_at">;

export interface WorkoutItem {
  exercise: string;
  detail: string;
  sets: number;
}

export interface TrainingSession {
  id: number;
  session_date: string;
  session_type: SessionType;
  duration_minutes: number;
  rpe: number | null;
  notes: string | null;
  workout_details: WorkoutItem[] | null;
  created_at: string;
}

export type SessionCreate = Omit<TrainingSession, "id" | "created_at">;

export interface PyramidEntry {
  grade: string;
  count: number;
}

export interface ProgressPoint {
  month: string;
  sends: number;
}

export interface AngleEntry {
  wall_angle: WallAngle;
  count: number;
}

export interface StatsSummary {
  total_climbs: number;
  total_sends: number;
  total_sessions: number;
  total_hours: number;
  hardest_boulder: string | null;
  hardest_route: string | null;
}
