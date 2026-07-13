# Aureon Frontend Evolution Queue

- Generated: `2026-05-15T18:32:02.587326+00:00`
- Status: `evolution_queue_ready_with_blockers`
- Repo: `C:\Users\user\aureon-trading-integrated-main-20260508`

## Summary

- `queue_count`: `585`
- `ready_adapter_count`: `462`
- `blocked_count`: `40`
- `archive_candidate_count`: `3`
- `generated_output_link_count`: `6`
- `target_screen_count`: `6`
- `highest_priority`: `100`

## Target Counts

```json
{
  "by_source_kind": {
    "accounting_generated_html": 20,
    "frontend_component": 378,
    "frontend_config": 4,
    "frontend_core": 103,
    "frontend_page": 2,
    "frontend_service": 7,
    "legacy_template": 6,
    "local_dashboard_server": 20,
    "public_asset": 41,
    "vault_ui_static": 4
  },
  "by_status": {
    "archive_candidate": 3,
    "blocked_security_review": 40,
    "link_generated_output": 6,
    "needs_safe_status_adapter": 74,
    "ready_for_frontend_adapter": 462
  },
  "by_target_screen": {
    "accounting": 52,
    "overview": 142,
    "research": 49,
    "saas_security": 36,
    "self_improvement": 49,
    "trading": 257
  }
}
```

## Work Orders

| Priority | Status | Target | Source | Action |
| ---: | --- | --- | --- | --- |
| 100 | `blocked_security_review` | `overview` | `frontend/src/components/WarRoomDashboard.tsx` | Create a read-only blocker card in Overview before any interactive control. |
| 100 | `blocked_security_review` | `overview` | `frontend/src/components/warroom/GasTankDisplay.tsx` | Create a read-only blocker card in Overview before any interactive control. |
| 100 | `blocked_security_review` | `saas_security` | `frontend/src/components/AdminKYCDashboard.tsx` | Create a read-only blocker card in SaaS Security before any interactive control. |
| 100 | `blocked_security_review` | `saas_security` | `frontend/src/components/AdminPaymentVerification.tsx` | Create a read-only blocker card in SaaS Security before any interactive control. |
| 100 | `blocked_security_review` | `saas_security` | `frontend/src/components/AuthForm.tsx` | Create a read-only blocker card in SaaS Security before any interactive control. |
| 100 | `blocked_security_review` | `saas_security` | `frontend/src/components/auth/APIKeySecurityGuide.tsx` | Create a read-only blocker card in SaaS Security before any interactive control. |
| 100 | `blocked_security_review` | `self_improvement` | `aureon/command_centers/aureon_command_center.py` | Create a read-only blocker card in Self-Improvement before any interactive control. |
| 100 | `ready_for_frontend_adapter` | `self_improvement` | `aureon/command_centers/aureon_queen_realtime_command_center.py` | Create frontend/src/components/unified/AureonQueenRealtimeCommandCenterStatusCard.tsx and mount it in the Self-Improvement screen. |
| 100 | `ready_for_frontend_adapter` | `self_improvement` | `aureon/command_centers/aureon_war_band_enhanced.py` | Create frontend/src/components/unified/AureonWarBandEnhancedStatusCard.tsx and mount it in the Self-Improvement screen. |
| 100 | `blocked_security_review` | `trading` | `aureon/bots/orca_command_center.py` | Create a read-only blocker card in Trading before any interactive control. |
| 100 | `ready_for_frontend_adapter` | `trading` | `aureon/command_centers/aureon_atn_command_center.py` | Create frontend/src/components/unified/AureonAtnCommandCenterStatusCard.tsx and mount it in the Trading screen. |
| 100 | `ready_for_frontend_adapter` | `trading` | `aureon/command_centers/aureon_command_center_enhanced.py` | Create frontend/src/components/unified/AureonCommandCenterEnhancedStatusCard.tsx and mount it in the Trading screen. |
| 100 | `ready_for_frontend_adapter` | `trading` | `aureon/command_centers/aureon_strategic_war_planner.py` | Create frontend/src/components/unified/AureonStrategicWarPlannerStatusCard.tsx and mount it in the Trading screen. |
| 100 | `ready_for_frontend_adapter` | `trading` | `aureon/command_centers/aureon_war_band.py` | Create frontend/src/components/unified/AureonWarBandStatusCard.tsx and mount it in the Trading screen. |
| 100 | `ready_for_frontend_adapter` | `trading` | `aureon/command_centers/war_room.py` | Create frontend/src/components/unified/WarRoomStatusCard.tsx and mount it in the Trading screen. |
| 100 | `ready_for_frontend_adapter` | `trading` | `aureon/command_centers/war_strategy.py` | Create frontend/src/components/unified/WarStrategyStatusCard.tsx and mount it in the Trading screen. |
| 100 | `blocked_security_review` | `trading` | `frontend/src/components/APIKeyManager.tsx` | Create a read-only blocker card in Trading before any interactive control. |
| 100 | `blocked_security_review` | `trading` | `frontend/src/components/AutonomousTradingGuide.tsx` | Create a read-only blocker card in Trading before any interactive control. |
| 100 | `blocked_security_review` | `trading` | `frontend/src/components/BinanceCredentialsSettings.tsx` | Create a read-only blocker card in Trading before any interactive control. |
| 100 | `blocked_security_review` | `trading` | `frontend/src/components/LiveDataDashboard.tsx` | Create a read-only blocker card in Trading before any interactive control. |
| 100 | `blocked_security_review` | `trading` | `frontend/src/components/LiveTradingTestPanel.tsx` | Create a read-only blocker card in Trading before any interactive control. |
| 100 | `blocked_security_review` | `trading` | `frontend/src/components/QuickTrade.tsx` | Create a read-only blocker card in Trading before any interactive control. |
| 100 | `blocked_security_review` | `trading` | `frontend/src/components/TradingSettingsPanel.tsx` | Create a read-only blocker card in Trading before any interactive control. |
| 100 | `blocked_security_review` | `trading` | `frontend/src/components/warroom/LiveTradeStream.tsx` | Create a read-only blocker card in Trading before any interactive control. |
| 100 | `blocked_security_review` | `trading` | `frontend/src/core/globalSystemsManager.ts` | Create a read-only blocker card in Trading before any interactive control. |
| 100 | `blocked_security_review` | `trading` | `frontend/src/core/startupHarvester.ts` | Create a read-only blocker card in Trading before any interactive control. |
| 100 | `blocked_security_review` | `trading` | `frontend/src/core/unifiedExchangeClient.ts` | Create a read-only blocker card in Trading before any interactive control. |
| 100 | `blocked_security_review` | `trading` | `frontend/src/core/unifiedOrchestrator.ts` | Create a read-only blocker card in Trading before any interactive control. |
| 100 | `blocked_security_review` | `trading` | `templates/queen_bot_intelligence.html` | Create a read-only blocker card in Trading before any interactive control. |
| 100 | `ready_for_frontend_adapter` | `trading` | `templates/queen_dashboard.html` | Create frontend/src/components/unified/QueenDashboardStatusCard.tsx and mount it in the Trading screen. |
| 100 | `ready_for_frontend_adapter` | `trading` | `templates/queen_sero_dashboard.html` | Create frontend/src/components/unified/QueenSeroDashboardStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/components/warroom/AurisNodesPanel.tsx` | Create frontend/src/components/unified/AurisnodespanelStatusCard.tsx and mount it in the Accounting screen. |
| 95 | `ready_for_frontend_adapter` | `saas_security` | `frontend/src/components/NexusLiveDashboard.tsx` | Create frontend/src/components/unified/NexuslivedashboardStatusCard.tsx and mount it in the SaaS Security screen. |
| 95 | `ready_for_frontend_adapter` | `saas_security` | `frontend/src/components/warroom/FullEcosystemStatus.tsx` | Create frontend/src/components/unified/FullecosystemstatusStatusCard.tsx and mount it in the SaaS Security screen. |
| 95 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/SystemsIntegrationDashboard.tsx` | Create frontend/src/components/unified/SystemsintegrationdashboardStatusCard.tsx and mount it in the Self-Improvement screen. |
| 95 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/warroom/EcosystemStatus.tsx` | Create frontend/src/components/unified/EcosystemstatusStatusCard.tsx and mount it in the Self-Improvement screen. |
| 95 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/warroom/QuantumStatePanel.tsx` | Create frontend/src/components/unified/QuantumstatepanelStatusCard.tsx and mount it in the Self-Improvement screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/AureonLiveDashboard.tsx` | Create frontend/src/components/unified/AureonlivedashboardStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/PerformanceMetricsDashboard.tsx` | Create frontend/src/components/unified/PerformancemetricsdashboardStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/RiskManagementDashboard.tsx` | Create frontend/src/components/unified/RiskmanagementdashboardStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/SolarWeatherDashboard.tsx` | Create frontend/src/components/unified/SolarweatherdashboardStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/TradingDashboard.tsx` | Create frontend/src/components/unified/TradingdashboardStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/ActivePositionsPanel.tsx` | Create frontend/src/components/unified/ActivepositionspanelStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/AurisNodesOrbit.tsx` | Create frontend/src/components/unified/AurisnodesorbitStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/BattleMap.tsx` | Create frontend/src/components/unified/BattlemapStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/ExchangeBalances.tsx` | Create frontend/src/components/unified/ExchangebalancesStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/HarmonicWaveform6DStatus.tsx` | Create frontend/src/components/unified/Harmonicwaveform6DstatusStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/HistoricalTimeline.tsx` | Create frontend/src/components/unified/HistoricaltimelineStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/KillConfirmationBanner.tsx` | Create frontend/src/components/unified/KillconfirmationbannerStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/LiveStrikeStream.tsx` | Create frontend/src/components/unified/LivestrikestreamStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/MetricsHQ.tsx` | Create frontend/src/components/unified/MetricshqStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/MultiExchangePanel.tsx` | Create frontend/src/components/unified/MultiexchangepanelStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/ProbabilityFusionPanel.tsx` | Create frontend/src/components/unified/ProbabilityfusionpanelStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/ProbabilityMatrixDisplay.tsx` | Create frontend/src/components/unified/ProbabilitymatrixdisplayStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/ProjectionHorizon.tsx` | Create frontend/src/components/unified/ProjectionhorizonStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/TemporalLadderStatus.tsx` | Create frontend/src/components/unified/TemporalladderstatusStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/TradeControlsHeader.tsx` | Create frontend/src/components/unified/TradecontrolsheaderStatusCard.tsx and mount it in the Trading screen. |
| 95 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/warroom/TradingStatusPanel.tsx` | Create frontend/src/components/unified/TradingstatuspanelStatusCard.tsx and mount it in the Trading screen. |
| 93 | `ready_for_frontend_adapter` | `overview` | `aureon/command_centers/__init__.py` | Create frontend/src/components/unified/InitStatusCard.tsx and mount it in the Overview screen. |
| 93 | `ready_for_frontend_adapter` | `overview` | `aureon/command_centers/aureon_command_center_lite.py` | Create frontend/src/components/unified/AureonCommandCenterLiteStatusCard.tsx and mount it in the Overview screen. |
| 91 | `blocked_security_review` | `overview` | `frontend/src/components/LiveEmotionalReader.tsx` | Create a read-only blocker card in Overview before any interactive control. |
| 91 | `blocked_security_review` | `overview` | `frontend/src/components/PaymentGate.tsx` | Create a read-only blocker card in Overview before any interactive control. |
| 89 | `ready_for_frontend_adapter` | `research` | `aureon/vault/ui/static/bridge_invite.html` | Create frontend/src/components/unified/BridgeInviteStatusCard.tsx and mount it in the Research screen. |
| 89 | `ready_for_frontend_adapter` | `research` | `aureon/vault/ui/static/index.html` | Create frontend/src/components/unified/IndexStatusCard.tsx and mount it in the Research screen. |
| 89 | `ready_for_frontend_adapter` | `self_improvement` | `aureon/bots/orca_launcher.py` | Create frontend/src/components/unified/OrcaLauncherStatusCard.tsx and mount it in the Self-Improvement screen. |
| 89 | `ready_for_frontend_adapter` | `self_improvement` | `aureon/wisdom/aureon_samuel_agent.py` | Create frontend/src/components/unified/AureonSamuelAgentStatusCard.tsx and mount it in the Self-Improvement screen. |
| 89 | `ready_for_frontend_adapter` | `trading` | `templates/aureon_face.html` | Create frontend/src/components/unified/AureonFaceStatusCard.tsx and mount it in the Trading screen. |
| 89 | `ready_for_frontend_adapter` | `trading` | `templates/queen_live_panel.html` | Create frontend/src/components/unified/QueenLivePanelStatusCard.tsx and mount it in the Trading screen. |
| 85 | `blocked_security_review` | `accounting` | `Kings_Accounting_Suite/output/filing_handoff/00000000/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/accounts_readable_for_ixbrl.html` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `blocked_security_review` | `accounting` | `Kings_Accounting_Suite/output/filing_handoff/00000000/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/computation_readable_for_ixbrl.html` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `blocked_security_review` | `accounting` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/accounts_readable_for_ixbrl.html` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `blocked_security_review` | `accounting` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/accounts_readable_for_ixbrl_2.html` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `blocked_security_review` | `accounting` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/05_hmrc_corporation_tax/computation_readable_for_ixbrl.html` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `blocked_security_review` | `accounting` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/07_review_workpapers/accounts_readable_for_ixbrl.html` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `blocked_security_review` | `accounting` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/07_review_workpapers/accounts_readable_for_ixbrl_2.html` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `blocked_security_review` | `accounting` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/07_review_workpapers/draft_accounts_readable_not_ixbrl.html` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `blocked_security_review` | `accounting` | `Kings_Accounting_Suite/output/filing_handoff/NI696693/2024-05-01_to_2025-04-30/07_review_workpapers/draft_accounts_readable_not_ixbrl_2.html` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `blocked_security_review` | `accounting` | `Kings_Accounting_Suite/output/statutory/00000000/2024-05-01_to_2025-04-30/accounts_readable_for_ixbrl.html` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `blocked_security_review` | `accounting` | `Kings_Accounting_Suite/output/statutory/00000000/2024-05-01_to_2025-04-30/computation_readable_for_ixbrl.html` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `blocked_security_review` | `accounting` | `Kings_Accounting_Suite/output/statutory/NI696693/2024-05-01_to_2025-04-30/accounts_readable_for_ixbrl.html` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `blocked_security_review` | `accounting` | `Kings_Accounting_Suite/output/statutory/NI696693/2024-05-01_to_2025-04-30/computation_readable_for_ixbrl.html` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `blocked_security_review` | `accounting` | `Kings_Accounting_Suite/output/statutory/NI696693/2024-05-01_to_2025-04-30/draft_accounts_readable_not_ixbrl.html` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `blocked_security_review` | `accounting` | `public/tarot-major-arcana.json` | Create a read-only blocker card in Accounting before any interactive control. |
| 85 | `ready_for_frontend_adapter` | `overview` | `frontend/src/components/EarthResonanceDashboard.tsx` | Create frontend/src/components/unified/EarthresonancedashboardStatusCard.tsx and mount it in the Overview screen. |
| 85 | `ready_for_frontend_adapter` | `overview` | `frontend/src/components/NoaaSpaceWeatherDashboard.tsx` | Create frontend/src/components/unified/NoaaspaceweatherdashboardStatusCard.tsx and mount it in the Overview screen. |
| 85 | `ready_for_frontend_adapter` | `overview` | `frontend/src/components/QuantumDashboard.tsx` | Create frontend/src/components/unified/QuantumdashboardStatusCard.tsx and mount it in the Overview screen. |
| 85 | `ready_for_frontend_adapter` | `overview` | `frontend/src/components/SimulationDashboard.tsx` | Create frontend/src/components/unified/SimulationdashboardStatusCard.tsx and mount it in the Overview screen. |
| 85 | `ready_for_frontend_adapter` | `overview` | `frontend/src/components/TemporalLadderDashboard.tsx` | Create frontend/src/components/unified/TemporalladderdashboardStatusCard.tsx and mount it in the Overview screen. |
| 85 | `ready_for_frontend_adapter` | `overview` | `frontend/src/components/UnifiedOrcaCommandDashboard.tsx` | Create frontend/src/components/unified/UnifiedorcacommanddashboardStatusCard.tsx and mount it in the Overview screen. |
| 85 | `ready_for_frontend_adapter` | `overview` | `frontend/src/components/warroom/CommandCenter.tsx` | Create frontend/src/components/unified/CommandcenterStatusCard.tsx and mount it in the Overview screen. |
| 85 | `ready_for_frontend_adapter` | `overview` | `frontend/src/components/warroom/DuckCommandoIntel.tsx` | Create frontend/src/components/unified/DuckcommandointelStatusCard.tsx and mount it in the Overview screen. |
| 85 | `ready_for_frontend_adapter` | `overview` | `frontend/src/components/warroom/PrimeSealStatusPanel.tsx` | Create frontend/src/components/unified/PrimesealstatuspanelStatusCard.tsx and mount it in the Overview screen. |
| 85 | `ready_for_frontend_adapter` | `overview` | `frontend/src/components/warroom/PrismFrequencyPanel.tsx` | Create frontend/src/components/unified/PrismfrequencypanelStatusCard.tsx and mount it in the Overview screen. |
| 85 | `ready_for_frontend_adapter` | `overview` | `frontend/src/components/warroom/PrismStatus.tsx` | Create frontend/src/components/unified/PrismstatusStatusCard.tsx and mount it in the Overview screen. |
| 85 | `ready_for_frontend_adapter` | `overview` | `frontend/src/components/warroom/SniperLeaderboard.tsx` | Create frontend/src/components/unified/SniperleaderboardStatusCard.tsx and mount it in the Overview screen. |
| 85 | `ready_for_frontend_adapter` | `overview` | `frontend/src/components/warroom/StrikeFeed.tsx` | Create frontend/src/components/unified/StrikefeedStatusCard.tsx and mount it in the Overview screen. |
| 85 | `ready_for_frontend_adapter` | `research` | `frontend/src/components/LiveValidationDashboard.tsx` | Create frontend/src/components/unified/LivevalidationdashboardStatusCard.tsx and mount it in the Research screen. |
| 85 | `ready_for_frontend_adapter` | `research` | `frontend/src/components/warroom/UnifiedBusStatus.tsx` | Create frontend/src/components/unified/UnifiedbusstatusStatusCard.tsx and mount it in the Research screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/components/DecisionVerificationPanel.tsx` | Create frontend/src/components/unified/DecisionverificationpanelStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/components/FTCPTimeline.tsx` | Create frontend/src/components/unified/FtcptimelineStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/components/GaryLeckeyFormation.tsx` | Create frontend/src/components/unified/GaryleckeyformationStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/components/GuardianDimensions.tsx` | Create frontend/src/components/unified/GuardiandimensionsStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/components/PrimeSentinelSeal.tsx` | Create frontend/src/components/unified/PrimesentinelsealStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/components/QuantumTelescopePanel.tsx` | Create frontend/src/components/unified/QuantumtelescopepanelStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/components/SandboxRunner.tsx` | Create frontend/src/components/unified/SandboxrunnerStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/components/SchumannResonanceMonitor.tsx` | Create frontend/src/components/unified/SchumannresonancemonitorStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/components/StargateVisualization.tsx` | Create frontend/src/components/unified/StargatevisualizationStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/aurisSymbolicTaxonomy.ts` | Create frontend/src/components/unified/AurissymbolictaxonomyStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/decisionAccuracyTracker.ts` | Create frontend/src/components/unified/DecisionaccuracytrackerStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/decisionExplainer.ts` | Create frontend/src/components/unified/DecisionexplainerStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/eckoushicCascade.ts` | Create frontend/src/components/unified/EckoushiccascadeStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/ftcpDetector.ts` | Create frontend/src/components/unified/FtcpdetectorStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/fullEcosystemConnector.ts` | Create frontend/src/components/unified/FullecosystemconnectorStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/hncImperialDetector.ts` | Create frontend/src/components/unified/HncimperialdetectorStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/lightPathTracer.ts` | Create frontend/src/components/unified/LightpathtracerStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/lighthouseConsensus.ts` | Create frontend/src/components/unified/LighthouseconsensusStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/prism.ts` | Create frontend/src/components/unified/PrismStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/quackersEvents.ts` | Create frontend/src/components/unified/QuackerseventsStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/rainbowBridge.ts` | Create frontend/src/components/unified/RainbowbridgeStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/stargateLattice.ts` | Create frontend/src/components/unified/StargatelatticeStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/temporalAnchor.ts` | Create frontend/src/components/unified/TemporalanchorStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/trailingStopManager.ts` | Create frontend/src/components/unified/TrailingstopmanagerStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `accounting` | `frontend/src/core/unityDetector.ts` | Create frontend/src/components/unified/UnitydetectorStatusCard.tsx and mount it in the Accounting screen. |
| 81 | `ready_for_frontend_adapter` | `saas_security` | `frontend/src/components/AppLayout.tsx` | Create frontend/src/components/unified/ApplayoutStatusCard.tsx and mount it in the SaaS Security screen. |
| 81 | `ready_for_frontend_adapter` | `saas_security` | `frontend/src/components/HNCScoreCard.tsx` | Create frontend/src/components/unified/HncscorecardStatusCard.tsx and mount it in the SaaS Security screen. |
| 81 | `ready_for_frontend_adapter` | `saas_security` | `frontend/src/components/HarmonicNexusAnalytics.tsx` | Create frontend/src/components/unified/HarmonicnexusanalyticsStatusCard.tsx and mount it in the SaaS Security screen. |
| 81 | `ready_for_frontend_adapter` | `saas_security` | `frontend/src/components/HarmonicNexusCore.tsx` | Create frontend/src/components/unified/HarmonicnexuscoreStatusCard.tsx and mount it in the SaaS Security screen. |
| 81 | `ready_for_frontend_adapter` | `saas_security` | `frontend/src/components/IdentityBinder.tsx` | Create frontend/src/components/unified/IdentitybinderStatusCard.tsx and mount it in the SaaS Security screen. |
| 81 | `ready_for_frontend_adapter` | `saas_security` | `frontend/src/components/LatencyHook.tsx` | Create frontend/src/components/unified/LatencyhookStatusCard.tsx and mount it in the SaaS Security screen. |
| 81 | `ready_for_frontend_adapter` | `saas_security` | `frontend/src/components/NexusWebSocket.tsx` | Create frontend/src/components/unified/NexuswebsocketStatusCard.tsx and mount it in the SaaS Security screen. |
| 81 | `ready_for_frontend_adapter` | `saas_security` | `frontend/src/components/TemporalUnityConsole.tsx` | Create frontend/src/components/unified/TemporalunityconsoleStatusCard.tsx and mount it in the SaaS Security screen. |
| 81 | `ready_for_frontend_adapter` | `saas_security` | `frontend/src/components/UnityNexusCore.tsx` | Create frontend/src/components/unified/UnitynexuscoreStatusCard.tsx and mount it in the SaaS Security screen. |
| 81 | `ready_for_frontend_adapter` | `saas_security` | `frontend/src/core/harmonicNexusCore.ts` | Create frontend/src/components/unified/HarmonicnexuscoreStatusCard.tsx and mount it in the SaaS Security screen. |
| 81 | `ready_for_frontend_adapter` | `saas_security` | `frontend/src/core/primelinesIdentity.ts` | Create frontend/src/components/unified/PrimelinesidentityStatusCard.tsx and mount it in the SaaS Security screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/BrainStatePanel.tsx` | Create frontend/src/components/unified/BrainstatepanelStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/ConsciousnessCoherenceTracker.tsx` | Create frontend/src/components/unified/ConsciousnesscoherencetrackerStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/ConsciousnessHistoryChart.tsx` | Create frontend/src/components/unified/ConsciousnesshistorychartStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/DimensionalDialler.tsx` | Create frontend/src/components/unified/DimensionaldiallerStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/HiveStatePanel.tsx` | Create frontend/src/components/unified/HivestatepanelStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/MandalaCodexProcessor.tsx` | Create frontend/src/components/unified/MandalacodexprocessorStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/OmegaFieldVisualization.tsx` | Create frontend/src/components/unified/OmegafieldvisualizationStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/PrimeLockActivation.tsx` | Create frontend/src/components/unified/PrimelockactivationStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/QueenHiveControl.tsx` | Create frontend/src/components/unified/QueenhivecontrolStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/SchumannLatticePatch.tsx` | Create frontend/src/components/unified/SchumannlatticepatchStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/SymbolicCompilerPanel.tsx` | Create frontend/src/components/unified/SymboliccompilerpanelStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/UnifiedTandemCore.tsx` | Create frontend/src/components/unified/UnifiedtandemcoreStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/cinema/CinematicHUD.tsx` | Create frontend/src/components/unified/CinematichudStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/cinema/CinematicObservatory.tsx` | Create frontend/src/components/unified/CinematicobservatoryStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/cinema/CinematicScene.tsx` | Create frontend/src/components/unified/CinematicsceneStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/cinema/CoherenceAurora.tsx` | Create frontend/src/components/unified/CoherenceauroraStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/cinema/HUDConsciousnessPanel.tsx` | Create frontend/src/components/unified/HudconsciousnesspanelStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/cinema/HUDQueenVoice.tsx` | Create frontend/src/components/unified/HudqueenvoiceStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/components/cinema/HiveConstellation.tsx` | Create frontend/src/components/unified/HiveconstellationStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/core/akashicMapperBridge.ts` | Create frontend/src/components/unified/AkashicmapperbridgeStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/core/autonomyHubBridge.ts` | Create frontend/src/components/unified/AutonomyhubbridgeStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/core/integralAQAL.ts` | Create frontend/src/components/unified/IntegralaqalStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/core/masterEquation.ts` | Create frontend/src/components/unified/MasterequationStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/core/nexusLiveFeedBridge.ts` | Create frontend/src/components/unified/NexuslivefeedbridgeStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/core/qgitaCoherence.ts` | Create frontend/src/components/unified/QgitacoherenceStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/core/queenHiveBrowser.ts` | Create frontend/src/components/unified/QueenhivebrowserStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/core/systemsIntegration.ts` | Create frontend/src/components/unified/SystemsintegrationStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/services/aureonService.ts` | Create frontend/src/components/unified/AureonserviceStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/services/ecosystemContextBuilder.ts` | Create frontend/src/components/unified/EcosystemcontextbuilderStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `self_improvement` | `frontend/src/services/lighthouseService.ts` | Create frontend/src/components/unified/LighthouseserviceStatusCard.tsx and mount it in the Self-Improvement screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/AkashicFrequencyVisualization.tsx` | Create frontend/src/components/unified/AkashicfrequencyvisualizationStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/AncientNumericalCodex.tsx` | Create frontend/src/components/unified/AncientnumericalcodexStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/AnomalyAlertsPanel.tsx` | Create frontend/src/components/unified/AnomalyalertspanelStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/AssetInventoryPanel.tsx` | Create frontend/src/components/unified/AssetinventorypanelStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/AuraNarrativeRenderer.tsx` | Create frontend/src/components/unified/AuranarrativerendererStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/AuraRingVisualizer.tsx` | Create frontend/src/components/unified/AuraringvisualizerStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/AureonChart.tsx` | Create frontend/src/components/unified/AureonchartStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/AureonReportCard.tsx` | Create frontend/src/components/unified/AureonreportcardStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/AutomatedHuntControl.tsx` | Create frontend/src/components/unified/AutomatedhuntcontrolStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/AutonomousTradingPanel.tsx` | Create frontend/src/components/unified/AutonomoustradingpanelStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/ChartContainer.tsx` | Create frontend/src/components/unified/ChartcontainerStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/CoherenceForecaster.tsx` | Create frontend/src/components/unified/CoherenceforecasterStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/CoherenceTrajectoryChart.tsx` | Create frontend/src/components/unified/CoherencetrajectorychartStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/CosmicPhaseIndicator.tsx` | Create frontend/src/components/unified/CosmicphaseindicatorStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/DrivingForcesChart.tsx` | Create frontend/src/components/unified/DrivingforceschartStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/EnhancedAngelOracleReader.tsx` | Create frontend/src/components/unified/EnhancedangeloraclereaderStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/FeatureCard.tsx` | Create frontend/src/components/unified/FeaturecardStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/Features.tsx` | Create frontend/src/components/unified/FeaturesStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/FloatingAIButton.tsx` | Create frontend/src/components/unified/FloatingaibuttonStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/FrequencyHarmonizationPanel.tsx` | Create frontend/src/components/unified/FrequencyharmonizationpanelStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/FullPortfolioDisplay.tsx` | Create frontend/src/components/unified/FullportfoliodisplayStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/GlyphTradingCorrelationChart.tsx` | Create frontend/src/components/unified/GlyphtradingcorrelationchartStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/HNCProbabilityMatrixPanel.tsx` | Create frontend/src/components/unified/HncprobabilitymatrixpanelStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/HarmonicKeyboard.tsx` | Create frontend/src/components/unified/HarmonickeyboardStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/HarmonicNexusPhaseField3D.tsx` | Create frontend/src/components/unified/Harmonicnexusphasefield3DStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/HarmonicTheoryFoundation.tsx` | Create frontend/src/components/unified/HarmonictheoryfoundationStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/Header.tsx` | Create frontend/src/components/unified/HeaderStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/HealthAlertSettings.tsx` | Create frontend/src/components/unified/HealthalertsettingsStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/Hero.tsx` | Create frontend/src/components/unified/HeroStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/HistoricalCoherenceChart.tsx` | Create frontend/src/components/unified/HistoricalcoherencechartStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/IgnitionButton.tsx` | Create frontend/src/components/unified/IgnitionbuttonStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/IntegralAQALVisualization.tsx` | Create frontend/src/components/unified/IntegralaqalvisualizationStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/KellyCriterionCalculator.tsx` | Create frontend/src/components/unified/KellycriterioncalculatorStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/LiveAnalysisStream.tsx` | Create frontend/src/components/unified/LiveanalysisstreamStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/LivePriceTicker.tsx` | Create frontend/src/components/unified/LivepricetickerStatusCard.tsx and mount it in the Trading screen. |
| 81 | `ready_for_frontend_adapter` | `trading` | `frontend/src/components/MarginSentimentPanel.tsx` | Create frontend/src/components/unified/MarginsentimentpanelStatusCard.tsx and mount it in the Trading screen. |
| ... | ... | ... | `385 more work orders in JSON` | ... |

## Safety

- `proposal_only`: `True`
- `legacy_systems_not_executed`: `True`
- `read_only_frontend_adapters_first`: `True`
- `no_live_trading`: `True`
- `no_official_filing`: `True`
- `no_payments`: `True`
- `secret_values_hidden`: `True`
- `apply_requires_explicit_handoff`: `True`

## Notes

- This queue is generated from the current SaaS inventory and is safe to show in the frontend.
- Work orders are migration intent, not proof that the legacy system has already been wired.
- Old systems stay available until their useful panels are replaced, embedded, or archived.
