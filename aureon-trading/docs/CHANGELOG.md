# Changelog

All notable changes to the Aureon Trading System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.9.0-beta] - 2025-12-29

### 🎉 First Beta Release - "Four Battlefronts"

The system is now a unified multi-exchange trading platform operating across 4 battlefields.

### Added
- **Multi-Battlefield Architecture** - Unified control of Binance, Kraken, Capital.com, and Alpaca
- **BATTLEFIELDS Configuration** - Per-exchange control of scouts, snipers, and harvesters
- **Round-Robin Scout Distribution** - Scouts spread evenly across all enabled exchanges
- **Cross-Exchange Duplicate Prevention** - Mycelium network prevents position conflicts
- **Alpaca Battlefield Activation** - Full trading enabled (not analytics-only)
- **Grounded README Documentation** - Philosophy explained with code references
- **System Health Check** - `test_system_health.py` validates all modules and configs

### Fixed
- **Capital.com Crypto Routing** - USDT/USDC/FDUSD pairs now correctly route to Binance
- **Exchange Symbol Detection** - `_detect_exchange_for_symbol()` checks suffixes first
- **Sniper Bridge Updates** - Battlefield tracking added to sniper coordination

### Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                    AUREON UNIFIED ECOSYSTEM                      │
├─────────────────────────────────────────────────────────────────┤
│  4 BATTLEFIELDS: Binance | Kraken | Capital.com | Alpaca        │
│  ─────────────────────────────────────────────────────────────  │
│  SCOUTS → SNIPERS → HARVESTERS (per exchange)                   │
│  ─────────────────────────────────────────────────────────────  │
│  MYCELIUM NETWORK: Cross-exchange intelligence & deduplication  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Files Modified
- `aureon_unified_ecosystem.py` - BATTLEFIELDS config, multi-exchange routing
- `irish_patriot_scouts.py` - Round-robin distribution
- `ira_sniper_mode.py` - Battlefield tracking
- `README.md` - Philosophy documentation

---

## [Unreleased]

### Planned for v1.0.0-stable
- [ ] 48-72 hour dry-run validation across all exchanges
- [ ] Automated test suite execution
- [ ] Performance metrics collection
- [ ] Production deployment confirmation

---

## [0.8.0] - 2025-12-27

### Added
- MIT `LICENSE` for code; CC BY 4.0 notice for docs/media
- Core documentation: `docs/Technical-Overview.md`, `docs/Operations.md`, `docs/Troubleshooting.md`
- `CODE_OF_CONDUCT.md` and initial `CHANGELOG.md`
- README header linking technical docs and safety warnings

---

## Version History

| Version | Date | Codename | Status |
|---------|------|----------|--------|
| 0.9.0-beta | 2025-12-29 | Four Battlefronts | **Current** |
| 0.8.0 | 2025-12-27 | Documentation | Previous |
| 1.0.0-stable | TBD | The Unified Army | Planned |

---

## Release Process

1. **Beta (0.x.x)** - Feature complete, testing in progress
2. **Stable (1.x.x)** - Production validated, safe for live trading
3. **Minor (x.Y.x)** - New features, backward compatible
4. **Patch (x.x.Z)** - Bug fixes only
