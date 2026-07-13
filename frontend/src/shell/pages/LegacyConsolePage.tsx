/**
 * The original nine-tab operational console, preserved intact inside the
 * unified shell. Its hash-tab navigation (#trading, #inventory, …) keeps
 * working within this route.
 */

import { LegacyConsole } from "@/App";

export default function LegacyConsolePage() {
  return <LegacyConsole />;
}
