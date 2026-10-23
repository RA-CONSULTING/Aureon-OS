"""
AEDS PHI-BRIDGE — Distributed Node Communication Protocol
==========================================================
Inter-node messaging for the mycelial AEDS network.

Based on Aureon's mycelial architecture:
- Phi-bridge: golden-ratio scaled message propagation
- Quantum voting: 3-council alignment collapses wave function to ACTION
- Threat broadcast: one node's observation becomes all nodes' intelligence

The phi-bridge is NOT a physical EM transmitter. It is a computational
protocol for synchronizing observation state across distributed nodes.
"""

import json
import time
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Callable, Set
from enum import Enum
import logging

# Import AEDS core from this directory. The sibling module ships with the bridge.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aureon_environmental_defense_system import (
    EnvironmentalThreat, ThreatLevel, ActionType, HNCFramework
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# SACRED CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

PHI = 1.618033988749895
PHI_SQUARED = 2.618033988749895

# ──────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────────────────────────────────────

class CouncilVote(Enum):
    EVIDENCE = "evidence"
    ETHICS = "ethics"
    STRATEGY = "strategy"

class QuantumState(Enum):
    SUPERPOSITION = "superposition"    # No councils aligned yet
    PARTIAL = "partial"               # 1-2 councils aligned
    COLLAPSED = "collapsed"           # All 3 aligned — ACTION triggered

@dataclass
class PhiMessage:
    """A message passed through the phi-bridge between nodes."""
    msg_id: str
    sender_node: str
    timestamp: str
    msg_type: str  # "threat_alert", "council_vote", "action_broadcast", "coherence_ping"
    payload: Dict
    phi_priority: float  # Priority scaled by phi — higher = faster propagation
    hop_count: int = 0
    max_hops: int = 7  # Fibonacci number — natural limit
    signature: str = ""  # Hash of payload + timestamp
    
    def __post_init__(self):
        if not self.signature:
            self.signature = self._compute_signature()
    
    def _compute_signature(self) -> str:
        """Compute integrity signature."""
        data = f"{self.sender_node}:{self.timestamp}:{json.dumps(self.payload, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def to_dict(self):
        return asdict(self)
    
    def propagate(self) -> 'PhiMessage':
        """Create next-hop message with phi-scaled priority."""
        return PhiMessage(
            msg_id=self.msg_id,
            sender_node=self.sender_node,
            timestamp=datetime.now(timezone.utc).isoformat(),
            msg_type=self.msg_type,
            payload=self.payload,
            phi_priority=self.phi_priority * PHI,  # Amplify on each hop
            hop_count=self.hop_count + 1,
            max_hops=self.max_hops,
            signature=self.signature
        )

@dataclass
class CouncilAlignment:
    """Tracks alignment of the 3 governance councils."""
    evidence_council: Optional[str] = None  # "approve", "reject", "abstain"
    ethics_council: Optional[str] = None
    strategy_council: Optional[str] = None
    evidence_timestamp: Optional[str] = None
    ethics_timestamp: Optional[str] = None
    strategy_timestamp: Optional[str] = None
    
    def alignment_count(self) -> int:
        return sum(1 for v in [self.evidence_council, self.ethics_council, self.strategy_council] if v == "approve")
    
    def quantum_state(self) -> QuantumState:
        count = self.alignment_count()
        if count >= 3:
            return QuantumState.COLLAPSED
        elif count >= 1:
            return QuantumState.PARTIAL
        return QuantumState.SUPERPOSITION
    
    def is_action_approved(self) -> bool:
        return self.quantum_state() == QuantumState.COLLAPSED

# ──────────────────────────────────────────────────────────────────────────────
# PHI-BRIDGE ENGINE
# ──────────────────────────────────────────────────────────────────────────────

class PhiBridgeEngine:
    """
    Distributed node communication via phi-scaled message propagation.
    
    Based on Aureon's mycelial architecture:
    - Messages propagate with phi-scaled priority amplification
    - Max 7 hops (Fibonacci limit)
    - Each node rebroadcasts to all known peers
    - Threat alerts get highest priority (phi^3)
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.peers: Set[str] = set()  # Known peer node IDs
        self.message_log: List[PhiMessage] = []
        self.seen_msg_ids: Set[str] = set()  # Deduplication
        self.handlers: Dict[str, Callable] = {}
        
    def register_peer(self, peer_id: str):
        """Register a peer node in the mycelial network."""
        self.peers.add(peer_id)
        logger.info(f"[PHI-BRIDGE] {self.node_id}: Peer registered: {peer_id}")
    
    def register_handler(self, msg_type: str, handler: Callable[[PhiMessage], None]):
        """Register a handler for a message type."""
        self.handlers[msg_type] = handler
    
    def send_message(self, msg_type: str, payload: Dict, priority_base: float = 1.0) -> PhiMessage:
        """
        Send a message through the phi-bridge.
        Priority is phi-scaled based on message type.
        """
        # Phi-scaled priority by message type
        priority_multipliers = {
            "threat_alert": PHI_SQUARED,      # Highest — immediate propagation
            "action_broadcast": PHI,           # High — action needs to spread
            "council_vote": PHI,              # High — governance decision
            "coherence_ping": 1.0,            # Normal — keepalive
        }
        
        priority = priority_base * priority_multipliers.get(msg_type, 1.0)
        
        msg = PhiMessage(
            msg_id=hashlib.sha256(f"{self.node_id}:{time.time()}".encode()).hexdigest()[:16],
            sender_node=self.node_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            msg_type=msg_type,
            payload=payload,
            phi_priority=priority
        )
        
        self._process_message(msg)
        return msg
    
    def receive_message(self, msg: PhiMessage) -> bool:
        """
        Receive a message from another node.
        Returns True if processed, False if dropped (duplicate or max hops).
        """
        # Deduplication
        if msg.msg_id in self.seen_msg_ids:
            return False
        
        # Max hops check
        if msg.hop_count >= msg.max_hops:
            logger.debug(f"[PHI-BRIDGE] {self.node_id}: Max hops reached for {msg.msg_id}")
            return False
        
        self.seen_msg_ids.add(msg.msg_id)
        self._process_message(msg)
        return True
    
    def _process_message(self, msg: PhiMessage):
        """Process and potentially rebroadcast a message."""
        self.message_log.append(msg)
        
        # Log
        logger.info(f"[PHI-BRIDGE] {self.node_id}: Received {msg.msg_type} from {msg.sender_node} "
                   f"(priority={msg.phi_priority:.3f}, hop={msg.hop_count})")
        
        # Call handler if registered
        handler = self.handlers.get(msg.msg_type)
        if handler:
            try:
                handler(msg)
            except Exception as e:
                logger.error(f"[PHI-BRIDGE] Handler error: {e}")
        
        # Rebroadcast to peers (mycelial replication)
        self._rebroadcast(msg)
    
    def _rebroadcast(self, msg: PhiMessage):
        """Rebroadcast to all peers with incremented hop and phi-scaled priority."""
        if msg.hop_count >= msg.max_hops:
            return
        
        propagated = msg.propagate()
        
        for peer in self.peers:
            # In a real distributed system, this would send over network
            # For now, we log the would-be broadcast
            logger.info(f"[PHI-BRIDGE] {self.node_id} -> {peer}: Propagating {msg.msg_type} "
                       f"(new_priority={propagated.phi_priority:.3f}, hop={propagated.hop_count})")

# ──────────────────────────────────────────────────────────────────────────────
# QUANTUM VOTING — 3-Council Governance
# ──────────────────────────────────────────────────────────────────────────────

class QuantumVotingEngine:
    """
    3-council quantum voting system.
    
    When all 3 councils (Evidence, Ethics, Strategy) align to APPROVE,
    the wave function COLLAPSES and action is triggered.
    
    Based on Aureon's Queen veto logic:
    - Pass 1: Pattern recognition (Evidence)
    - Pass 2: Harmonic validation (Ethics)
    - Pass 3: Coherence validation (Strategy)
    - Pass 4: Conscience veto (all 3 must align)
    """
    
    def __init__(self):
        self.pending_votes: Dict[str, CouncilAlignment] = {}  # action_id -> alignment
        self.decision_log: List[Dict] = []
    
    def submit_vote(self, action_id: str, council: CouncilVote, verdict: str) -> Dict:
        """
        Submit a vote from a council.
        
        Args:
            action_id: Unique ID for the proposed action
            council: Which council is voting
            verdict: "approve", "reject", or "abstain"
        
        Returns:
            Dict with current quantum state and whether action is approved
        """
        if action_id not in self.pending_votes:
            self.pending_votes[action_id] = CouncilAlignment()
        
        alignment = self.pending_votes[action_id]
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if council == CouncilVote.EVIDENCE:
            alignment.evidence_council = verdict
            alignment.evidence_timestamp = timestamp
        elif council == CouncilVote.ETHICS:
            alignment.ethics_council = verdict
            alignment.ethics_timestamp = timestamp
        elif council == CouncilVote.STRATEGY:
            alignment.strategy_council = verdict
            alignment.strategy_timestamp = timestamp
        
        # Check quantum state
        state = alignment.quantum_state()
        approved = alignment.is_action_approved()
        
        # Log
        self.decision_log.append({
            "action_id": action_id,
            "council": council.value,
            "verdict": verdict,
            "timestamp": timestamp,
            "alignment_count": alignment.alignment_count(),
            "quantum_state": state.value,
            "action_approved": approved
        })
        
        # If any council rejects, the wave function collapses to REJECT
        if verdict == "reject":
            state = QuantumState.COLLAPSED
            approved = False
            logger.info(f"[QUANTUM-VOTE] {action_id}: REJECTED by {council.value} council")
        elif approved:
            logger.info(f"[QUANTUM-VOTE] {action_id}: WAVE FUNCTION COLLAPSED — ALL 3 COUNCILS ALIGNED — ACTION APPROVED")
        else:
            logger.info(f"[QUANTUM-VOTE] {action_id}: State={state.value}, aligned={alignment.alignment_count()}/3")
        
        return {
            "action_id": action_id,
            "quantum_state": state.value,
            "alignment_count": alignment.alignment_count(),
            "action_approved": approved,
            "evidence": alignment.evidence_council,
            "ethics": alignment.ethics_council,
            "strategy": alignment.strategy_council
        }
    
    def get_alignment(self, action_id: str) -> Optional[CouncilAlignment]:
        return self.pending_votes.get(action_id)

# ──────────────────────────────────────────────────────────────────────────────
# AEDS NODE — Integrated Phi-Bridge + Quantum Voting
# ──────────────────────────────────────────────────────────────────────────────

class AEDSMycelialNode:
    """
    A single node in the AEDS mycelial network.
    Combines threat detection, phi-bridge communication, and quantum voting.
    """
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.phi_bridge = PhiBridgeEngine(node_id)
        self.quantum_vote = QuantumVotingEngine()
        self.hnc = HNCFramework()
        self.threats_received: List[PhiMessage] = []
        
        # Register handlers
        self.phi_bridge.register_handler("threat_alert", self._handle_threat_alert)
        self.phi_bridge.register_handler("action_broadcast", self._handle_action_broadcast)
        self.phi_bridge.register_handler("council_vote", self._handle_council_vote)
    
    def _handle_threat_alert(self, msg: PhiMessage):
        """Handle incoming threat alert from another node."""
        threat_data = msg.payload
        logger.warning(f"[NODE {self.node_id}] THREAT ALERT from {msg.sender_node}: "
                      f"{threat_data.get('entity', 'unknown')} — {threat_data.get('description', '')}")
        self.threats_received.append(msg)
    
    def _handle_action_broadcast(self, msg: PhiMessage):
        """Handle incoming action broadcast from another node."""
        action_data = msg.payload
        logger.info(f"[NODE {self.node_id}] ACTION BROADCAST from {msg.sender_node}: "
                   f"{action_data.get('action_type', 'unknown')} — {action_data.get('target', '')}")
    
    def _handle_council_vote(self, msg: PhiMessage):
        """Handle incoming council vote from another node."""
        vote_data = msg.payload
        self.quantum_vote.submit_vote(
            action_id=vote_data.get('action_id'),
            council=CouncilVote(vote_data.get('council')),
            verdict=vote_data.get('verdict')
        )
    
    def broadcast_threat(self, threat: EnvironmentalThreat):
        """Broadcast a detected threat to all nodes via phi-bridge."""
        payload = {
            "threat_id": threat.id,
            "entity": threat.target_entity,
            "severity": threat.severity.value,
            "coherence": threat.coherence_gamma,
            "description": threat.description,
            "recommended_action": threat.recommended_action.value
        }
        
        msg = self.phi_bridge.send_message("threat_alert", payload)
        logger.info(f"[NODE {self.node_id}] Broadcast threat: {threat.target_entity}")
        return msg
    
    def propose_action(self, action_id: str, action_type: str, target: str, evidence: Dict) -> Dict:
        """
        Propose an action and initiate quantum voting across councils.
        """
        logger.info(f"[NODE {self.node_id}] Proposing action: {action_id} -> {action_type} on {target}")
        
        # Auto-vote Evidence council based on data quality
        evidence_verdict = "approve" if evidence.get('confidence', 0) >= 0.65 else "reject"
        result = self.quantum_vote.submit_vote(action_id, CouncilVote.EVIDENCE, evidence_verdict)
        
        # Broadcast vote to network
        self.phi_bridge.send_message("council_vote", {
            "action_id": action_id,
            "council": "evidence",
            "verdict": evidence_verdict
        })
        
        return result
    
    def status(self) -> Dict:
        return {
            "node_id": self.node_id,
            "peers": list(self.phi_bridge.peers),
            "messages_processed": len(self.phi_bridge.message_log),
            "threats_received": len(self.threats_received),
            "pending_votes": len(self.quantum_vote.pending_votes),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ──────────────────────────────────────────────────────────────────────────────
# DEMO / TEST
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    print("=" * 60)
    print("AEDS PHI-BRIDGE — Mycelial Node Communication Test")
    print("=" * 60)
    
    # Create 3 nodes (mycelial network)
    node1 = AEDSMycelialNode("sero_main")
    node2 = AEDSMycelialNode("mnemo_governance")
    node3 = AEDSMycelialNode("kimi_coordinator")
    
    # Register peers (mycelial connections)
    node1.phi_bridge.register_peer("mnemo_governance")
    node1.phi_bridge.register_peer("kimi_coordinator")
    node2.phi_bridge.register_peer("sero_main")
    node2.phi_bridge.register_peer("kimi_coordinator")
    node3.phi_bridge.register_peer("sero_main")
    node3.phi_bridge.register_peer("mnemo_governance")
    
    # Node 1 detects a threat and broadcasts
    print("\n[TEST 1] Node 1 detects threat, broadcasts to network")
    test_threat = EnvironmentalThreat(
        id="test_001",
        timestamp=datetime.now(timezone.utc).isoformat(),
        threat_type="emissions_spike",
        severity=ThreatLevel.ALERT,
        target_entity="exxon_mobil",
        description="ExxonMobil emissions exceed threshold",
        coherence_gamma=0.680,
        recommended_action=ActionType.EXPOSE
    )
    node1.broadcast_threat(test_threat)
    
    # Node 2 proposes action, initiates quantum voting
    print("\n[TEST 2] Node 2 proposes action, quantum voting begins")
    result = node2.propose_action(
        action_id="expose_exxon_001",
        action_type="EXPOSE",
        target="exxon_mobil",
        evidence={"confidence": 0.95, "source": "NOAA"}
    )
    print(f"Evidence council: {result['evidence']}, State: {result['quantum_state']}")
    
    # Node 3 votes Ethics council
    print("\n[TEST 3] Node 3 votes Ethics council")
    result = node3.quantum_vote.submit_vote("expose_exxon_001", CouncilVote.ETHICS, "approve")
    print(f"Ethics council: {result['ethics']}, State: {result['quantum_state']}")
    
    # Node 1 votes Strategy council — wave function collapses
    print("\n[TEST 4] Node 1 votes Strategy council — WAVE FUNCTION COLLAPSE")
    result = node1.quantum_vote.submit_vote("expose_exxon_001", CouncilVote.STRATEGY, "approve")
    print(f"Strategy council: {result['strategy']}")
    print(f"QUANTUM STATE: {result['quantum_state']}")
    print(f"ACTION APPROVED: {result['action_approved']}")
    
    # Broadcast approved action
    if result['action_approved']:
        node1.phi_bridge.send_message("action_broadcast", {
            "action_id": "expose_exxon_001",
            "action_type": "EXPOSE",
            "target": "exxon_mobil",
            "approved_by": "all_3_councils"
        })
    
    # Status summary
    print("\n" + "=" * 60)
    print("NODE STATUS SUMMARY")
    print("=" * 60)
    for node in [node1, node2, node3]:
        status = node.status()
        print(f"\n{status['node_id']}:")
        print(f"  Peers: {status['peers']}")
        print(f"  Messages processed: {status['messages_processed']}")
        print(f"  Threats received: {status['threats_received']}")
        print(f"  Pending votes: {status['pending_votes']}")
    
    print("\n" + "=" * 60)
    print("PHI-BRIDGE TEST COMPLETE")
    print("=" * 60)
