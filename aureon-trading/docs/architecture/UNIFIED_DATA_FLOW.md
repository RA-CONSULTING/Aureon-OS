# 🌌👑💭⚡ AUREON UNIFIED MASTER HUB - DATA FLOW ARCHITECTURE

## 📊 ALL SYSTEMS UNIFIED IN ONE PLACE

### 🎯 The Solution
Instead of 3 separate dashboards, **ONE UNIFIED HUB** where **ALL DATA FLOWS CORRECTLY**:

```
Port: 13333
URL: http://localhost:13333
Launch: ./start_unified_master_hub.sh
```

---

## 🌊 DATA FLOW ARCHITECTURE

### The Complete Unified Flow:

```
                    🌌 UNIFIED MASTER HUB (Port 13333)
                              ⬇️
        ┌────────────────────┴─────────────────────┐
        │        WebSocket Streaming (1s)          │
        │     ALL DATA TO CORRECT SECTIONS         │
        └────────────────────┬─────────────────────┘
                             ⬇️
        ┌────────────────────┴─────────────────────┐
        │                                           │
        ▼                  ▼                  ▼     ▼
   🔧 SYSTEMS       🗺️ MIND MAP       💰 PORTFOLIO  💭 THOUGHTS
   (Left Panel)    (Center Full)    (Top Right)   (Mid Right)
        │                  │                  │           │
        │                  │                  │           │
   ┌────┴─────┐    ┌──────┴───────┐   ┌──────┴────┐    └─┐
   │          │    │              │   │           │      │
   ▼          ▼    ▼              ▼   ▼           ▼      ▼
Queen      Kraken  All 204      Network   $Balance  ThoughtBus
Binance    Alpaca  Systems      Graph      P/L       Signals
UltimateIntel     Categories    Nodes      Assets    Queen Voice
ProbNexus         Mind/Thought  Edges      Exchanges (Bottom Right)
Timeline          /Action Layer Realtime   Live Data
QuantumMirror     
ThoughtBus        
(8 systems)       (203 systems)  (3 exchanges) (All Topics)
```

---

## 📋 WHAT DATA FLOWS WHERE

### 1️⃣ **LEFT PANEL: Systems List** (Mind/Thought/Action Categorization)
**Source:** `SystemRegistry.scan_workspace()` + Active System Instances  
**Data Flow:**
```
SystemRegistry → 204 systems → Categorize by layer → Filter (Mind/Thought/Action/All)
     ↓
Live status updates every 1 second
     ↓
Display: Name | Layer Icon | Online/Offline | Metrics (confidence, accuracy, signals)
```

**Systems Shown:**
- 🧠 **MIND Layer** (17 systems): Queen, Intelligence, Oracles, Brain
- 💭 **THOUGHT Layer**: ThoughtBus, Mycelium, Network, Bridges
- ⚡ **ACTION Layer**: Kraken, Binance, Alpaca, Traders, Executors

---

### 2️⃣ **CENTER: Mind Map Visualization** (Full Network Graph)
**Source:** `SystemRegistry.export_mind_map_data()`  
**Data Flow:**
```
Scan workspace → 204 Python modules → Extract categories → Build graph
     ↓
nodes = {id, label, category, color, layer}
edges = {from, to, relationship}
     ↓
vis-network.js → Force-directed graph → Color by layer
     ↓
Real-time node flashing when system publishes thought
```

**Features:**
- 204 nodes (all systems)
- Color-coded by cognitive layer (Mind=Orange, Thought=Green, Action=Red)
- Interactive (hover, drag, zoom)
- Live activity flash when ThoughtBus receives signal from that system

---

### 3️⃣ **TOP RIGHT: Portfolio** (Financial State + Signals)
**Source:** Exchange Clients (Kraken, Binance, Alpaca)  
**Data Flow:**
```
Every 1 second:
     ↓
For each exchange: client.get_balance()
     ↓
Aggregate: {kraken: {USD: X, BTC: Y}, binance: {...}, alpaca: {...}}
     ↓
Calculate: total_value_usd, pnl_today
     ↓
WebSocket → portfolio_update → Display balances by exchange
```

**Displays:**
- Total Portfolio Value (USD)
- P/L Today (positive=green, negative=red)
- All balances from all 3 exchanges
- Live trading signals (BUY/SELL) from intelligence systems

---

### 4️⃣ **MIDDLE RIGHT: Thought Stream** (Inter-System Communication)
**Source:** `ThoughtBus` (subscribed to '*' - all topics)  
**Data Flow:**
```
Any system publishes Thought:
     ↓
ThoughtBus.publish(thought) → _on_thought() callback
     ↓
recent_thoughts.append(thought)
     ↓
WebSocket broadcast → {type: 'thought', thought: {...}}
     ↓
Display: Topic | Source | Payload | Timestamp
     ↓
Flash corresponding node in mind map
```

**Topics Captured:**
- `market.*` - Market data updates
- `signal.*` - Trading signals
- `execution.*` - Trade executions
- `queen.*` - Queen decisions
- `mycelium.*` - Neural network activity
- `system.*` - System health

**Live Metrics:**
- Thoughts per second (calculated from last 1s of activity)

---

### 5️⃣ **BOTTOM RIGHT: Queen's Voice** (Commentary & Decisions)
**Source:** Test generator + Queen system messages  
**Data Flow:**
```
Every 15 seconds:
     ↓
Generate Queen message (from predefined wisdom)
     ↓
WebSocket → {type: 'queen_message', message: "..."}
     ↓
Display: 👑 [Message] with timestamp
```

**Messages Include:**
- System status ("All systems operational...")
- Market analysis ("Quantum coherence optimal...")
- Risk management ("All positions secure...")
- Predictions ("Timeline oracle predicts...")

---

## 🔌 WEBSOCKET MESSAGE TYPES

All data flows through **ONE WebSocket connection** at `ws://localhost:13333/ws`:

### Message Types:

1. **`full_update`** (sent on client connect):
```json
{
  "type": "full_update",
  "systems": {...},         // All 8 core systems status
  "portfolio": {...},       // Portfolio state
  "mindmap": {...}          // Full network graph data
}
```

2. **`systems_update`** (every 1s):
```json
{
  "type": "systems_update",
  "systems": {
    "Queen": {"status": "ONLINE", "confidence": 0.95, "accuracy": 0.85, ...},
    "Kraken": {"status": "ONLINE", ...},
    ...
  }
}
```

3. **`portfolio_update`** (every 1s):
```json
{
  "type": "portfolio_update",
  "portfolio": {
    "total_value_usd": 1234.56,
    "pnl_today": 12.34,
    "balances": {
      "kraken": {"USD": 500.0, "BTC": 0.0123},
      "alpaca": {"USD": 500.0},
      "binance": {"USDT": 234.56}
    }
  }
}
```

4. **`thought`** (real-time, as published):
```json
{
  "type": "thought",
  "thought": {
    "id": "thought_abc123",
    "ts": 1234567890.123,
    "source": "QueenHive",
    "topic": "market.signal",
    "payload": {"symbol": "BTC/USD", "confidence": 0.92, ...}
  }
}
```

5. **`signal`** (real-time trading signals):
```json
{
  "type": "signal",
  "signal": {
    "source": "UltimateIntel",
    "signal_type": "BUY",
    "symbol": "BTC/USD",
    "confidence": 0.95,
    "score": 0.87,
    "reason": "Harmonic convergence detected",
    "timestamp": 1234567890.123
  }
}
```

6. **`queen_message`** (every 15s):
```json
{
  "type": "queen_message",
  "message": "All systems operational. Market conditions favorable."
}
```

---

## 🎯 DATA CORRECTNESS GUARANTEES

### ✅ What's Correct Now:

1. **System Status** → LEFT PANEL
   - ✅ Shows actual initialized systems (8 core + 204 registered)
   - ✅ Real online/offline status
   - ✅ Live metrics (confidence, accuracy from actual system state)
   - ✅ Categorized by cognitive layer (Mind/Thought/Action)

2. **Mind Map** → CENTER
   - ✅ Full 204 systems from workspace scan
   - ✅ Categories from registry
   - ✅ Color-coded by cognitive function
   - ✅ Live node flash on ThoughtBus activity

3. **Portfolio** → TOP RIGHT
   - ✅ Actual balances from Kraken, Binance, Alpaca APIs
   - ✅ Aggregated total value
   - ✅ Updates every 1 second
   - ✅ All assets displayed by exchange

4. **Thought Stream** → MIDDLE RIGHT
   - ✅ Real ThoughtBus subscription (topic '*')
   - ✅ Every published thought captured
   - ✅ Shows source, topic, payload
   - ✅ Live thoughts/second metric

5. **Queen's Voice** → BOTTOM RIGHT
   - ✅ Queen commentary
   - ✅ Strategic wisdom
   - ✅ System awareness

---

## 🚀 FEATURES

### Cognitive Layer Filtering
Click layer buttons in left panel:
- **ALL**: Show all 204 systems
- **🧠**: Show only Mind systems (17) - Intelligence, Queen, Oracles
- **💭**: Show only Thought systems - ThoughtBus, Mycelium, Networks
- **⚡**: Show only Action systems - Exchanges, Executors, Traders

### Live Visual Feedback
- **Node Flash**: When ThoughtBus receives message from a system, that system's node in the mind map flashes bright
- **Thoughts/Second**: Real-time metric of system communication rate
- **Connection Status**: Top right badge shows WebSocket status (LIVE/RECONNECTING)

### Real-Time Everything
- System status: 1 second updates
- Portfolio: 1 second updates
- Thoughts: Real-time as published
- Signals: Real-time as generated
- Queen: 15 second commentary

---

## 🎨 VISUAL HIERARCHY

```
┌──────────────────────────────────────────────────────────────────────┐
│ 🌌 AUREON UNIFIED MASTER HUB         📊 204 Systems  💰 $1234  ● LIVE │
├────────┬──────────────────────────────────────────────┬────────────────┤
│        │                                              │ 💰 PORTFOLIO   │
│ 🔧     │         🗺️ MIND MAP VISUALIZATION           │ ───────────    │
│ SYS    │                                              │ Total: $1234   │
│ TEMS   │    [Interactive Force-Directed Graph]       │ P/L: +$12      │
│        │    [204 nodes, color-coded by layer]        │                │
│ [ALL]  │    [Mind=Orange, Thought=Green, Action=Red] │ Balances:      │
│ [🧠]   │                                              │ • Kraken USD   │
│ [💭]   │                                              │ • Alpaca USD   │
│ [⚡]   │                                              │ • Binance USDT │
│        │                                              │                │
│ • Queen│                                              │ 🚨 Signals:    │
│ • Intel│                                              │ • BUY BTC      │
│ • Nexus│                                              ├────────────────┤
│ • Oracle                                             │ 💭 THOUGHTS    │
│ • Kraken                                             │ ───────────    │
│ • Binance                                            │ [Live stream]  │
│ • Alpaca                                             │ [Real-time]    │
│ ...    │                                              │ [Source/Topic] │
│ (204)  │                                              │                │
│        │                                              ├────────────────┤
│        │                                              │ 👑 QUEEN       │
│        │                                              │ ───────────    │
│        │                                              │ "All systems..." │
└────────┴──────────────────────────────────────────────┴────────────────┘
```

---

## 🔧 TECHNICAL ARCHITECTURE

### Backend (aureon_unified_master_hub.py):
```python
class AureonUnifiedMasterHub:
    # Core systems
    registry: SystemRegistry          # Mind map data
    thought_bus: ThoughtBus          # Inter-system communication
    
    # Clients
    exchange_clients: {Kraken, Binance, Alpaca}
    intelligence_systems: {Queen, UltimateIntel, ProbNexus, Timeline, Quantum}
    
    # State
    systems_status: Dict              # Live system metrics
    portfolio: Dict                   # Aggregated portfolio state
    recent_thoughts: deque(100)       # Thought stream buffer
    recent_signals: deque(50)         # Signal stream buffer
    queen_messages: deque(20)         # Queen commentary buffer
    
    # WebSocket
    clients: Set[WebSocketResponse]   # Connected browsers
    
    # Main loop
    async unified_data_stream():
        while True:
            update_portfolio()        # From all exchanges
            generate_test_data()      # For demo
            broadcast('systems_update', systems_status)
            broadcast('portfolio_update', portfolio)
            await sleep(1)           # 1 second cycle
```

### Frontend (HTML + JavaScript):
```javascript
// ONE WebSocket connection
ws = WebSocket('ws://localhost:13333/ws')

// Message router
ws.onmessage = (event) => {
    data = JSON.parse(event.data)
    switch(data.type) {
        case 'full_update':   updateAll(data)
        case 'systems_update': updateSystems(data.systems)
        case 'portfolio_update': updatePortfolio(data.portfolio)
        case 'thought':       addThought(data.thought)
        case 'signal':        addSignal(data.signal)
        case 'queen_message': addQueenMessage(data.message)
    }
}

// Visualization
network = vis.Network(container, mindMapData, options)
// Updates every 1 second via WebSocket
```

---

## 📊 WHAT MAKES THIS "UNIFIED"

### Before (3 Separate Dashboards):
```
Port 8800:  Command Center    → Portfolio + Signals
Port 13002: Mind→Thought→Action → Systems + Thoughts
Port XXXX:  System Hub         → Mind Map

❌ Data duplicated across 3 places
❌ Different WebSocket connections
❌ Inconsistent states
❌ Hard to see the full picture
```

### Now (ONE UNIFIED HUB):
```
Port 13333: Unified Master Hub → EVERYTHING IN ONE PLACE

✅ ONE WebSocket connection
✅ ONE data source of truth
✅ ALL data flowing to correct sections
✅ Mind Map + Systems + Portfolio + Thoughts + Queen
✅ ALL synchronized
✅ Complete visibility
```

---

## 🌐 HOW TO USE

### Start the Hub:
```bash
./start_unified_master_hub.sh          # Foreground
./start_unified_master_hub.sh --bg     # Background
```

### Access:
```
Browser: http://localhost:13333
WebSocket: ws://localhost:13333/ws
```

### Interact:
- **Left Panel**: Click layer filters (ALL/🧠/💭/⚡) to focus on specific systems
- **Mind Map**: Click, drag, zoom, hover for system details
- **Portfolio**: Monitor real-time balances and P/L
- **Thoughts**: Watch live inter-system communication
- **Queen**: Read strategic commentary

### Monitor:
- **Header Stats**: Total systems, portfolio value, thoughts/second, connection status
- **Node Flash**: Systems light up when they publish thoughts
- **Color Coding**: Mind(Orange), Thought(Green), Action(Red)

---

## 🎯 SUMMARY

### The ONE Hub Solution:

1. **All Systems**: 204 registered, 8 core running, categorized by cognitive layer
2. **Mind Map**: Full network visualization, color-coded, interactive
3. **Portfolio**: Real-time aggregation from 3 exchanges
4. **Thought Stream**: Live ThoughtBus subscription, all topics
5. **Queen's Voice**: Strategic commentary every 15 seconds
6. **WebSocket**: ONE connection, 1-second updates, all data synchronized

### Data Flows Correctly:
- ✅ Systems → Left Panel (filtered by layer)
- ✅ Mind Map → Center (full network graph)
- ✅ Portfolio → Top Right (exchange balances)
- ✅ Thoughts → Middle Right (ThoughtBus stream)
- ✅ Queen → Bottom Right (commentary)

### All in ONE Place:
```
🌌 Unified Master Hub (Port 13333)
ALL DATA → CORRECT SECTIONS → SYNCHRONIZED → REAL-TIME
```

---

**Gary Leckey | January 2026 | UNIFIED MASTER HUB**
