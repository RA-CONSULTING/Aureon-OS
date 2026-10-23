import React from "react";
import { Card, CardHeader, CardTitle, CardContent, Badge } from "@/components/ui";

type Props = {
  alpha_power: number;
  alpha_wisdom: number;
  alpha_love: number;
  product: number;
  pass: boolean;
};

export default function ACAGatePanel(p: Props) {
  const fmt = (x:number)=> (isFinite(x)? x.toFixed(3):"—");
  const strokeOK = p.pass ? "#10B981" : "#F59E0B";
  const strokeNo = "#EF4444";

  // A simple, stylized golden spiral path that becomes more visible when the gate is open.
  const goldenSpiral = (
    <path
      d="M 0,0 C 10,-10 30,-10 30,0 S 10,10 0,10 C -10,10 -10,-10 -20,-20 S -40,-20 -40,0 S -20,20 0,20 C 20,20 20,-20 40,-40 S 80,-40 80,0 S 40,40 0,40"
      stroke="#FBBF24"
      strokeWidth="1.5"
      fill="none"
      opacity={p.pass ? 0.8 : 0.15}
      transform-origin="center"
      transform="rotate(-90) scale(1.2)"
    />
  );

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle className="flex items-center gap-3">
          Alexander • Cleopatra • Aphrodite
          <Badge variant={p.pass ? "success" : "warning"}>
            {p.pass ? "GATE OPEN" : "HOLD"}
          </Badge>
          <Badge variant="outline">score {fmt(p.product)}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <div className="text-sm grid gap-2">
          <div>▲ <b>Power (Triangle)</b> — containment & non-harm
            <Badge className="ml-2" variant={p.alpha_power>=0.70 ? "success":"destructive"}>
              {fmt(p.alpha_power)}
            </Badge>
          </div>
          <div>■ <b>Wisdom (Square)</b> — clarity & transparency
            <Badge className="ml-2" variant={p.alpha_wisdom>=0.70 ? "success":"destructive"}>
              {fmt(p.alpha_wisdom)}
            </Badge>
          </div>
          <div>◊ <b>Love (Vesica)</b> — consent & reversibility
            <Badge className="ml-2" variant={p.alpha_love>=0.80 ? "success":"destructive"}>
              {fmt(p.alpha_love)}
            </Badge>
          </div>
          <div className="opacity-70 text-xs">
            Moral in geometry: Power holds. Wisdom reveals. Love invites.
          </div>
        </div>

        <div className="flex items-center justify-center">
          {/* Minimal sacred-geometry SVG */}
          <svg viewBox="-120 -120 240 240" width="240" height="240">
            {/* Outer circle (unity/field) */}
            <circle cx="0" cy="0" r="100" fill="none" stroke="#93C5FD" strokeWidth="1.5"/>

            {/* Triangle (Power) */}
            <polygon
              points="0,-100 86.6025403784,50 -86.6025403784,50"
              fill="none"
              stroke={p.alpha_power>=0.70? strokeOK : strokeNo}
              strokeWidth="2.5"
            />
            {/* Square (Wisdom) */}
            <polygon
              points="70.710678,70.710678 -70.710678,70.710678 -70.710678,-70.710678 70.710678,-70.710678"
              fill="none"
              stroke={p.alpha_wisdom>=0.70? strokeOK : strokeNo}
              strokeWidth="2.5"
              opacity="0.9"
            />
            {/* Vesica (Love) */}
            <g>
              <circle cx="0" cy="30.9" r="61.8" fill="none"
                stroke={p.alpha_love>=0.80? strokeOK : strokeNo} strokeWidth="2.5"/>
              <circle cx="0" cy="-30.9" r="61.8" fill="none"
                stroke={p.alpha_love>=0.80? strokeOK : strokeNo} strokeWidth="2.5"/>
            </g>
            
            {/* Golden Spiral (Becoming) */}
            {goldenSpiral}

            {/* Lamp */}
            <circle cx="0" cy="0" r="4" fill="#F59E0B"/>
          </svg>
        </div>
      </CardContent>
    </Card>
  );
}
