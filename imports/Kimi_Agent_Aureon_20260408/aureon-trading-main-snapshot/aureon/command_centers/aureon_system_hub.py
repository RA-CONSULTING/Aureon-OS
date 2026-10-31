#!/usr/bin/env python3
"""
🌌 AUREON SYSTEM HUB - CENTRAL COMMAND & MIND MAP
==================================================
Master registry and visualization for all 90+ Aureon Trading systems.

Categories:
1. Intelligence Gatherers (Bot/Firm/Whale)
2. Market Scanners & Wave Analysis
3. Bot Tracking & Mapping
4. Momentum Systems
5. Probability & Prediction
6. Neural Networks & Learning
7. Codebreaking & Harmonics
8. Stargate & Quantum Systems
9. Dashboards & Monitoring
10. Communication & Integration
11. Execution Engines
12. Exchange Clients

Author: Aureon Trading System
Date: January 2026
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if hasattr(sys.stderr, 'buffer') and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from pathlib import Path
import json
import re
import warnings
from datetime import datetime
from collections import defaultdict
import ast
import psutil

# Sacred constants
PHI = 1.618033988749895  # Golden ratio
LOVE_FREQUENCY = 528  # Hz


@dataclass
class SystemInfo:
    """Information about a single system/module."""
    name: str
    filepath: str
    category: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    is_dashboard: bool = False
    dashboard_port: Optional[int] = None
    is_running: bool = False
    last_modified: Optional[str] = None
    lines_of_code: int = 0
    has_thought_bus: bool = False
    has_queen_integration: bool = False
    sacred_frequencies: List[float] = field(default_factory=list)


@dataclass
class SystemCategory:
    """Category grouping multiple systems."""
    name: str
    description: str
    color: str  # Hex color for visualization
    icon: str  # Emoji icon
    systems: List[SystemInfo] = field(default_factory=list)
    
    def add_system(self, system: SystemInfo):
        """Add a system to this category."""
        self.systems.append(system)
    
    @property
    def system_count(self) -> int:
        return len(self.systems)


class SystemRegistry:
    """
    Master registry for all Aureon systems.
    Auto-discovers Python modules and categorizes them.
    """
    
    def __init__(self, workspace_path: Optional[str] = None):
        if workspace_path:
            resolved_workspace = Path(workspace_path)
        else:
            env_workspace = os.getenv("AUREON_WORKSPACE")
            if env_workspace:
                resolved_workspace = Path(env_workspace)
            else:
                resolved_workspace = Path(__file__).resolve().parents[2]
        self.workspace_path = resolved_workspace.resolve()
        self.categories: Dict[str, SystemCategory] = {}
        self.systems: Dict[str, SystemInfo] = {}
        self._initialize_categories()
    
    def _initialize_categories(self):
        """Define all system categories."""
        categories_config = [
            {
                "name": "Intelligence Gatherers",
                "description": "Bot, Firm, Whale intelligence systems",
                "color": "#FF6B6B",
                "icon": "🕵️"
            },
            {
                "name": "Market Scanners",
                "description": "Wave analysis, momentum detection, market sweeps",
                "color": "#4ECDC4",
                "icon": "📊"
            },
            {
                "name": "Bot Tracking",
                "description": "Bot detection, classification, mapping",
                "color": "#45B7D1",
                "icon": "🤖"
            },
            {
                "name": "Momentum Systems",
                "description": "Movement detection >0.34%, animal-themed hunters",
                "color": "#FFA07A",
                "icon": "⚡"
            },
            {
                "name": "Probability & Prediction",
                "description": "ML prediction, coherence validation",
                "color": "#98D8C8",
                "icon": "🎯"
            },
            {
                "name": "Neural Networks",
                "description": "Queen Hive Mind, Mycelium, Elephant Memory",
                "color": "#F7B731",
                "icon": "🧠"
            },
            {
                "name": "Codebreaking & Harmonics",
                "description": "Enigma rotors, harmonic signals, frequency analysis",
                "color": "#A29BFE",
                "icon": "🔐"
            },
            {
                "name": "Stargate & Quantum",
                "description": "Planetary nodes, quantum telescopes, timeline anchoring",
                "color": "#6C5CE7",
                "icon": "🌌"
            },
            {
                "name": "Dashboards",
                "description": "Web interfaces, visualizations, monitoring",
                "color": "#FD79A8",
                "icon": "📈"
            },
            {
                "name": "Communication",
                "description": "Thought Bus, Chirp Bus, integration hubs",
                "color": "#FDCB6E",
                "icon": "🔗"
            },
            {
                "name": "Execution Engines",
                "description": "Trading execution, profit gates, order routing",
                "color": "#00B894",
                "icon": "⚙️"
            },
            {
                "name": "Exchange Clients",
                "description": "Kraken, Binance, Alpaca, Capital.com APIs",
                "color": "#74B9FF",
                "icon": "🌍"
            }
        ]
        
        for config in categories_config:
            category = SystemCategory(
                name=config["name"],
                description=config["description"],
                color=config["color"],
                icon=config["icon"]
            )
            self.categories[config["name"]] = category
    
    def scan_workspace(self):
        """Scan workspace and categorize all Python files."""
        print(f"🔍 Scanning workspace: {self.workspace_path}")

        self.systems.clear()
        for category in self.categories.values():
            category.systems.clear()

        python_files = list(self._iter_python_files())
        python_files = sorted(set(python_files))
        
        print(f"📁 Found {len(python_files)} Python modules")
        
        for filepath in python_files:
            if filepath.name.startswith('test_') or filepath.name.startswith('__'):
                continue
            
            system_info = self._analyze_file(filepath)
            if system_info:
                self.systems[system_info.name] = system_info
                
                # Categorize
                category = self._categorize_system(system_info)
                if category in self.categories:
                    self.categories[category].add_system(system_info)
        
        print(f"✅ Registered {len(self.systems)} systems across {len(self.categories)} categories")

    def _iter_python_files(self):
        """Yield Python files while skipping cache/virtualenv/vendor folders."""
        skip_dirs = {
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "node_modules",
        }
        for path in self.workspace_path.rglob("*.py"):
            if any(part in skip_dirs for part in path.parts):
                continue
            yield path
    
    def _analyze_file(self, filepath: Path) -> Optional[SystemInfo]:
        """Analyze a Python file to extract system information."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract description from docstring
            description = self._extract_docstring(content)
            
            # Count lines of code (excluding comments/blanks)
            lines = [l.strip() for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
            loc = len(lines)
            
            # Extract imports
            imports = self._extract_imports(content, filepath)
            
            # Check for integrations
            has_thought_bus = 'thought_bus' in content.lower() or 'ThoughtBus' in content
            has_queen = 'queen' in content.lower() and ('hive' in content.lower() or 'sero' in content.lower())
            
            # Check if dashboard
            is_dashboard = 'Flask' in content or 'app.run' in content or 'dashboard' in filepath.name.lower()
            dashboard_port = self._extract_port(content) if is_dashboard else None
            
            # Extract sacred frequencies
            sacred_freqs = self._extract_frequencies(content)
            
            system_info = SystemInfo(
                name=filepath.stem,
                filepath=str(filepath.relative_to(self.workspace_path)),
                category="",  # Will be set by categorization
                description=description,
                imports=imports,
                is_dashboard=is_dashboard,
                dashboard_port=dashboard_port,
                last_modified=datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
                lines_of_code=loc,
                has_thought_bus=has_thought_bus,
                has_queen_integration=has_queen,
                sacred_frequencies=sacred_freqs
            )
            
            return system_info
            
        except Exception as e:
            print(f"⚠️  Error analyzing {filepath.name}: {e}")
            return None
    
    def _extract_docstring(self, content: str) -> str:
        """Extract module docstring."""
        match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if match:
            docstring = match.group(1).strip()
            # Get first line
            first_line = docstring.split('\n')[0].strip()
            return first_line[:200]  # Limit length
        return "No description"
    
    def _extract_imports(self, content: str, filepath: Optional[Path] = None) -> List[str]:
        """Extract imported modules."""
        imports = []
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(content, filename=str(filepath) if filepath else "<unknown>")
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except:
            # Fallback to regex
            import_pattern = r'^(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            for line in content.split('\n'):
                match = re.match(import_pattern, line.strip())
                if match:
                    imports.append(match.group(1))
        
        # Filter for aureon modules
        return [imp for imp in imports if 'aureon' in imp or 'micro' in imp]
    
    def _extract_port(self, content: str) -> Optional[int]:
        """Extract Flask port number."""
        match = re.search(r'port[=\s]+(\d+)', content)
        if match:
            return int(match.group(1))
        return None
    
    def _extract_frequencies(self, content: str) -> List[float]:
        """Extract sacred frequency references."""
        frequencies = []
        sacred_patterns = [
            (r'528', 528.0),  # Love frequency
            (r'7\.83', 7.83),  # Schumann
            (r'432', 432.0),   # Sacred A
            (r'396', 396.0),   # Liberation
            (r'PHI|1\.618', 1.618)  # Golden ratio
        ]
        
        for pattern, freq in sacred_patterns:
            if re.search(pattern, content):
                frequencies.append(freq)
        
        return frequencies
    
    def _categorize_system(self, system: SystemInfo) -> str:
        """Categorize a system based on name patterns."""
        name = system.name.lower()
        desc = system.description.lower()
        
        # Bot Tracking (CHECK FIRST - before Intelligence Gatherers)
        if any(x in name for x in ['bot_hunter', 'bot_shape', 'bot_map', 'bot_entity', 
                                    'bot_intelligence', 'bot_classifier', 'bot_census',
                                    'bot_fingerprint', 'planetary_bot']):
            return "Bot Tracking"
        
        # Intelligence Gatherers (whale, firm intelligence - NOT bot tracking)
        if any(x in name for x in ['intelligence', 'profiler', 'firm', 'whale', 'counter']):
            if 'bot' not in name:  # Bot systems go to Bot Tracking
                return "Intelligence Gatherers"
        
        # Market Scanners
        if any(x in name for x in ['scanner', 'wave', 'ocean', 'mega', 'sweep']):
            if 'bot' not in name:  # Exclude bot scanners
                return "Market Scanners"
        
        # Momentum
        if any(x in name for x in ['momentum', 'animal', 'compound', 'kelly']):
            return "Momentum Systems"
        
        # Probability
        if any(x in name for x in ['probability', 'nexus', 'prediction', 'validation']):
            return "Probability & Prediction"
        
        # Neural Networks
        if any(x in name for x in ['queen', 'neuron', 'mycelium', 'elephant', 'brain', 'learning']):
            return "Neural Networks"
        
        # Codebreaking & Harmonics
        if any(x in name for x in ['enigma', 'harmonic', 'signal', 'cipher']):
            return "Codebreaking & Harmonics"
        
        # Stargate & Quantum
        if any(x in name for x in ['stargate', 'quantum', 'timeline', 'mirror']):
            return "Stargate & Quantum"
        
        # Dashboards
        if system.is_dashboard or 'dashboard' in name or 'command_center' in name:
            return "Dashboards"
        
        # Communication
        if any(x in name for x in ['bus', 'bridge', 'hub', 'orchestrator']):
            return "Communication"
        
        # Execution
        if any(x in name for x in ['execution', 'labyrinth', 'profit', 'gate', 'trader']):
            return "Execution Engines"
        
        # Exchange Clients
        if 'client' in name:
            return "Exchange Clients"
        
        # Default to Communication if has thought bus
        if system.has_thought_bus:
            return "Communication"
        
        return "Communication"  # Default category
    
    def get_category_stats(self) -> Dict:
        """Get statistics for all categories."""
        stats = {}
        for cat_name, category in self.categories.items():
            stats[cat_name] = {
                "count": category.system_count,
                "total_loc": sum(s.lines_of_code for s in category.systems),
                "dashboards": sum(1 for s in category.systems if s.is_dashboard),
                "thought_bus_integrated": sum(1 for s in category.systems if s.has_thought_bus),
                "queen_integrated": sum(1 for s in category.systems if s.has_queen_integration)
            }
        return stats
    
    def export_mind_map_data(self) -> Dict:
        """Export data for mind map visualization."""
        nodes = []
        edges = []
        running_cmdlines = self._get_running_cmdlines()
        
        # Create nodes for each system
        for system in self.systems.values():
            category = self._categorize_system(system)
            cat_obj = self.categories.get(category)
            is_running = self._is_system_running(system, running_cmdlines)
            system.is_running = is_running
            background_color = cat_obj.color if cat_obj else "#999999"
            border_color = "#00B894" if is_running else "#FF6B6B"
            
            node = {
                "id": system.name,
                "label": system.name.replace('aureon_', '').replace('_', ' ').title(),
                "title": system.description,
                "group": category,
                "color": {
                    "background": background_color,
                    "border": border_color,
                    "highlight": {
                        "background": background_color,
                        "border": border_color,
                    },
                    "hover": {
                        "background": background_color,
                        "border": border_color,
                    },
                },
                "shape": "dot" if not system.is_dashboard else "star",
                "size": min(10 + system.lines_of_code / 100, 50),
                "font": {"size": 14},
                "is_dashboard": system.is_dashboard,
                "dashboard_port": system.dashboard_port,
                "loc": system.lines_of_code,
                "has_thought_bus": system.has_thought_bus,
                "has_queen": system.has_queen_integration,
                "is_running": is_running
            }
            nodes.append(node)
        
        # Create edges based on imports
        for system in self.systems.values():
            for imported in system.imports:
                if imported in self.systems:
                    edge = {
                        "from": system.name,
                        "to": imported,
                        "arrows": "to",
                        "color": {"opacity": 0.3},
                        "width": 1
                    }
                    edges.append(edge)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "categories": [
                {
                    "name": cat.name,
                    "color": cat.color,
                    "icon": cat.icon,
                    "count": cat.system_count
                }
                for cat in self.categories.values()
            ]
        }

    @staticmethod
    def _get_running_cmdlines() -> List[str]:
        cmdlines = []
        try:
            for proc in psutil.process_iter(attrs=["cmdline"]):
                cmdline = proc.info.get("cmdline") or []
                if cmdline:
                    cmdlines.append(" ".join(cmdline).lower())
        except Exception:
            return []
        return cmdlines

    @staticmethod
    def _is_system_running(system: SystemInfo, cmdlines: List[str]) -> bool:
        targets = {
            system.name.lower(),
            f"{system.name}.py".lower(),
            system.filepath.lower(),
        }

        for cmd in cmdlines:
            for target in targets:
                if target and target in cmd:
                    return True
        return False
    
    def save_registry(self, output_path: str = "aureon_system_registry.json"):
        """Save the full registry to JSON."""
        data = {
            "generated": datetime.now().isoformat(),
            "total_systems": len(self.systems),
            "categories": {
                name: {
                    "description": cat.description,
                    "icon": cat.icon,
                    "color": cat.color,
                    "systems": [
                        {
                            "name": s.name,
                            "filepath": s.filepath,
                            "description": s.description,
                            "loc": s.lines_of_code,
                            "is_dashboard": s.is_dashboard,
                            "dashboard_port": s.dashboard_port,
                            "has_thought_bus": s.has_thought_bus,
                            "has_queen_integration": s.has_queen_integration,
                            "sacred_frequencies": s.sacred_frequencies
                        }
                        for s in cat.systems
                    ]
                }
                for name, cat in self.categories.items()
            },
            "statistics": self.get_category_stats()
        }
        
        filepath = self.workspace_path / output_path
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 Saved registry to {output_path}")


def main():
    """Main entry point."""
    print("🌌 AUREON SYSTEM HUB - Initializing...")
    print("=" * 60)
    
    registry = SystemRegistry()
    registry.scan_workspace()
    
    print("\n📊 Category Statistics:")
    print("-" * 60)
    
    stats = registry.get_category_stats()
    for cat_name, cat_stats in stats.items():
        category = registry.categories[cat_name]
        print(f"{category.icon} {cat_name:25s} | {cat_stats['count']:3d} systems | {cat_stats['total_loc']:6d} LOC")
    
    print("\n" + "=" * 60)
    print(f"✅ Total: {len(registry.systems)} systems registered")
    print(f"📊 Total LOC: {sum(s.lines_of_code for s in registry.systems.values()):,}")
    print(f"🌐 Dashboards: {sum(1 for s in registry.systems.values() if s.is_dashboard)}")
    print(f"🔗 ThoughtBus Integrated: {sum(1 for s in registry.systems.values() if s.has_thought_bus)}")
    print(f"👑 Queen Integrated: {sum(1 for s in registry.systems.values() if s.has_queen_integration)}")
    
    # Save registry
    registry.save_registry()
    
    print("\n🌐 Launch Dashboard:")
    print("   python aureon_system_hub_dashboard.py")
    print("   Then open: http://localhost:13001")


if __name__ == "__main__":
    main()
