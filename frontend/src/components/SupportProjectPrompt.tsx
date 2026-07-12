/**
 * SupportProjectPrompt — the non-intrusive "support the project" card.
 *
 * A small dismissible corner card (never a modal; the console is never
 * blocked). Shown only when useSupportProject says a prompt is due. Opens the
 * SumUp support link in a new tab; the user self-confirms with the amount they
 * gave, which credits their gas tank via the existing gas-tank-topup edge
 * function and records a payment_transactions row (provider 'sumup', status
 * 'self_confirmed') for reconciliation against SumUp payouts.
 */

import { useState } from "react";
import { Heart, X } from "lucide-react";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useSupportProject } from "@/hooks/useSupportProject";

export function SupportProjectPrompt() {
  const { due, runtimeHours, snooze, thank, links } = useSupportProject();
  const [opened, setOpened] = useState(false);
  const [amount, setAmount] = useState("10");
  const [confirming, setConfirming] = useState(false);

  if (!due || links.length === 0) return null;

  const supportUrl = links[0];

  const openLink = () => {
    window.open(supportUrl, "_blank", "noopener,noreferrer");
    setOpened(true);
  };

  const selfConfirm = async () => {
    const value = Math.max(1, Math.min(10_000, Number(amount) || 0));
    setConfirming(true);
    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const userId = sessionData.session?.user?.id;
      if (!userId) {
        toast.info("Sign in to have your support credit the gas tank. Thank you either way!");
        thank();
        return;
      }
      // Credit the tank through the existing top-up path (account creation,
      // TOP_UP transaction, realtime update all included).
      const { error: topUpError } = await supabase.functions.invoke("gas-tank-topup", {
        body: { userId, amount: value, membershipType: "standard" },
      });
      if (topUpError) throw topUpError;
      // Reconciliation trail: self-confirmed SumUp support.
      await supabase.from("payment_transactions").insert({
        user_id: userId,
        amount: value,
        currency: "GBP",
        payment_provider: "sumup",
        payment_status: "self_confirmed",
        payment_url: supportUrl,
        metadata: {
          purpose: "support_the_project",
          created_from: "support_prompt",
          runtime_hours: Math.round(runtimeHours * 10) / 10,
        },
      });
      toast.success(`Thank you for supporting Aureon! £${value} added to your gas tank.`);
      thank();
    } catch (err) {
      const message = err instanceof Error ? err.message : "something went wrong";
      toast.error(`Could not record your support: ${message}`);
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-sm">
      <Card className="border-border/60 shadow-lg">
        <CardContent className="p-4 space-y-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <Heart className="h-4 w-4 text-primary shrink-0" />
              <p className="text-sm font-medium">Enjoying Aureon?</p>
            </div>
            <button
              type="button"
              aria-label="Dismiss"
              onClick={snooze}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <p className="text-xs text-muted-foreground">
            Aureon is free to run — you&apos;ve clocked ~{Math.floor(runtimeHours)}h with it.
            If it&apos;s earning its keep, consider supporting the project.
          </p>
          {!opened ? (
            <div className="flex gap-2">
              <Button size="sm" className="flex-1" onClick={openLink}>
                Support the project
              </Button>
              <Button size="sm" variant="ghost" onClick={snooze}>
                Maybe later
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">
                Once you&apos;ve paid, confirm the amount to credit your gas tank:
              </p>
              <div className="flex gap-2">
                <Input
                  type="number"
                  min={1}
                  max={10000}
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="h-8 w-24"
                  aria-label="Support amount in GBP"
                />
                <Button size="sm" onClick={selfConfirm} disabled={confirming}>
                  {confirming ? "Recording…" : "I've supported"}
                </Button>
                <Button size="sm" variant="ghost" onClick={snooze}>
                  Skip
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
