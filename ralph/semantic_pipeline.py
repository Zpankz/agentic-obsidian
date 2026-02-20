"""Semantic mapping pipeline: graph analytics → mdbase types → mtn tasks.

Maps graph-computed properties to actionable study tasks:
  - cluster_id → curriculum section grouping
  - delta_class → study priority tier
  - priority_score → mtn task priority
  - Delta-Miss nodes → auto-generated study tasks
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("ralph.semantic_pipeline")

GKG_PATH = Path("/home/exedev/gkg")
SNAPSHOT_PATH = Path("/home/exedev/agentic-obsidian/snapshots/gkg-latest.json")


@dataclass
class StudyTarget:
    """A study target derived from graph analysis."""
    path: str
    title: str
    entity_type: str
    priority: str  # high, normal, low
    reason: str
    related_saqs: list[str]
    pass_rate: float | None = None
    cluster: str = ""
    pagerank: float = 0.0


def load_snapshot() -> dict:
    """Load the latest graph snapshot."""
    with open(SNAPSHOT_PATH) as f:
        return json.load(f)


def identify_delta_miss_nodes(snapshot: dict) -> list[StudyTarget]:
    """Find high-priority study targets from graph analysis.
    
    Delta-Miss criteria:
      - LO nodes with low-pass-rate SAQs (< 40%)
      - LO nodes with high pagerank but low confidence
      - SAQ nodes with passRate < 40%
      - Nodes with high in_degree but stale content
    """
    targets = []
    nodes = snapshot.get("nodes", [])
    
    for n in nodes:
        fm = n.get("fm", {})
        entity = fm.get("entityType", "")
        path = n.get("path", "")
        basename = n.get("basename", "")
        
        # SAQ with low pass rate
        if entity == "SAQ" and isinstance(fm.get("passRate"), (int, float)):
            pr = fm["passRate"]
            if pr < 40:
                targets.append(StudyTarget(
                    path=path,
                    title=fm.get("title", basename) if isinstance(fm.get("title"), str) else basename,
                    entity_type="SAQ",
                    priority="high" if pr < 25 else "normal",
                    reason=f"Low pass rate: {pr}%",
                    related_saqs=[path],
                    pass_rate=pr,
                    cluster=fm.get("cluster_id", ""),
                    pagerank=fm.get("pagerank", 0),
                ))
        
        # LO with many SAQ links but high staleness
        if entity == "lo":
            saq_count = len(fm.get("saq.direct", []))
            staleness = fm.get("staleness_days", 0)
            pagerank = fm.get("pagerank", 0)
            
            if saq_count >= 5 and staleness > 30 and pagerank > 0.001:
                targets.append(StudyTarget(
                    path=path,
                    title=fm.get("title", basename),
                    entity_type="lo",
                    priority="high",
                    reason=f"High-pagerank LO ({pagerank:.4f}) with {saq_count} SAQs, stale {staleness}d",
                    related_saqs=[str(s) for s in fm.get("saq.direct", [])[:5]],
                    cluster=fm.get("cluster_id", ""),
                    pagerank=pagerank,
                ))
    
    # Sort by priority then pagerank
    targets.sort(key=lambda t: (0 if t.priority == "high" else 1, -t.pagerank))
    return targets


def generate_mtn_tasks(targets: list[StudyTarget], limit: int = 20) -> list[dict]:
    """Convert study targets into mtn task specifications."""
    tasks = []
    for t in targets[:limit]:
        task = {
            "title": f"Study: {t.title[:80]}",
            "priority": t.priority,
            "contexts": [t.entity_type, t.cluster] if t.cluster else [t.entity_type],
            "projects": [f"[[{t.path}]]"],
            "tags": ["task", "study", "auto-generated"],
            "description": t.reason,
        }
        if t.pass_rate is not None:
            task["description"] += f" | Pass rate: {t.pass_rate}%"
        tasks.append(task)
    return tasks


def create_mtn_task(task: dict) -> str | None:
    """Create a task via mtn CLI."""
    try:
        cmd = ["mtn", "create", task["title"]]
        if task.get("priority") == "high":
            cmd.extend(["--priority", "high"])
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
            cwd=str(GKG_PATH)
        )
        if result.returncode == 0:
            return result.stdout.strip()
        logger.warning(f"mtn create failed: {result.stderr}")
        return None
    except Exception as e:
        logger.warning(f"mtn create error: {e}")
        return None


def run_pipeline(limit: int = 20, dry_run: bool = True) -> dict:
    """Execute the full semantic mapping pipeline.
    
    Returns summary of identified targets and created tasks.
    """
    snapshot = load_snapshot()
    targets = identify_delta_miss_nodes(snapshot)
    tasks = generate_mtn_tasks(targets, limit=limit)
    
    created = []
    if not dry_run:
        for task in tasks:
            task_id = create_mtn_task(task)
            if task_id:
                created.append(task_id)
    
    return {
        "total_targets": len(targets),
        "high_priority": sum(1 for t in targets if t.priority == "high"),
        "tasks_generated": len(tasks),
        "tasks_created": len(created) if not dry_run else "dry_run",
        "top_targets": [
            {"path": t.path, "reason": t.reason, "priority": t.priority}
            for t in targets[:10]
        ],
    }


if __name__ == "__main__":
    import sys
    dry = "--execute" not in sys.argv
    result = run_pipeline(dry_run=dry)
    print(json.dumps(result, indent=2))
