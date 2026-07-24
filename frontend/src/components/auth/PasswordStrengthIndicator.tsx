import { useMemo } from "react";
import { Check, X } from "lucide-react";

interface PasswordStrengthIndicatorProps {
  password: string;
}

interface Requirement {
  label: string;
  met: boolean;
}

export function PasswordStrengthIndicator({ password }: PasswordStrengthIndicatorProps) {
  const requirements: Requirement[] = useMemo(() => [
    { label: "At least 8 characters", met: password.length >= 8 },
    { label: "Contains uppercase letter", met: /[A-Z]/.test(password) },
    { label: "Contains lowercase letter", met: /[a-z]/.test(password) },
    { label: "Contains a number", met: /[0-9]/.test(password) },
  ], [password]);

  const strength = useMemo(() => {
    const metCount = requirements.filter(r => r.met).length;
    if (metCount === 0) return { level: 0, label: "", color: "" };
    if (metCount === 1) return { level: 1, label: "Weak", color: "bg-destructive" };
    if (metCount === 2) return { level: 2, label: "Fair", color: "bg-warning" };
    if (metCount === 3) return { level: 3, label: "Good", color: "bg-warning" };
    return { level: 4, label: "Strong", color: "bg-success" };
  }, [requirements]);

  if (!password) return null;

  return (
    <div className="space-y-2 mt-2">
      {/* Strength Bar */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden flex gap-0.5">
          {[1, 2, 3, 4].map((level) => (
            <div
              key={level}
              className={`flex-1 h-full rounded-full transition-colors ${
                level <= strength.level ? strength.color : "bg-muted"
              }`}
            />
          ))}
        </div>
        {strength.label && (
          <span className={`text-xs font-medium ${
            strength.level === 4 ? "text-success" :
            strength.level === 3 ? "text-warning" :
            strength.level === 2 ? "text-warning" :
            "text-destructive"
          }`}>
            {strength.label}
          </span>
        )}
      </div>

      {/* Requirements List */}
      <div className="grid grid-cols-2 gap-1">
        {requirements.map((req) => (
          <div key={req.label} className="flex items-center gap-1.5 text-xs">
            {req.met ? (
              <Check className="h-3 w-3 text-success" />
            ) : (
              <X className="h-3 w-3 text-muted-foreground" />
            )}
            <span className={req.met ? "text-foreground" : "text-muted-foreground"}>
              {req.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
