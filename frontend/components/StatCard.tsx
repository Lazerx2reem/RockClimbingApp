export default function StatCard({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="card relative overflow-hidden p-4">
      {/* Accent rail */}
      <span className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-lake-500 to-sage-400" />
      <p className="text-xs font-medium uppercase tracking-wide text-steel-500">
        {label}
      </p>
      <p className="mt-1 text-2xl font-bold text-ink">{value}</p>
    </div>
  );
}
