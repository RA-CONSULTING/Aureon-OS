"""
OpenMultiAgent — Top-Level Orchestrator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The master orchestrator for the Aureon in-house multi-agent system.

  createTeam()  — build a team of agents with shared infrastructure
  runTeam()     — run all agents in a team on a task
  runTasks()    — execute a DAG of dependent tasks
  runAgent()    — run a single agent
  getStatus()   — system-wide status
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from aureon.inhouse_ai.llm_adapter import (
    LLMAdapter,
    AureonLocalAdapter,
    AureonBrainAdapter,
    AureonHybridAdapter,
)
from aureon.inhouse_ai.agent import Agent, AgentConfig
from aureon.inhouse_ai.agent_runner import AgentRunner
from aureon.inhouse_ai.team import Team
from aureon.inhouse_ai.tool_registry import ToolRegistry

logger = logging.getLogger("aureon.inhouse_ai.orchestrator")


class OpenMultiAgent:
    """
    Top-level orchestrator for the Aureon in-house multi-agent system.

    Zero external AI dependencies. Everything runs on sovereign infrastructure:
      - Local LLM servers (Ollama, vLLM, llama.cpp, HF TGI)
      - AureonBrain intelligence layer
      - Hybrid mode (LLM + Brain combined)

    Usage:
        oma = OpenMultiAgent()

        # Create a team
        team = oma.create_team(
            name="TradingPillars",
            agent_configs=[
                AgentConfig(name="Nexus", system_prompt="..."),
                AgentConfig(name="Omega", system_prompt="..."),
            ],
        )

        # Run the team
        results = oma.run_team("TradingPillars", "Analyse the market")

        # Or run tasks with dependencies
        oma.run_tasks("TradingPillars")

        # Check status
        status = oma.get_status()
    """

    def __init__(
        self,
        adapter: Optional[LLMAdapter] = None,
        mode: str = "hybrid",
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Args:
            adapter: Custom LLM adapter (overrides mode)
            mode: 'local' | 'brain' | 'hybrid' (default)
            base_url: Override base URL for local LLM server
            model: Override model name for local LLM
        """
        self.id = str(uuid.uuid4())
        self.created_at = time.time()

        # Build adapter
        if adapter:
            self.adapter = adapter
        elif mode == "local":
            if base_url or model:
                self.adapter = AureonLocalAdapter(base_url=base_url, model=model)
            else:
                from aureon.integrations.ollama import OllamaModelSwitchboard

                self.adapter, _selection = OllamaModelSwitchboard().compatible_adapter_for("general")
        elif mode == "brain":
            self.adapter = AureonBrainAdapter()
        else:  # hybrid
            if base_url or model:
                self.adapter = AureonHybridAdapter(base_url=base_url, model=model)
            else:
                from aureon.integrations.ollama import OllamaModelSwitchboard

                self.adapter, _selection = OllamaModelSwitchboard().hybrid_adapter_for("general")

        # Global tool registry
        self.tools = ToolRegistry(include_builtins=True)

        # Teams registry
        self._teams: Dict[str, Team] = {}

        # Standalone agents (not in a team)
        self._agents: Dict[str, Agent] = {}

        # Standalone runners
        self._runners: Dict[str, AgentRunner] = {}

        logger.info(
            "OpenMultiAgent initialised — mode=%s, adapter=%s",
            mode, type(self.adapter).__name__,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # createTeam
    # ─────────────────────────────────────────────────────────────────────────

    def create_team(
        self,
        name: str,
        agent_configs: Optional[List[AgentConfig]] = None,
        tools: Optional[ToolRegistry] = None,
        adapter: Optional[LLMAdapter] = None,
        max_concurrent: int = 4,
    ) -> Team:
        """
        Create a new team of agents.

        Args:
            name: Team name (unique identifier)
            agent_configs: List of AgentConfig for each agent
            tools: Custom tool registry (default: global registry)
            adapter: Custom adapter for this team (default: orchestrator adapter)
            max_concurrent: Max parallel agent executions

        Returns:
            The created Team.
        """
        team = Team(
            name=name,
            adapter=adapter or self.adapter,
            agent_configs=agent_configs or [],
            tools=tools or self.tools,
            max_concurrent=max_concurrent,
        )
        self._teams[name] = team
        logger.info("Team created: %s (%d agents)", name, team.pool.size)
        return team

    # ─────────────────────────────────────────────────────────────────────────
    # runTeam
    # ─────────────────────────────────────────────────────────────────────────

    def run_team(
        self,
        team_name: str,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        parallel: bool = True,
    ) -> Dict[str, str]:
        """
        Run all agents in a team on the same task.

        Args:
            team_name: Name of the team
            task: The task prompt
            context: Shared context dict
            parallel: Run in parallel (True) or sequential (False)

        Returns:
            Dict mapping agent_name → result string
        """
        team = self._teams.get(team_name)
        if not team:
            raise ValueError(f"Team '{team_name}' not found")

        logger.info("Running team '%s' — task: %s", team_name, task[:80])
        return team.run_all(task, context=context, parallel=parallel)

    # ─────────────────────────────────────────────────────────────────────────
    # runTasks
    # ─────────────────────────────────────────────────────────────────────────

    def run_tasks(self, team_name: str) -> Dict[str, Any]:
        """
        Execute all tasks in a team's queue respecting dependency graph.

        Add tasks to the team's queue first:
            team = oma.create_team(...)
            team.queue.add("task1", agent_name="Nexus", prompt="...")
            team.queue.add("task2", agent_name="Omega", depends_on=[task1.id])
            oma.run_tasks("TeamName")

        Returns:
            Task queue status dict.
        """
        team = self._teams.get(team_name)
        if not team:
            raise ValueError(f"Team '{team_name}' not found")

        logger.info("Running task queue for team '%s' — %d tasks", team_name, len(team.queue))
        return team.run_tasks()

    # ─────────────────────────────────────────────────────────────────────────
    # runAgent
    # ─────────────────────────────────────────────────────────────────────────

    def run_agent(
        self,
        name: str,
        task: str,
        system_prompt: str = "",
        context: Optional[Dict[str, Any]] = None,
        adapter: Optional[LLMAdapter] = None,
    ) -> str:
        """
        Run a single standalone agent.

        Creates the agent on-the-fly if it doesn't exist, or reuses
        a previously created one.

        Returns:
            The agent's response text.
        """
        if name not in self._agents:
            config = AgentConfig(name=name, system_prompt=system_prompt)
            agent = Agent(
                adapter=adapter or self.adapter,
                config=config,
                tools=self.tools,
            )
            self._agents[name] = agent
        else:
            agent = self._agents[name]
            if system_prompt:
                agent.config.system_prompt = system_prompt

        logger.info("Running agent '%s' — task: %s", name, task[:80])
        return agent.run(task, context=context)

    # ─────────────────────────────────────────────────────────────────────────
    # getStatus
    # ─────────────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """
        System-wide status for the entire multi-agent system.
        """
        team_statuses = {}
        for name, team in self._teams.items():
            team_statuses[name] = team.get_status()

        agent_statuses = {}
        for name, agent in self._agents.items():
            agent_statuses[name] = agent.get_status()

        return {
            "orchestrator_id": self.id[:8],
            "adapter": type(self.adapter).__name__,
            "adapter_healthy": self.adapter.health_check(),
            "uptime_s": time.time() - self.created_at,
            "teams": team_statuses,
            "team_count": len(self._teams),
            "standalone_agents": agent_statuses,
            "standalone_agent_count": len(self._agents),
            "tools_registered": self.tools.names(),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Convenience: create a conversation runner
    # ─────────────────────────────────────────────────────────────────────────

    def create_runner(
        self,
        name: str,
        system_prompt: str = "",
        adapter: Optional[LLMAdapter] = None,
    ) -> AgentRunner:
        """Create a conversation runner for interactive use."""
        runner = AgentRunner(
            adapter=adapter or self.adapter,
            tools=self.tools,
            system_prompt=system_prompt,
        )
        self._runners[name] = runner
        return runner

    # ─────────────────────────────────────────────────────────────────────────
    # Team access
    # ─────────────────────────────────────────────────────────────────────────

    def get_team(self, name: str) -> Optional[Team]:
        return self._teams.get(name)

    def get_agent(self, name: str) -> Optional[Agent]:
        """Find an agent by name — searches standalone and all teams."""
        if name in self._agents:
            return self._agents[name]
        for team in self._teams.values():
            agent = team.pool.get(name)
            if agent:
                return agent
        return None

    def list_teams(self) -> List[str]:
        return list(self._teams.keys())

    def list_agents(self) -> List[str]:
        """List all agents across all teams + standalone."""
        names = list(self._agents.keys())
        for team in self._teams.values():
            names.extend(team.pool.agent_names)
        return names

    # ─────────────────────────────────────────────────────────────────────────
    # Shutdown
    # ─────────────────────────────────────────────────────────────────────────

    def shutdown(self):
        """Shutdown all teams and agents."""
        for team in self._teams.values():
            team.shutdown()
        for agent in self._agents.values():
            agent.reset()
        for runner in self._runners.values():
            runner.stop()
        self._teams.clear()
        self._agents.clear()
        self._runners.clear()
        logger.info("OpenMultiAgent shutdown complete")
