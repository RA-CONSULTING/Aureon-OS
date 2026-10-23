"""One entry point for the staged Aureon Fusion tree.

    python -m aureon_fusion
    python -m aureon_fusion --join-offline
"""

from __future__ import annotations

import json
import sys

from .join import join_layers, status_report


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help", "help"}:
        print("usage: python -m aureon_fusion [--json] [--join-offline]")
        print("live trading is off. --join-offline composes layers with no network.")
        return 0
    as_json = "--json" in args
    if "--join-offline" in args:
        def _offline(_url: str) -> bytes:
            raise ValueError("offline")

        report = status_report()
        try:
            report["layers"] = join_layers(field_transport=_offline, market_transport=_offline)
        except Exception as exc:
            report["layers_error"] = type(exc).__name__
            report["layers"] = None
    else:
        report = status_report()
    if report.get("live_trading") is not False or report.get("may_act") is not False:
        from aureon.autonomous.autonomy_mode import autonomy_mode

        if autonomy_mode() != "full":
            print("AUREON_FUSION_LIVE_HOLD refused an armed status", file=sys.stderr)
            return 2
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        live = bool(report.get("live_trading"))
        may_act = bool(report.get("may_act"))
        print("Aureon Fusion")
        print(f"live_trading: {str(live).lower()}")
        print(f"paper_default: {str(not live).lower()}")
        print(f"dry_run_default: {str(not live).lower()}")
        print(f"may_act: {str(may_act).lower()}")
        print("action gate: " + ("RELEASE" if may_act else "HOLD"))
        print("publication: staging in this private repo; not pushed to Aureon-OS")
        print("")
        print("capabilities:")
        for name, info in report["capabilities"].items():
            flag = "present" if info["present"] else "MISSING"
            print(f"  {flag:7} {name:20} {info['path']}")
        print("")
        print("not retrieved:")
        for item in report["unavailable_sources"]:
            print(f"  {item['repo']}: {item['reason']}")
        if "layers" in report:
            layers = report.get("layers") or {}
            print("")
            print(f"layer join: status={layers.get('status')} may_act={layers.get('may_act')}")
            for layer in layers.get("layers") or []:
                print(
                    f"  {layer.get('id')}: truth={layer.get('truth_status')} "
                    f"gate={layer.get('gate')} reason={layer.get('reason')}"
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())
