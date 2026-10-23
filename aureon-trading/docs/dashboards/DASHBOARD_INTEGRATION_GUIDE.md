#!/usr/bin/env python3
"""
🔧 AUREON PRO DASHBOARD - INTEGRATION GUIDE
═══════════════════════════════════════════════════════════════════════════

STEP-BY-STEP GUIDE TO ADD NEW INTELLIGENCE PANELS TO THE DASHBOARD

This guide shows exactly how to integrate the 7 new intelligence panels into
aureon_pro_dashboard.py without breaking existing functionality.

NEW FEATURES ADDED:
- 🦈 Predator Detection Panel
- 🇮🇪🎯 IRA Sniper Scope Panel
- 🔮 Quantum Systems Status Panel
- ⏳ Timeline Oracle Panel
- 📊 Intelligence Health Monitor
- 🐋 Whale Tracker Panel
- 🥷 Stealth Execution Panel

REAL DATA ONLY - All panels read from state files and live intelligence systems.
"""

INTEGRATION_STEPS = """
═══════════════════════════════════════════════════════════════════════════
STEP 1: IMPORT THE INTELLIGENCE HUB
═══════════════════════════════════════════════════════════════════════════

At the top of aureon_pro_dashboard.py, add:

```python
# Import intelligence hub for advanced panels
try:
    from dashboard_intelligence_enhancements import (
        IntelligenceHub,
        INTELLIGENCE_PANELS_HTML,
        INTELLIGENCE_PANELS_CSS,
        INTELLIGENCE_PANELS_JS
    )
    INTELLIGENCE_HUB_AVAILABLE = True
except ImportError:
    INTELLIGENCE_HUB_AVAILABLE = False
    logger.warning("Intelligence Hub not available")
```

═══════════════════════════════════════════════════════════════════════════
STEP 2: INITIALIZE INTELLIGENCE HUB IN __init__
═══════════════════════════════════════════════════════════════════════════

In AureonProDashboard.__init__(), add:

```python
# Initialize intelligence hub
self.intelligence_hub = None
if INTELLIGENCE_HUB_AVAILABLE:
    self.intelligence_hub = IntelligenceHub()
    self.logger.info("✅ Intelligence Hub initialized")
```

═══════════════════════════════════════════════════════════════════════════
STEP 3: ADD API ROUTES
═══════════════════════════════════════════════════════════════════════════

In setup_routes(), add these new endpoints:

```python
self.app.router.add_get('/api/intelligence', self.handle_intelligence)
self.app.router.add_get('/api/predator', self.handle_predator)
self.app.router.add_get('/api/sniper', self.handle_sniper)
self.app.router.add_get('/api/quantum', self.handle_quantum)
self.app.router.add_get('/api/timeline', self.handle_timeline)
self.app.router.add_get('/api/intelligence-health', self.handle_intelligence_health)
```

═══════════════════════════════════════════════════════════════════════════
STEP 4: ADD API HANDLERS
═══════════════════════════════════════════════════════════════════════════

Add these new handler methods to AureonProDashboard class:

```python
async def handle_intelligence(self, request):
    \"\"\"Return all intelligence data unified.\"\"\"
    if self.intelligence_hub:
        data = await self.intelligence_hub.get_all_intelligence()
        return web.json_response(data)
    return web.json_response({'error': 'Intelligence Hub not available'}, status=503)

async def handle_predator(self, request):
    \"\"\"Return predator detection data.\"\"\"
    if self.intelligence_hub:
        data = await self.intelligence_hub.refresh_predator_data()
        return web.json_response(data)
    return web.json_response({'error': 'Predator detection not available'}, status=503)

async def handle_sniper(self, request):
    \"\"\"Return IRA sniper scope data.\"\"\"
    if self.intelligence_hub:
        data = await self.intelligence_hub.refresh_sniper_data()
        return web.json_response(data)
    return web.json_response({'error': 'Sniper scope not available'}, status=503)

async def handle_quantum(self, request):
    \"\"\"Return quantum systems status.\"\"\"
    if self.intelligence_hub:
        data = await self.intelligence_hub.refresh_quantum_data()
        return web.json_response(data)
    return web.json_response({'error': 'Quantum systems not available'}, status=503)

async def handle_timeline(self, request):
    \"\"\"Return timeline oracle data.\"\"\"
    if self.intelligence_hub:
        data = await self.intelligence_hub.refresh_timeline_data()
        return web.json_response(data)
    return web.json_response({'error': 'Timeline oracle not available'}, status=503)

async def handle_intelligence_health(self, request):
    \"\"\"Return intelligence health status.\"\"\"
    if self.intelligence_hub:
        data = await self.intelligence_hub.refresh_intelligence_health()
        return web.json_response(data)
    return web.json_response({'error': 'Intelligence health not available'}, status=503)
```

═══════════════════════════════════════════════════════════════════════════
STEP 5: ADD BACKGROUND REFRESH LOOP
═══════════════════════════════════════════════════════════════════════════

Add this new background task:

```python
async def intelligence_refresh_loop(self):
    \"\"\"Refresh all intelligence data periodically and broadcast to clients.\"\"\"
    await asyncio.sleep(5)  # Wait for init
    
    while True:
        try:
            if self.intelligence_hub:
                # Refresh all intelligence data
                intelligence_data = await self.intelligence_hub.get_all_intelligence()
                
                # Broadcast to all connected clients
                await self.broadcast({
                    'type': 'intelligence_update',
                    'data': intelligence_data
                })
                
                self.logger.info(f"📊 Intelligence: {intelligence_data['health']['online']}/{intelligence_data['health']['total_systems']} systems online")
        except Exception as e:
            self.logger.error(f"❌ Intelligence refresh error: {e}")
        
        await asyncio.sleep(10)  # Refresh every 10 seconds
```

And start it in async def start():

```python
if self.intelligence_hub:
    asyncio.create_task(self.intelligence_refresh_loop())
```

═══════════════════════════════════════════════════════════════════════════
STEP 6: INJECT HTML PANELS INTO DASHBOARD
═══════════════════════════════════════════════════════════════════════════

In the PRO_DASHBOARD_HTML variable, add the intelligence panels.

Find the section with the 3-column grid layout and add a new row:

```html
<!-- INTELLIGENCE PANELS ROW (NEW) -->
<div class="intelligence-row">
    {INTELLIGENCE_PANELS_HTML}
</div>
```

Then inject it when rendering:

```python
async def handle_index(self, request):
    html = PRO_DASHBOARD_HTML
    
    # Inject intelligence panels if available
    if INTELLIGENCE_HUB_AVAILABLE:
        html = html.replace('{INTELLIGENCE_PANELS_HTML}', INTELLIGENCE_PANELS_HTML)
        html = html.replace('{INTELLIGENCE_PANELS_CSS}', INTELLIGENCE_PANELS_CSS)
        html = html.replace('{INTELLIGENCE_PANELS_JS}', INTELLIGENCE_PANELS_JS)
    else:
        html = html.replace('{INTELLIGENCE_PANELS_HTML}', '<!-- Intelligence panels not available -->')
        html = html.replace('{INTELLIGENCE_PANELS_CSS}', '')
        html = html.replace('{INTELLIGENCE_PANELS_JS}', '')
    
    return web.Response(text=html, content_type='text/html')
```

═══════════════════════════════════════════════════════════════════════════
STEP 7: UPDATE CSS GRID LAYOUT
═══════════════════════════════════════════════════════════════════════════

Modify the .main-container CSS to add a new row for intelligence panels:

```css
.main-container {
    display: grid;
    grid-template-columns: 320px 1fr 380px;
    grid-template-rows: auto 1fr auto;  /* Added auto for intelligence row */
    gap: 1px;
    background: var(--border-color);
    height: calc(100vh - 50px);
}

/* Intelligence panels row */
.intelligence-row {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1px;
    background: var(--border-color);
}
```

═══════════════════════════════════════════════════════════════════════════
STEP 8: ADD CSS STYLES
═══════════════════════════════════════════════════════════════════════════

In the <style> section of PRO_DASHBOARD_HTML, add:

```css
{INTELLIGENCE_PANELS_CSS}
```

═══════════════════════════════════════════════════════════════════════════
STEP 9: ADD JAVASCRIPT HANDLERS
═══════════════════════════════════════════════════════════════════════════

In the <script> section of PRO_DASHBOARD_HTML, add:

```javascript
{INTELLIGENCE_PANELS_JS}
```

═══════════════════════════════════════════════════════════════════════════
STEP 10: TEST THE INTEGRATION
═══════════════════════════════════════════════════════════════════════════

1. Run the dashboard:
   ```bash
   python aureon_pro_dashboard.py
   ```

2. Open browser to http://localhost:14000

3. Verify all panels are visible:
   - 🦈 Predator Detection panel shows threats
   - 🇮🇪🎯 IRA Sniper Scope shows active targets
   - 🔮 Quantum Systems shows 10 systems status
   - ⏳ Timeline Oracle shows pending validations
   - 📊 Intelligence Health shows 30+ systems
   
4. Check WebSocket console for intelligence_update messages

5. Verify all data is REAL (reads from state files):
   - active_position.json
   - 7day_pending_validations.json
   - 7day_anchored_timelines.json
   - quantum_systems_state.json
   - etc.

═══════════════════════════════════════════════════════════════════════════
STEP 11: DEPLOY TO DIGITALOCEAN
═══════════════════════════════════════════════════════════════════════════

1. Commit changes:
   ```bash
   git add dashboard_intelligence_enhancements.py
   git add aureon_pro_dashboard.py
   git commit -m "Add intelligence panels to Aureon Pro Dashboard"
   git push origin main
   ```

2. DigitalOcean App Platform will auto-deploy

3. Verify at https://your-app.ondigitalocean.app

═══════════════════════════════════════════════════════════════════════════
TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════

Issue: Intelligence panels not showing
Fix: Check INTELLIGENCE_HUB_AVAILABLE is True in logs

Issue: "Intelligence Hub not available" error
Fix: Ensure dashboard_intelligence_enhancements.py is in same directory

Issue: Empty/zero data in panels
Fix: Check state files exist (7day_*.json, active_position.json, etc.)

Issue: Systems showing offline
Fix: Normal - only systems actually imported by orca_complete_kill_cycle will show online

Issue: WebSocket not updating panels
Fix: Check browser console for 'intelligence_update' messages

═══════════════════════════════════════════════════════════════════════════
ARCHITECTURE NOTES
═══════════════════════════════════════════════════════════════════════════

DATA FLOW:
1. IntelligenceHub reads state files (REAL DATA)
2. Background loop refreshes every 10 seconds
3. Data broadcast via WebSocket to all clients
4. JavaScript updates DOM elements in real-time

STATE FILES (REAL DATA SOURCES):
- active_position.json - Current open position
- 7day_pending_validations.json - Pending 4th decisions
- 7day_anchored_timelines.json - Confirmed timelines
- 7day_current_plan.json - Active 7-day plan
- quantum_systems_state.json - Quantum systems status
- orca_kill_stats.json - IRA sniper scope stats
- whale_tracker_state.json - Whale detection data
- stealth_execution_state.json - Stealth metrics

NO SIMULATIONS - All data comes from real trading systems!

═══════════════════════════════════════════════════════════════════════════
WHAT YOU'LL SEE
═══════════════════════════════════════════════════════════════════════════

After integration, the dashboard will show:

TOP ROW (existing):
- Queen's Voice Panel (full width)

MIDDLE ROW (existing):
- Portfolio Panel (left)
- Chart Panel (center)
- Activity Feed (right)

BOTTOM ROW (NEW):
- 🦈 Predator Detection
- 🇮🇪🎯 IRA Sniper Scope
- 🔮 Quantum Systems
- ⏳ Timeline Oracle
- 📊 Intelligence Health
- 🐋 Whale Tracker
- 🥷 Stealth Execution

All panels update in real-time via WebSocket!
All data is REAL from state files and live intelligence systems!

═══════════════════════════════════════════════════════════════════════════
"""

if __name__ == '__main__':
    print(__doc__)
    print(INTEGRATION_STEPS)
