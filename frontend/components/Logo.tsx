/**
 * Ascent brand mark: an alpine peak mirrored in a still lake.
 * Uses the palette's lake blue and sage teal. `className` controls the size.
 */
export default function Logo({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      role="img"
      aria-label="Ascent logo"
      className={className}
    >
      {/* Peak (reflection above the waterline) */}
      <path d="M4 18 L13 5 L20 14 L24 9 L28 18 Z" fill="#3A6A9B" />
      <path d="M13 5 L16.5 10.2 L11.4 12.1 Z" fill="#F1F5F6" fillOpacity="0.9" />
      {/* Lake reflection below the waterline */}
      <path d="M4 20 L13 30 L20 22.5 L24 26 L28 20 Z" fill="#A3C6C4" fillOpacity="0.85" />
      {/* Waterline */}
      <rect x="3" y="18.4" width="26" height="1.4" rx="0.7" fill="#3C4B59" fillOpacity="0.4" />
    </svg>
  );
}
