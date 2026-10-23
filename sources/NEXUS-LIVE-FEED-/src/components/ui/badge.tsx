import * as React from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info";

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: Variant;
}

const Badge = ({ className, variant = "default", ...props }: BadgeProps) => {
  const map: Record<Variant, string> = {
    default:
      "border border-[rgba(102,76,255,0.45)] bg-gradient-to-r from-[#4c7cff]/80 via-[#6f4bff]/75 to-[#f5d26a]/80 text-[#f8fbff]",
    secondary: "border border-[rgba(82,108,255,0.35)] bg-[rgba(20,32,76,0.6)] text-[#d6e3ff]",
    destructive: "border border-[rgba(236,72,153,0.45)] bg-[rgba(236,72,153,0.22)] text-[#ffe8f4]",
    outline: "border border-[rgba(245,210,106,0.45)] text-[#f5d26a]",
    success: "border border-[rgba(45,212,191,0.45)] bg-[rgba(34,197,247,0.2)] text-[#e9fcff]",
    warning: "border border-[rgba(245,210,106,0.55)] bg-[rgba(245,210,106,0.24)] text-[#fff8de]",
    info: "border border-[rgba(96,165,250,0.45)] bg-[rgba(59,130,246,0.22)] text-[#e6f3ff]",
  };
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium backdrop-blur",
        map[variant],
        className
      )}
      {...props}
    />
  );
};

export { Badge };
export default Badge;
