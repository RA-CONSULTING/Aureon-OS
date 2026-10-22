import React, { useState } from "react";
import { NORTH_STAR_CLAIM, publishNorthStar } from "@/lib/prime/prime-north-star";
import { Card, CardHeader, CardTitle, CardContent, CardDescription, Badge, Button } from "@/components/ui";

export default function NorthStarCard() {
  const mantra = "All that is, all that was, all that shall be, tandem in unity.";
  const [status, setStatus] = useState<string | null>(null);

  async function onPublish() {
    setStatus("Publishing…");
    // In a real scenario, this would publish the new mantra/claim
    // For now, we'''ll just simulate the API call from the original component
    const res = await publishNorthStar();
    setStatus(res.ok ? `Published (HTTP ${res.status})` : `Publish failed (${res.status}): ${res.text}`);
  }

  return (
    <Card className="relative overflow-hidden">
      <CardHeader className="space-y-2">
        <CardTitle>The North Star: Unity</CardTitle>
        <CardDescription className="text-lg font-light tracking-wide !mt-4">
          {mantra}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4">
            <Button onClick={onPublish} disabled={!!status}>
              Publish Unity Claim
            </Button>
            {status && <Badge variant="outline">{status}</Badge>}
        </div>
      </CardContent>
    </Card>
  );
}
