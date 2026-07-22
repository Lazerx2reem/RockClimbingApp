"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { V_SCALE, YDS } from "@/lib/grades";
import type { Climb, ClimbType, SendType, WallAngle } from "@/lib/types";

const SEND_LABELS: Record<SendType, string> = {
  flash: "Flash",
  onsight: "Onsight",
  redpoint: "Redpoint",
  repeat: "Repeat",
  project: "Project",
};

const SEND_STYLES: Record<SendType, string> = {
  flash: "bg-amber-100 text-amber-800",
  onsight: "bg-amber-100 text-amber-800",
  redpoint: "bg-emerald-100 text-emerald-800",
  repeat: "bg-sky-100 text-sky-800",
  project: "bg-stone-200 text-stone-600",
};

const inputCls =
  "mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm focus:border-emerald-600 focus:outline-none";

export default function LogbookPage() {
  const [climbs, setClimbs] = useState<Climb[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [climbType, setClimbType] = useState<ClimbType>("boulder");
  const [grade, setGrade] = useState("V2");
  const [sendType, setSendType] = useState<SendType>("redpoint");
  const [wallAngle, setWallAngle] = useState<WallAngle | "">("");
  const [attempts, setAttempts] = useState(1);
  const [location, setLocation] = useState("");
  const [climbedOn, setClimbedOn] = useState(() =>
    new Date().toISOString().slice(0, 10)
  );
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listClimbs().then(setClimbs).catch((e) => setError(String(e.message)));
  }, []);

  const gradeOptions = climbType === "boulder" ? V_SCALE : YDS;

  function onTypeChange(type: ClimbType) {
    setClimbType(type);
    setGrade(type === "boulder" ? "V2" : "5.10a");
    // Onsight is for ropes, flash for boulders — keep the selection sane.
    if (type === "boulder" && sendType === "onsight") setSendType("flash");
    if (type !== "boulder" && sendType === "flash") setSendType("onsight");
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await api.createClimb({
        name,
        grade,
        grade_system: climbType === "boulder" ? "v_scale" : "yds",
        climb_type: climbType,
        wall_angle: wallAngle === "" ? null : wallAngle,
        location: location || null,
        send_type: sendType,
        attempt_count: attempts,
        notes: notes || null,
        climbed_on: climbedOn,
      });
      setClimbs((prev) => [created, ...(prev ?? [])]);
      setName("");
      setNotes("");
      setAttempts(1);
      setShowForm(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: number) {
    if (!window.confirm("Delete this climb?")) return;
    await api.deleteClimb(id);
    setClimbs((prev) => (prev ?? []).filter((c) => c.id !== id));
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Logbook</h1>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800"
        >
          {showForm ? "Cancel" : "Log a climb"}
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {showForm && (
        <form
          onSubmit={onSubmit}
          className="mt-4 grid grid-cols-1 gap-4 rounded-xl border border-stone-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          <label className="block sm:col-span-2 lg:col-span-1">
            <span className="text-sm font-medium">Name</span>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Cave Classic"
              className={inputCls}
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium">Type</span>
            <select
              value={climbType}
              onChange={(e) => onTypeChange(e.target.value as ClimbType)}
              className={inputCls}
            >
              <option value="boulder">Boulder</option>
              <option value="sport">Sport</option>
              <option value="trad">Trad</option>
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-medium">Grade</span>
            <select
              value={grade}
              onChange={(e) => setGrade(e.target.value)}
              className={inputCls}
            >
              {gradeOptions.map((g) => (
                <option key={g}>{g}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-medium">Result</span>
            <select
              value={sendType}
              onChange={(e) => setSendType(e.target.value as SendType)}
              className={inputCls}
            >
              {climbType === "boulder" ? (
                <option value="flash">Flash</option>
              ) : (
                <option value="onsight">Onsight</option>
              )}
              <option value="redpoint">Redpoint</option>
              <option value="repeat">Repeat</option>
              <option value="project">Project (not sent)</option>
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-medium">Wall angle</span>
            <select
              value={wallAngle}
              onChange={(e) => setWallAngle(e.target.value as WallAngle | "")}
              className={inputCls}
            >
              <option value="">—</option>
              <option value="slab">Slab</option>
              <option value="vertical">Vertical</option>
              <option value="overhang">Overhang</option>
              <option value="roof">Roof</option>
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-medium">Attempts</span>
            <input
              type="number"
              min={1}
              value={attempts}
              onChange={(e) => setAttempts(Number(e.target.value))}
              className={inputCls}
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium">Date</span>
            <input
              type="date"
              required
              value={climbedOn}
              onChange={(e) => setClimbedOn(e.target.value)}
              className={inputCls}
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium">Location</span>
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="gym or crag"
              className={inputCls}
            />
          </label>
          <label className="block sm:col-span-2 lg:col-span-3">
            <span className="text-sm font-medium">Notes</span>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="beta, conditions, how it felt…"
              className={inputCls}
            />
          </label>
          <div className="sm:col-span-2 lg:col-span-3">
            <button
              type="submit"
              disabled={busy}
              className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50"
            >
              {busy ? "Saving…" : "Save climb"}
            </button>
          </div>
        </form>
      )}

      <div className="mt-4 space-y-2">
        {climbs === null && <p className="text-sm text-stone-400">Loading…</p>}
        {climbs?.length === 0 && (
          <p className="rounded-xl border border-dashed border-stone-300 p-8 text-center text-sm text-stone-500">
            No climbs yet — log your first one!
          </p>
        )}
        {climbs?.map((climb) => (
          <div
            key={climb.id}
            className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-xl border border-stone-200 bg-white px-4 py-3"
          >
            <span className="w-12 text-lg font-bold text-emerald-800">
              {climb.grade}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{climb.name}</p>
              <p className="truncate text-xs text-stone-500">
                {[
                  climb.climb_type,
                  climb.wall_angle,
                  climb.location,
                  `${climb.attempt_count} att.`,
                ]
                  .filter(Boolean)
                  .join(" · ")}
                {climb.notes ? ` — ${climb.notes}` : ""}
              </p>
            </div>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${SEND_STYLES[climb.send_type]}`}
            >
              {SEND_LABELS[climb.send_type]}
            </span>
            <span className="text-xs tabular-nums text-stone-400">
              {climb.climbed_on}
            </span>
            <button
              onClick={() => onDelete(climb.id)}
              aria-label={`Delete ${climb.name}`}
              className="text-xs text-stone-400 hover:text-red-600"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
