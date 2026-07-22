"use client";

import { useEffect, useState } from "react";
import HBarChart from "@/components/HBarChart";
import MonthlySends from "@/components/MonthlySends";
import StatCard from "@/components/StatCard";
import { api } from "@/lib/api";
import type {
  AngleEntry,
  ProgressPoint,
  PyramidEntry,
  StatsSummary,
} from "@/lib/types";

const ANGLE_LABELS: Record<string, string> = {
  slab: "Slab",
  vertical: "Vert",
  overhang: "Over",
  roof: "Roof",
};

export default function DashboardPage() {
  const [summary, setSummary] = useState<StatsSummary | null>(null);
  const [pyramid, setPyramid] = useState<PyramidEntry[] | null>(null);
  const [discipline, setDiscipline] = useState<"boulder" | "route">("boulder");
  const [progress, setProgress] = useState<ProgressPoint[] | null>(null);
  const [angles, setAngles] = useState<AngleEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.summary(), api.progress(), api.angles()])
      .then(([s, p, a]) => {
        setSummary(s);
        setProgress(p);
        setAngles(a);
      })
      .catch((e) => setError(String(e.message)));
  }, []);

  useEffect(() => {
    api.pyramid(discipline).then(setPyramid).catch((e) => setError(String(e.message)));
  }, [discipline]);

  if (error) {
    return <p className="text-sm text-red-600">{error}</p>;
  }

  const empty =
    summary !== null && summary.total_climbs === 0 && summary.total_sessions === 0;

  return (
    <div>
      <h1 className="text-xl font-bold">Dashboard</h1>

      {empty && (
        <p className="mt-4 rounded-xl border border-dashed border-stone-300 p-8 text-center text-sm text-stone-500">
          Nothing here yet — log a climb or a session to see your stats.
        </p>
      )}

      {summary && !empty && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard label="Total sends" value={String(summary.total_sends)} />
            <StatCard
              label="Hardest boulder"
              value={summary.hardest_boulder ?? "—"}
            />
            <StatCard label="Hardest route" value={summary.hardest_route ?? "—"} />
            <StatCard
              label="Training hours"
              value={summary.total_hours.toLocaleString()}
            />
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <section className="rounded-xl border border-stone-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold">Grade pyramid</h2>
                <div className="flex rounded-md border border-stone-200 p-0.5 text-xs font-medium">
                  {(["boulder", "route"] as const).map((d) => (
                    <button
                      key={d}
                      onClick={() => setDiscipline(d)}
                      className={`rounded px-2.5 py-1 capitalize ${
                        discipline === d
                          ? "bg-emerald-700 text-white"
                          : "text-stone-500 hover:bg-stone-100"
                      }`}
                    >
                      {d === "boulder" ? "Boulders" : "Routes"}
                    </button>
                  ))}
                </div>
              </div>
              <div className="mt-4">
                {pyramid === null ? (
                  <p className="text-sm text-stone-400">Loading…</p>
                ) : pyramid.length === 0 ? (
                  <p className="text-sm text-stone-400">
                    No {discipline === "boulder" ? "boulder" : "route"} sends yet.
                  </p>
                ) : (
                  <HBarChart
                    ariaLabel={`Sends by grade (${discipline})`}
                    data={pyramid.map((p) => ({ label: p.grade, value: p.count }))}
                  />
                )}
              </div>
            </section>

            <section className="rounded-xl border border-stone-200 bg-white p-4">
              <h2 className="font-semibold">Sends per month</h2>
              <div className="mt-4">
                {progress === null ? (
                  <p className="text-sm text-stone-400">Loading…</p>
                ) : progress.length === 0 ? (
                  <p className="text-sm text-stone-400">No sends yet.</p>
                ) : (
                  <MonthlySends data={progress} />
                )}
              </div>
            </section>

            <section className="rounded-xl border border-stone-200 bg-white p-4 lg:col-span-2">
              <h2 className="font-semibold">Volume by wall angle</h2>
              <p className="text-xs text-stone-400">
                All logged climbs with a recorded angle.
              </p>
              <div className="mt-4 max-w-md">
                {angles === null ? (
                  <p className="text-sm text-stone-400">Loading…</p>
                ) : angles.length === 0 ? (
                  <p className="text-sm text-stone-400">
                    Tag climbs with a wall angle to see this.
                  </p>
                ) : (
                  <HBarChart
                    ariaLabel="Climb volume by wall angle"
                    data={angles.map((a) => ({
                      label: ANGLE_LABELS[a.wall_angle] ?? a.wall_angle,
                      value: a.count,
                    }))}
                  />
                )}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
