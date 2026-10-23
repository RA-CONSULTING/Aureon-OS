import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import sero, { ActuationRequest, AuditRecord, SeroConfig, SeroDirectives, DirectivePacket } from "../lib/sero/sero-core";

type Ctx = {
  config: typeof SeroConfig;
  directives: typeof SeroDirectives;
  updateConfig: (c: Partial<typeof SeroConfig>) => void;
  updateDirectives: (packet: DirectivePacket) => void;
  actuate: (req: ActuationRequest) => AuditRecord;
  audit: AuditRecord[];
};

const SeroCtx = createContext<Ctx | null>(null);

export const SeroProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  const [tick, setTick] = useState(0);
  const refresh = useCallback(() => setTick(x => x+1), []);

  const api: Ctx = useMemo(() => ({
    config: sero.SeroConfig,
    directives: sero.SeroDirectives,
    updateConfig: (c: Partial<typeof SeroConfig>) => { Object.assign(sero.SeroConfig, c); refresh(); },
    updateDirectives: (packet: DirectivePacket) => { sero.applyDirectivePacket(packet); refresh(); },
    actuate: (req: ActuationRequest) => {
      const rec = sero.actuate(req);
      refresh(); // to update audit log
      return rec;
    },
    audit: sero.listAudit(),
  }), [tick, refresh]);

  return <SeroCtx.Provider value={api}>{children}</SeroCtx.Provider>;
};

export function useSero() {
  const ctx = useContext(SeroCtx);
  if (!ctx) throw new Error("useSero must be used within SeroProvider");
  return ctx;
}
