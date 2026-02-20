"""Pydantic AI agent implementations for RALPH specialist roles.

Uses pydantic-ai for structured output validation and tool binding.
Each agent wraps an AgentSpec with runtime execution capabilities.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from pydantic import BaseModel, Field
    from pydantic_ai import Agent as PydanticAgent
    from pydantic_ai import RunContext
    HAS_PYDANTIC_AI = True
except ImportError:
    HAS_PYDANTIC_AI = False

from ralph.agents import AgentSpec, AgentRole, AGENT_SPECS
from ralph.tools import ToolRegistry

logger = logging.getLogger("ralph.pydantic_agents")


# --- Structured Output Models ---

if HAS_PYDANTIC_AI:

    class GraphAnalysis(BaseModel):
        """Output from the graph analyst agent."""
        total_nodes: int = Field(description="Total nodes in graph")
        clusters: int = Field(description="Number of clusters")
        orphan_count: int = Field(description="Disconnected nodes")
        top_pagerank_nodes: list[str] = Field(description="Top 5 nodes by PageRank")
        delta_miss_count: int = Field(description="Nodes with delta_class == 'miss'")
        recommendations: list[str] = Field(description="Suggested actions")

    class ContentPlan(BaseModel):
        """Output from the content writer agent."""
        action: str = Field(description="create, update, or validate")
        file_path: str = Field(description="Target vault file path")
        entity_type: str = Field(description="mdbase type (lo, saq, concept, etc.)")
        frontmatter: dict[str, Any] = Field(description="YAML frontmatter fields")
        body_sections: list[str] = Field(description="Markdown section headings")
        validation_status: str = Field(description="pass, fail, or pending")

    class TaskPlan(BaseModel):
        """Output from the task manager agent."""
        tasks: list[dict[str, Any]] = Field(description="Tasks to create/update")
        beads_to_close: list[str] = Field(description="Bead IDs to close")
        priority_rationale: str = Field(description="Why these tasks are prioritized")

    class SystemTwoInsight(BaseModel):
        """Output from the System 2 deep thinker."""
        insight: str = Field(description="The synthesized insight")
        confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
        evidence: list[str] = Field(description="Supporting vault file paths")
        contradictions: list[str] = Field(description="Conflicting evidence")
        suggested_pkg_note: str | None = Field(description="Suggested PKG note content")

    class OrchestratorPlan(BaseModel):
        """Output from the orchestrator agent."""
        delegations: list[dict[str, str]] = Field(
            description="List of {agent, task, priority} delegations"
        )
        parallel: bool = Field(description="Whether delegations can run in parallel")
        estimated_iterations: int = Field(description="Expected RALPH iterations needed")


def create_pydantic_agent(
    spec: AgentSpec,
    tools: ToolRegistry,
) -> Any:
    """Create a pydantic-ai Agent from an AgentSpec.

    Returns a PydanticAgent configured with the spec's model, system prompt,
    and tool bindings.
    """
    if not HAS_PYDANTIC_AI:
        raise RuntimeError("pydantic-ai not installed. Run: pip install pydantic-ai")

    # Map role to output type
    output_types = {
        AgentRole.GRAPH: GraphAnalysis,
        AgentRole.CONTENT: ContentPlan,
        AgentRole.TASK: TaskPlan,
        AgentRole.SYSTEM2: SystemTwoInsight,
        AgentRole.ORCHESTRATOR: OrchestratorPlan,
    }

    output_type = output_types.get(spec.role)

    agent = PydanticAgent(
        model=spec.model,
        system_prompt=spec.system_prompt,
        result_type=output_type,  # type: ignore
    )

    # Register tool functions from the ToolRegistry
    for tool_name in spec.tools:
        tool = tools.get(tool_name)
        if tool:
            @agent.tool
            async def call_tool(ctx: RunContext, name: str = tool_name, **kwargs: Any) -> str:
                """Call a vault tool."""
                result = await tools.call(name, **kwargs)
                return str(result)[:4000]  # Truncate to avoid token limits

    return agent


def create_all_agents(tools: ToolRegistry) -> dict[AgentRole, Any]:
    """Create all specialist agents."""
    agents = {}
    for role, spec in AGENT_SPECS.items():
        if role == AgentRole.VOICE:  # Voice agent is handled separately
            continue
        try:
            agents[role] = create_pydantic_agent(spec, tools)
            logger.info(f"Created agent: {spec.name} ({role.value})")
        except Exception as e:
            logger.warning(f"Failed to create agent {spec.name}: {e}")
    return agents
