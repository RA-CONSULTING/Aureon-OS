
import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const MandalaOverlay = ({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) => {
  return (
    <div className={cn("pointer-events-none absolute inset-0 z-0 opacity-20", className)} {...props}>
      <svg
        className="h-full w-full"
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <radialGradient id="mandala-core" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(255,255,255,0.22)" />
            <stop offset="65%" stopColor="rgba(255,255,255,0.06)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0)" />
          </radialGradient>
          <linearGradient id="mandala-lines" x1="0%" x2="100%" y1="0%" y2="100%">
            <stop offset="0%" stopColor="rgba(125,211,252,0.45)" />
            <stop offset="50%" stopColor="rgba(251,191,36,0.35)" />
            <stop offset="100%" stopColor="rgba(244,114,182,0.4)" />
          </linearGradient>
          <pattern id="mandala-stars" width="12" height="12" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="0.6" fill="rgba(255,255,255,0.4)" />
            <circle cx="8" cy="5" r="0.8" fill="rgba(255,255,255,0.25)" />
            <circle cx="5" cy="10" r="0.5" fill="rgba(255,255,255,0.35)" />
          </pattern>
        </defs>
        <rect width="100" height="100" fill="url(#mandala-stars)" opacity="0.35" />
        <circle cx="50" cy="50" r="45" fill="url(#mandala-core)" opacity="0.5" />
        <g transform="translate(50 50)">
          {[...Array(18)].map((_, i) => (
            <g key={`ring-${i}`} transform={`rotate(${(i * 360) / 18})`}>
              <circle
                cx="0"
                cy="0"
                r={20 + i * 1.8}
                fill="none"
                stroke="url(#mandala-lines)"
                strokeWidth={i % 3 === 0 ? 0.8 : 0.35}
                opacity={i % 2 === 0 ? 0.22 : 0.1}
              />
            </g>
          ))}
          {[...Array(12)].map((_, i) => (
            <g key={`petal-${i}`} transform={`rotate(${i * 30})`}>
              <path
                d="M0,-28 C 9,-18 9,18 0,28"
                fill="none"
                stroke="url(#mandala-lines)"
                strokeWidth="0.5"
                opacity="0.35"
              />
              <circle cx="28" cy="0" r="3.8" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.25)" strokeWidth="0.4" />
            </g>
          ))}
          <polygon
            points="0,-16 13.856,8 -13.856,8"
            fill="none"
            stroke="rgba(255,255,255,0.45)"
            strokeWidth="0.6"
            opacity="0.65"
          />
          <polygon
            points="0,-28 24.248,14 -24.248,14"
            fill="none"
            stroke="rgba(255,255,255,0.15)"
            strokeWidth="0.4"
            opacity="0.55"
          />
        </g>
      </svg>
    </div>
  );
};

export default MandalaOverlay;
