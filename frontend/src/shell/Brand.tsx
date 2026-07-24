/**
 * BrandMark — the Aureon vector logo.
 *
 * A gold tile with a clean geometric "A" nexus monogram, drawn as inline SVG so it
 * stays crisp at any size (header, favicon, social). Brand-consistent gold regardless
 * of light/dark theme — logos don't theme. Replaces the photographic JPEG that used to
 * be center-cropped into a 32px square.
 */

export function BrandMark({ size = 32, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      role="img"
      aria-label="Aureon"
      className={className}
    >
      <defs>
        <linearGradient id="aureon-mark-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#eaa11d" />
          <stop offset="1" stopColor="#cf7f09" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="7" fill="url(#aureon-mark-g)" />
      <path
        d="M16 7 L9 25 M16 7 L23 25 M11.7 19.4 L20.3 19.4"
        fill="none"
        stroke="#1c1405"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
