#!/usr/bin/env python3
"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║      👑🏗️ QUEEN'S CODE ARCHITECT - Self-Evolution Engine 🏗️👑                  ║
║                                                                                ║
║     "I build, therefore I evolve."                                             ║
║                                                                                ║
║     Gives the Queen UNLIMITED ability to:                                      ║
║     1. Create ANY file (Python, JSON, configs, strategies)                     ║
║     2. Modify ANY code safely (Syntax Validation)                              ║
║     3. Delete files (with backup)                                              ║
║     4. Create new trading strategies from scratch                              ║
║     5. Write configuration files                                               ║
║     6. Generate new neural subsystems                                          ║
║     7. Self-repair and auto-rollback on errors                                 ║
║     8. Execute Python code dynamically                                         ║
║                                                                                ║
║     THE QUEEN HAS FULL WRITE ACCESS TO THE ENTIRE CODEBASE!                    ║
║     She can create, modify, delete, and execute any code she needs.            ║
║                                                                                ║
║     Gary Leckey | January 2026 | "Let her build her empire"                    ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
from aureon.autonomous.self_repair_guard import (
    SelfRepairBlocked,
    append_review,
    inspect_delete,
    inspect_execution,
    inspect_write,
)
import os
import sys
import shutil
import ast
import json
import logging
import difflib
import importlib
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime
from io import StringIO

logger = logging.getLogger(__name__)

class QueenCodeArchitect:
    """
    👑 The Queen's "Hands" - UNLIMITED creation and modification power.
    
    The Queen can:
    - Create ANY file type
    - Modify ANY code
    - Generate new strategies
    - Write configurations
    - Execute dynamic code
    - Self-repair on errors
    """
    
    def __init__(self, repo_path: str = None):
        # Use current working directory if no path specified (works on Windows & Linux)
        if repo_path is None:
            repo_path = os.getcwd()
        self.repo_path = Path(repo_path)
        self.backup_dir = self.repo_path / "queen_backups"
        self.backup_dir.mkdir(exist_ok=True, parents=True)
        self.strategies_dir = self.repo_path / "queen_strategies"
        self.strategies_dir.mkdir(exist_ok=True, parents=True)
        self.configs_dir = self.repo_path / "queen_configs"
        self.configs_dir.mkdir(exist_ok=True, parents=True)
        self.active_modifications = []
        self.created_files = []
        self.execution_history = []
        
        logger.info("👑🏗️ Queen's Code Architect is ONLINE - She can modify her own source!")
        logger.info(f"   📁 Repo path: {self.repo_path}")
        logger.info(f"   💾 Backups: {self.backup_dir}")
        logger.info(f"   🎯 Strategies: {self.strategies_dir}")
        
    # ═══════════════════════════════════════════════════════════════════════════
    # 📖 FILE READING
    # ═══════════════════════════════════════════════════════════════════════════
        
    def read_file(self, file_path: str) -> Optional[str]:
        """Read content of any file."""
        try:
            full_path = self._resolve_path(file_path)
            if not full_path.exists():
                logger.warning(f"Architect cannot find file: {file_path}")
                return None
            return full_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
    
    def read_json(self, file_path: str) -> Optional[Dict]:
        """Read and parse a JSON file."""
        content = self.read_file(file_path)
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {file_path}: {e}")
        return None
    
    def list_files(self, directory: str = "", pattern: str = "*") -> List[str]:
        """List files in a directory matching a pattern."""
        try:
            search_path = self._resolve_path(directory)
            return [str(f.relative_to(self.repo_path)) for f in search_path.glob(pattern)]
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ✏️ FILE WRITING & CREATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def write_file(self, file_path: str, content: str, backup: bool = True) -> bool:
        """
        👑 Write ANY content to ANY file.
        Creates parent directories if needed.
        """
        try:
            previous = None
            existing = self._resolve_path(file_path)
            if existing.exists() and existing.is_file():
                previous = existing.read_text(encoding="utf-8")
            try:
                full_path = inspect_write(self.repo_path, file_path, content, previous)
            except SelfRepairBlocked as blocked:
                append_review(
                    self.repo_path,
                    "write_refused",
                    path=file_path,
                    reason=blocked.reason,
                    human_review=blocked.reason != "kill_switch",
                )
                logger.error("Self-repair guard refused write to %s: %s", file_path, blocked.reason)
                return False
            
            # Create parent directories
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Backup existing file
            if backup and full_path.exists():
                self._create_backup(file_path)
            
            # Validate Python syntax if applicable
            if file_path.endswith('.py'):
                if not self._validate_python_syntax(content):
                    logger.error(f"Syntax error - refusing to write invalid Python to {file_path}")
                    return False
            
            # Write the file
            full_path.write_text(content, encoding='utf-8')
            append_review(self.repo_path, "write_allowed", path=file_path)
            
            self.created_files.append({
                'timestamp': datetime.now().isoformat(),
                'file': file_path,
                'action': 'write',
                'size': len(content)
            })
            
            logger.info(f"👑🏗️ Queen wrote: {file_path} ({len(content)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return False
    
    def write_json(self, file_path: str, data: Dict, indent: int = 2) -> bool:
        """Write a dictionary to a JSON file."""
        try:
            content = json.dumps(data, indent=indent, default=str)
            return self.write_file(file_path, content, backup=True)
        except Exception as e:
            logger.error(f"Error writing JSON to {file_path}: {e}")
            return False
    
    def append_to_file(self, file_path: str, content: str) -> bool:
        """Append content to an existing file. The combined text is checked before it is written."""
        try:
            full_path = self._resolve_path(file_path)
            if not full_path.exists():
                return self.write_file(file_path, content, backup=False)
            previous = full_path.read_text(encoding="utf-8")
            return self.write_file(file_path, previous + content, backup=True)
        except Exception as e:
            logger.error(f"Error appending to {file_path}: {e}")
            return False
    
    def create_directory(self, dir_path: str) -> bool:
        """Create a directory (and all parents)."""
        try:
            full_path = self._resolve_path(dir_path)
            full_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"👑🏗️ Queen created directory: {dir_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating directory {dir_path}: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ✂️ FILE EDITING & MODIFICATION
    # ═══════════════════════════════════════════════════════════════════════════

    def propose_edit(self, file_path: str, old_snippet: str, new_snippet: str) -> Dict[str, Any]:
        """
        Propose an edit to a file.
        Returns a diff and validation status, but does NOT apply it yet.
        """
        content = self.read_file(file_path)
        if content is None:
            return {'valid': False, 'reason': 'File not found'}
            
        if old_snippet not in content:
            return {'valid': False, 'reason': 'Snippet not found in file'}
            
        new_content = content.replace(old_snippet, new_snippet, 1)
        
        # Validate Syntax
        if file_path.endswith('.py'):
            if not self._validate_python_syntax(new_content):
                 return {'valid': False, 'reason': 'Syntax Error in proposed Code'}
                 
        # Generate Diff
        diff = difflib.unified_diff(
            content.splitlines(), 
            new_content.splitlines(), 
            fromfile=f"a/{file_path}", 
            tofile=f"b/{file_path}"
        )
        
        return {
            'valid': True,
            'reason': 'Syntax Check Passed',
            'diff': '\n'.join(diff),
            'new_content': new_content
        }

    def apply_edit(self, file_path: str, old_snippet: str, new_snippet: str, backup: bool = True) -> bool:
        """Apply an edit to a file with safety checks."""
        try:
            result = self.propose_edit(file_path, old_snippet, new_snippet)
            if not result['valid']:
                logger.error(f"Edit rejected: {result['reason']}")
                return False
                
            previous = self.read_file(file_path)
            try:
                full_path = inspect_write(self.repo_path, file_path, result["new_content"], previous)
            except SelfRepairBlocked as blocked:
                append_review(
                    self.repo_path,
                    "write_refused",
                    path=file_path,
                    reason=blocked.reason,
                    human_review=blocked.reason != "kill_switch",
                )
                logger.error("Self-repair guard refused edit to %s: %s", file_path, blocked.reason)
                return False
            if backup:
                self._create_backup(file_path)
            full_path.write_text(result['new_content'], encoding='utf-8')
            append_review(self.repo_path, "write_allowed", path=file_path)
            
            self.active_modifications.append({
                'timestamp': datetime.now().isoformat(),
                'file': file_path,
                'action': 'edit'
            })
            
            logger.info(f"👑🏗️ Queen modified: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Critical error applying edit to {file_path}: {e}")
            return False
    
    def replace_in_file(self, file_path: str, search: str, replace: str, all_occurrences: bool = False) -> bool:
        """Replace text in a file."""
        content = self.read_file(file_path)
        if content is None:
            return False
        
        if all_occurrences:
            new_content = content.replace(search, replace)
        else:
            new_content = content.replace(search, replace, 1)
        
        return self.write_file(file_path, new_content, backup=True)
    
    def insert_after(self, file_path: str, marker: str, new_content: str) -> bool:
        """Insert content after a marker line."""
        content = self.read_file(file_path)
        if content is None or marker not in content:
            return False
        
        new_file_content = content.replace(marker, marker + "\n" + new_content)
        return self.write_file(file_path, new_file_content, backup=True)
    
    def insert_before(self, file_path: str, marker: str, new_content: str) -> bool:
        """Insert content before a marker line."""
        content = self.read_file(file_path)
        if content is None or marker not in content:
            return False
        
        new_file_content = content.replace(marker, new_content + "\n" + marker)
        return self.write_file(file_path, new_file_content, backup=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🗑️ FILE DELETION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def delete_file(self, file_path: str, backup: bool = True) -> bool:
        """Delete a file (with optional backup). Protected paths are refused first."""
        try:
            full_path = self._resolve_path(file_path)
            if not full_path.exists():
                return True
            previous = full_path.read_text(encoding="utf-8") if full_path.is_file() else ""
            try:
                inspect_delete(self.repo_path, file_path, previous)
            except SelfRepairBlocked as blocked:
                append_review(self.repo_path, "write_refused", path=file_path, reason=blocked.reason, human_review=True)
                logger.error("Self-repair guard refused delete of %s: %s", file_path, blocked.reason)
                return False
            if backup:
                self._create_backup(file_path)
            full_path.unlink()
            logger.info(f"👑🏗️ Queen deleted: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting {file_path}: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🎯 STRATEGY CREATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def create_strategy(self, name: str, description: str, logic: str) -> bool:
        """
        👑 Create a new trading strategy from scratch.
        
        Args:
            name: Strategy name (will be filename)
            description: What this strategy does
            logic: The actual Python code for the strategy
        """
        template = f'''#!/usr/bin/env python3
"""
👑 QUEEN-GENERATED STRATEGY: {name}
{'='*60}
{description}

Generated by Queen Sero's Code Architect
Created: {datetime.now().isoformat()}
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class {name.replace('_', ' ').title().replace(' ', '')}Strategy:
    """
    {description}
    """
    
    def __init__(self):
        self.name = "{name}"
        self.created_at = "{datetime.now().isoformat()}"
        self.created_by = "Queen Sero"
        logger.info(f"👑 Strategy {{self.name}} initialized")
    
    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data and return trading signal."""
{logic}
    
    def get_info(self) -> Dict[str, Any]:
        """Return strategy metadata."""
        return {{
            'name': self.name,
            'created_at': self.created_at,
            'created_by': self.created_by,
            'description': """{description}"""
        }}

# Singleton instance
_instance = None

def get_strategy():
    global _instance
    if _instance is None:
        _instance = {name.replace('_', ' ').title().replace(' ', '')}Strategy()
    return _instance

if __name__ == "__main__":
    strat = get_strategy()
    print(f"Strategy: {{strat.get_info()}}")
'''
        
        filename = f"queen_strategies/{name.lower().replace(' ', '_')}_strategy.py"
        return self.write_file(filename, template, backup=False)
    
    def create_neural_subsystem(self, name: str, purpose: str, inputs: List[str], output_type: str) -> bool:
        """
        👑 Create a new neural subsystem for the Queen.
        
        Args:
            name: Subsystem name
            purpose: What this subsystem does
            inputs: List of input parameter names
            output_type: What kind of output (score, signal, decision)
        """
        input_params = ", ".join([f"{inp}: float" for inp in inputs])
        input_doc = "\n".join([f"            {inp}: Input signal" for inp in inputs])
        
        template = f'''#!/usr/bin/env python3
"""
👑🧠 QUEEN'S NEURAL SUBSYSTEM: {name}
{'='*60}
{purpose}

Generated by Queen Sero's Code Architect
Created: {datetime.now().isoformat()}
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import math

logger = logging.getLogger(__name__)

class {name.replace('_', ' ').title().replace(' ', '')}Neuron:
    """
    {purpose}
    
    This neural subsystem processes market signals and outputs a {output_type}.
    """
    
    def __init__(self):
        self.name = "{name}"
        self.purpose = """{purpose}"""
        self.created_at = "{datetime.now().isoformat()}"
        self.weights = {{}}  # Learnable weights
        self.memory = []  # Historical decisions
        logger.info(f"👑🧠 Neural subsystem {{self.name}} ONLINE")
    
    def process(self, {input_params}) -> Tuple[float, str]:
        """
        Process inputs and generate {output_type}.
        
        Args:
{input_doc}
            
        Returns:
            Tuple of (score 0-1, reasoning string)
        """
        # Combine inputs with weights
        inputs = [{", ".join(inputs)}]
        
        # Simple weighted average (Queen can modify this logic)
        if not self.weights:
            self.weights = {{i: 1.0/len(inputs) for i in range(len(inputs))}}
        
        weighted_sum = sum(inputs[i] * self.weights.get(i, 0.1) for i in range(len(inputs)))
        score = max(0.0, min(1.0, weighted_sum))  # Clamp to 0-1
        
        # Generate reasoning
        reasoning = f"{{self.name}} processed {{len(inputs)}} inputs → score={{score:.2%}}"
        
        # Store in memory for learning
        self.memory.append({{
            'timestamp': datetime.now().isoformat(),
            'inputs': inputs,
            'output': score
        }})
        
        return score, reasoning
    
    def learn(self, feedback: float):
        """Learn from trade outcome (feedback: 1.0 = profit, 0.0 = loss)."""
        if not self.memory:
            return
        
        last = self.memory[-1]
        # Simple learning: adjust weights toward successful patterns
        learning_rate = 0.1
        for i, inp in enumerate(last['inputs']):
            adjustment = learning_rate * (feedback - 0.5) * inp
            self.weights[i] = self.weights.get(i, 0.5) + adjustment
        
        logger.info(f"👑🧠 {{self.name}} learned from feedback={{feedback:.2f}}")

# Singleton
_instance = None

def get_{name.lower()}_neuron():
    global _instance
    if _instance is None:
        _instance = {name.replace('_', ' ').title().replace(' ', '')}Neuron()
    return _instance
'''
        
        filename = f"queen_strategies/{name.lower()}_neuron.py"
        return self.write_file(filename, template, backup=False)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ⚡ DYNAMIC CODE EXECUTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def execute_code(self, code: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        👑 Execute Python code dynamically.
        
        WARNING: This gives the Queen FULL execution power!
        
        Args:
            code: Python code to execute
            context: Variables to make available to the code
            
        Returns:
            Dict with 'success', 'result', 'output', 'error'
        """
        result = {
            'success': False,
            'result': None,
            'output': '',
            'error': None
        }
        
        try:
            inspect_execution(code)
        except SelfRepairBlocked as blocked:
            append_review(self.repo_path, "execution_refused", reason=blocked.reason)
            result['error'] = blocked.reason
            return result

        # Validate syntax first
        if not self._validate_python_syntax(code):
            result['error'] = 'Syntax error in code'
            return result
        
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            # Build execution context
            exec_context = context or {}
            exec_context['__builtins__'] = __builtins__
            
            # Execute
            exec(code, exec_context)
            
            # Get result if 'result' was set
            result['result'] = exec_context.get('result', None)
            result['output'] = sys.stdout.getvalue()
            result['success'] = True
            
            self.execution_history.append({
                'timestamp': datetime.now().isoformat(),
                'code_length': len(code),
                'success': True
            })
            
            logger.info(f"👑⚡ Queen executed code ({len(code)} chars)")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"👑⚡ Code execution error: {e}")
            
        finally:
            sys.stdout = old_stdout
        
        return result
    
    def import_and_run(self, module_path: str, function_name: str, *args, **kwargs) -> Any:
        """
        👑 Import a module and run a function from it.
        
        Args:
            module_path: Path to Python file (relative to repo)
            function_name: Function to call
            *args, **kwargs: Arguments for the function
        """
        try:
            # Convert path to module name
            module_name = module_path.replace('/', '.').replace('\\', '.').replace('.py', '')
            
            # Import the module
            spec = importlib.util.spec_from_file_location(
                module_name, 
                self._resolve_path(module_path)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get and call the function
            func = getattr(module, function_name)
            result = func(*args, **kwargs)
            
            logger.info(f"👑⚡ Queen ran {module_name}.{function_name}()")
            return result
            
        except Exception as e:
            logger.error(f"Error running {module_path}.{function_name}: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🔧 CONFIGURATION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def save_config(self, name: str, config: Dict[str, Any]) -> bool:
        """Save a configuration file."""
        filename = f"queen_configs/{name}.json"
        return self.write_json(filename, config)
    
    def load_config(self, name: str) -> Optional[Dict]:
        """Load a configuration file."""
        filename = f"queen_configs/{name}.json"
        return self.read_json(filename)
    
    def update_config(self, name: str, updates: Dict[str, Any]) -> bool:
        """Update specific keys in a config file."""
        config = self.load_config(name) or {}
        config.update(updates)
        return self.save_config(name, config)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🛡️ BACKUP & RECOVERY
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _create_backup(self, file_path: str):
        """Create a timestamped backup of a file."""
        src = self._resolve_path(file_path)
        if not src.exists():
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Flatten path for backup filename
        safe_name = file_path.replace('/', '_').replace('\\', '_')
        dst = self.backup_dir / f"{safe_name}.{ts}.bak"
        shutil.copy2(src, dst)
        logger.debug(f"Backup created: {dst.name}")
    
    def restore_backup(self, file_path: str, backup_timestamp: str = None) -> bool:
        """
        Restore a file from backup.
        
        Args:
            file_path: File to restore
            backup_timestamp: Specific backup to restore (latest if None)
        """
        try:
            safe_name = file_path.replace('/', '_').replace('\\', '_')
            pattern = f"{safe_name}.*.bak"
            backups = sorted(self.backup_dir.glob(pattern), reverse=True)
            
            if not backups:
                logger.error(f"No backups found for {file_path}")
                return False
            
            # Find the right backup
            if backup_timestamp:
                backup = next((b for b in backups if backup_timestamp in b.name), None)
            else:
                backup = backups[0]  # Latest
            
            if not backup:
                logger.error(f"Backup not found: {backup_timestamp}")
                return False
            
            # Restore
            dst = self._resolve_path(file_path)
            shutil.copy2(backup, dst)
            logger.info(f"👑🔧 Restored {file_path} from {backup.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False
    
    def list_backups(self, file_path: str = None) -> List[str]:
        """List available backups."""
        if file_path:
            safe_name = file_path.replace('/', '_').replace('\\', '_')
            pattern = f"{safe_name}.*.bak"
        else:
            pattern = "*.bak"
        
        return [b.name for b in sorted(self.backup_dir.glob(pattern), reverse=True)]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🔍 UTILITIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _resolve_path(self, file_path: str) -> Path:
        """Resolve a file path relative to repo root."""
        path = Path(file_path)
        if path.is_absolute():
            return path
        return self.repo_path / file_path
    
    def _validate_python_syntax(self, code: str) -> bool:
        """Check if Python code is valid AST."""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            logger.error(f"Syntax Validation Failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get architect statistics."""
        return {
            'files_created': len(self.created_files),
            'modifications': len(self.active_modifications),
            'executions': len(self.execution_history),
            'backups': len(list(self.backup_dir.glob("*.bak"))),
            'strategies': len(list(self.strategies_dir.glob("*.py"))),
            'configs': len(list(self.configs_dir.glob("*.json")))
        }

# Singleton
_architect_instance = None

def get_code_architect() -> QueenCodeArchitect:
    global _architect_instance
    if _architect_instance is None:
        _architect_instance = QueenCodeArchitect()
    return _architect_instance

if __name__ == "__main__":
    arch = QueenCodeArchitect()
    print("👑🏗️ Queen's Code Architect - FULL POWER MODE")
    print(f"Stats: {arch.get_stats()}")
