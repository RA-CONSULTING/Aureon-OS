/**
 * useSupportProject — timer-based "support the project" prompting.
 *
 * Free-access model: the console never blocks. Cumulative runtime is tracked in
 * localStorage (ticking only while the tab is visible); once the user has run
 * the console for SUPPORT_PROMPT_HOURS a small, dismissible prompt becomes due.
 * "Maybe later" snoozes for SUPPORT_SNOOZE_HOURS of further runtime; confirmed
 * support snoozes for THANKS_DAYS of wall-clock time.
 */

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "aureon_support_project_v1";
const TICK_MS = 60_000; // accumulate runtime once a minute

const PROMPT_HOURS = Number(import.meta.env.VITE_SUPPORT_PROMPT_HOURS ?? "4") || 4;
const SNOOZE_HOURS = Number(import.meta.env.VITE_SUPPORT_SNOOZE_HOURS ?? "12") || 12;
const THANKS_DAYS = 7;

const DEFAULT_LINKS = "https://pay.sumup.com/b2c/QGFKREQI,https://pay.sumup.com/b2c/QFTPOX6U";

export const SUPPORT_PAYMENT_URLS: string[] = String(
  (import.meta.env.VITE_SUPPORT_PAYMENT_URLS as string | undefined) || DEFAULT_LINKS,
)
  .split(",")
  .map((u) => u.trim())
  .filter(Boolean);

interface SupportState {
  runtimeMs: number;          // cumulative visible runtime
  promptAfterMs: number;      // runtime threshold for the next prompt
  thankedUntil: number;       // wall-clock ms; suppress prompts until then
}

function loadState(): SupportState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<SupportState>;
      return {
        runtimeMs: Number(parsed.runtimeMs) || 0,
        promptAfterMs: Number(parsed.promptAfterMs) || PROMPT_HOURS * 3_600_000,
        thankedUntil: Number(parsed.thankedUntil) || 0,
      };
    }
  } catch {
    // corrupted state — start fresh
  }
  return { runtimeMs: 0, promptAfterMs: PROMPT_HOURS * 3_600_000, thankedUntil: 0 };
}

function saveState(state: SupportState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // storage full/unavailable — prompting just stays runtime-local
  }
}

export function useSupportProject() {
  const [due, setDue] = useState(false);
  const [runtimeHours, setRuntimeHours] = useState(0);

  useEffect(() => {
    const evaluate = () => {
      const s = loadState();
      setRuntimeHours(s.runtimeMs / 3_600_000);
      setDue(Date.now() >= s.thankedUntil && s.runtimeMs >= s.promptAfterMs);
    };
    evaluate();
    const timer = setInterval(() => {
      if (document.visibilityState !== "visible") return;
      const s = loadState();
      s.runtimeMs += TICK_MS;
      saveState(s);
      evaluate();
    }, TICK_MS);
    return () => clearInterval(timer);
  }, []);

  const snooze = useCallback(() => {
    const s = loadState();
    s.promptAfterMs = s.runtimeMs + SNOOZE_HOURS * 3_600_000;
    saveState(s);
    setDue(false);
  }, []);

  const thank = useCallback(() => {
    const s = loadState();
    s.thankedUntil = Date.now() + THANKS_DAYS * 86_400_000;
    s.promptAfterMs = s.runtimeMs + SNOOZE_HOURS * 3_600_000;
    saveState(s);
    setDue(false);
  }, []);

  return { due, runtimeHours, snooze, thank, links: SUPPORT_PAYMENT_URLS };
}
