#!/usr/bin/env python3
"""graph-extract.py — Obsidian vault graph extraction, metrics & diff.

Extracts a complete knowledge graph from an Obsidian vault including:
  - Full frontmatter (YAML) per node
  - Wikilink edges (body + frontmatter cross-refs)
  - Graph metrics: in/out degree, PageRank, hub score, components, clusters
  - Structural analysis: orphans, bridges, hubs
  - Snapshot diffing for before/after comparison

Usage:
  python graph-extract.py <vault_dir>                       # extract graph JSON to stdout
  python graph-extract.py <vault_dir> -o snapshot.json      # save snapshot
  python graph-extract.py --diff before.json after.json     # diff two snapshots
  python graph-extract.py <vault_dir> --summary             # compact summary only

Requires: Python 3.8+, PyYAML
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WIKILINK_RE = re.compile(r'\[\[([^\]|#]+?)(?:#[^\]|]*)?(?:\|[^\]]*)?]]')
FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---', re.DOTALL)

# Frontmatter keys that contain cross-references (wikilink lists)
CROSSREF_KEYS = {
    'saq.direct', 'saq.indirect',
    'lo.direct', 'lo.indirect',
    'elo.indirect', 'elo.direct',
    'lo.mapped', 'lo',
    'section', 'section.sub',
    'resources',
}

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from markdown text."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1))
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def extract_wikilinks_from_value(value: Any) -> List[str]:
    """Recursively extract wikilink targets from a frontmatter value."""
    links = []
    if isinstance(value, str):
        links.extend(WIKILINK_RE.findall(value))
    elif isinstance(value, list):
        for item in value:
            links.extend(extract_wikilinks_from_value(item))
    elif isinstance(value, dict):
        for v in value.values():
            links.extend(extract_wikilinks_from_value(v))
    return links


def extract_body_wikilinks(text: str) -> List[str]:
    """Extract wikilinks from body (after frontmatter)."""
    m = FRONTMATTER_RE.match(text)
    body = text[m.end():] if m else text
    return WIKILINK_RE.findall(body)


def node_id_from_path(path: str, vault_root: str) -> str:
    """Derive node ID from file path (stem, no extension)."""
    return Path(path).stem


def resolve_link_target(raw: str) -> str:
    """Normalize a wikilink target to a node ID."""
    return Path(raw.strip()).stem


# ---------------------------------------------------------------------------
# Graph building
# ---------------------------------------------------------------------------

class VaultGraph:
    """Full vault graph with metadata."""

    def __init__(self, vault_dir: str):
        self.vault_dir = os.path.abspath(vault_dir)
        self.nodes: Dict[str, dict] = {}
        self.edges: List[dict] = []
        self.adjacency: Dict[str, Set[str]] = collections.defaultdict(set)
        self.reverse_adj: Dict[str, Set[str]] = collections.defaultdict(set)
        self._alias_map: Dict[str, str] = {}
        self._parse_time = 0.0
        self._metric_time = 0.0

    def build(self):
        t0 = time.monotonic()
        md_files = []
        for root, _dirs, files in os.walk(self.vault_dir):
            for fn in files:
                if fn.endswith('.md'):
                    md_files.append(os.path.join(root, fn))

        for fpath in md_files:
            self._parse_file(fpath)

        resolved_edges = []
        for e in self.edges:
            target = self._resolve(e['target'])
            e['target'] = target
            resolved_edges.append(e)
            self.adjacency[e['source']].add(target)
            self.reverse_adj[target].add(e['source'])
        self.edges = resolved_edges

        self._parse_time = time.monotonic() - t0

    def _parse_file(self, fpath: str):
        nid = node_id_from_path(fpath, self.vault_dir)
        rel_path = os.path.relpath(fpath, self.vault_dir)

        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
        except OSError:
            return

        fm = parse_frontmatter(text)

        self.nodes[nid] = {
            'id': nid,
            'path': rel_path,
            'entityType': fm.get('entityType', ''),
            'title': fm.get('title', nid),
            'college': fm.get('college', ''),
            'frontmatter': fm,
        }

        aliases = fm.get('aliases', [])
        if isinstance(aliases, list):
            for a in aliases:
                self._alias_map[str(a).strip()] = nid
        self._alias_map[nid] = nid

        for key in CROSSREF_KEYS:
            val = fm.get(key)
            if val is None:
                continue
            targets = extract_wikilinks_from_value(val)
            for raw in targets:
                tid = resolve_link_target(raw)
                self.edges.append({
                    'source': nid,
                    'target': tid,
                    'type': 'frontmatter',
                    'key': key,
                })

        body_links = extract_body_wikilinks(text)
        for raw in body_links:
            tid = resolve_link_target(raw)
            self.edges.append({
                'source': nid,
                'target': tid,
                'type': 'body',
                'key': '',
            })

    def _resolve(self, target: str) -> str:
        return self._alias_map.get(target, target)

    def compute_metrics(self) -> dict:
        t0 = time.monotonic()
        all_ids = set(self.nodes.keys())
        phantom_ids = set()
        for e in self.edges:
            if e['target'] not in all_ids:
                phantom_ids.add(e['target'])

        all_node_ids = all_ids | phantom_ids

        in_deg = {nid: len(self.reverse_adj.get(nid, set())) for nid in all_node_ids}
        out_deg = {nid: len(self.adjacency.get(nid, set())) for nid in all_node_ids}

        pr = self._pagerank(all_node_ids, 0.85, 40)

        components = self._connected_components(all_node_ids)
        comp_map = {}
        for i, comp in enumerate(components):
            for nid in comp:
                comp_map[nid] = i

        hub_score = {}
        for nid in all_node_ids:
            neighbors = self.adjacency.get(nid, set())
            if neighbors:
                avg_pr = sum(pr.get(n, 0) for n in neighbors) / len(neighbors)
                hub_score[nid] = len(neighbors) * avg_pr
            else:
                hub_score[nid] = 0.0

        orphans = [nid for nid in all_ids
                   if in_deg.get(nid, 0) == 0 and out_deg.get(nid, 0) == 0]

        bridges = self._find_bridges(all_ids)

        cluster_sizes = collections.Counter(comp_map[nid] for nid in all_ids)

        self._metric_time = time.monotonic() - t0

        return {
            'node_count': len(all_ids),
            'phantom_count': len(phantom_ids),
            'edge_count': len(self.edges),
            'unique_edge_count': len(set((e['source'], e['target']) for e in self.edges)),
            'in_degree': in_deg,
            'out_degree': out_deg,
            'pagerank': pr,
            'hub_score': hub_score,
            'component_id': comp_map,
            'component_count': len(components),
            'component_sizes': sorted(cluster_sizes.values(), reverse=True),
            'orphans': sorted(orphans),
            'bridges': sorted(bridges),
            'phantom_nodes': sorted(phantom_ids),
        }

    def _pagerank(self, node_ids: set, damping: float, iterations: int) -> dict:
        n = len(node_ids)
        if n == 0:
            return {}
        pr = {nid: 1.0 / n for nid in node_ids}
        base = (1.0 - damping) / n

        for _ in range(iterations):
            new_pr = {}
            dangling = sum(pr[nid] for nid in node_ids if not self.adjacency.get(nid))
            dangling_share = damping * dangling / n

            for nid in node_ids:
                rank = base + dangling_share
                for src in self.reverse_adj.get(nid, set()):
                    out_count = len(self.adjacency.get(src, set()))
                    if out_count > 0:
                        rank += damping * pr.get(src, 0) / out_count
                new_pr[nid] = rank
            pr = new_pr
        return pr

    def _connected_components(self, node_ids: set) -> List[Set[str]]:
        visited = set()
        components = []
        for start in node_ids:
            if start in visited:
                continue
            comp = set()
            stack = [start]
            while stack:
                nid = stack.pop()
                if nid in visited:
                    continue
                visited.add(nid)
                comp.add(nid)
                for neighbor in self.adjacency.get(nid, set()):
                    if neighbor not in visited and neighbor in node_ids:
                        stack.append(neighbor)
                for neighbor in self.reverse_adj.get(nid, set()):
                    if neighbor not in visited and neighbor in node_ids:
                        stack.append(neighbor)
            if comp:
                components.append(comp)
        return components

    def _find_bridges(self, node_ids: set) -> List[str]:
        """Find articulation points using iterative DFS."""
        adj_undirected: Dict[str, Set[str]] = collections.defaultdict(set)
        for nid in node_ids:
            for nb in self.adjacency.get(nid, set()):
                if nb in node_ids:
                    adj_undirected[nid].add(nb)
                    adj_undirected[nb].add(nid)
            for nb in self.reverse_adj.get(nid, set()):
                if nb in node_ids:
                    adj_undirected[nid].add(nb)
                    adj_undirected[nb].add(nid)

        disc = {}
        low = {}
        parent = {}
        ap = set()
        timer = [0]

        def dfs_iterative(start):
            stack = [(start, iter(adj_undirected.get(start, set())), True)]
            disc[start] = low[start] = timer[0]
            timer[0] += 1
            parent[start] = None
            child_count = collections.defaultdict(int)

            while stack:
                node, neighbors, is_root_flag = stack[-1]
                try:
                    nb = next(neighbors)
                    if nb not in disc:
                        parent[nb] = node
                        child_count[node] += 1
                        disc[nb] = low[nb] = timer[0]
                        timer[0] += 1
                        stack.append((nb, iter(adj_undirected.get(nb, set())), False))
                    elif nb != parent.get(node):
                        low[node] = min(low[node], disc[nb])
                except StopIteration:
                    stack.pop()
                    if stack:
                        prev_node = stack[-1][0]
                        low[prev_node] = min(low[prev_node], low[node])
                        if parent[prev_node] is None:
                            if child_count[prev_node] > 1:
                                ap.add(prev_node)
                        else:
                            if low[node] >= disc[prev_node]:
                                ap.add(prev_node)

        for nid in node_ids:
            if nid not in disc:
                dfs_iterative(nid)

        return list(ap)

    def to_snapshot(self, metrics: dict) -> dict:
        """Produce a full JSON-serializable snapshot."""
        node_metrics = {}
        for nid, node in self.nodes.items():
            node_metrics[nid] = {
                **node,
                'in_degree': metrics['in_degree'].get(nid, 0),
                'out_degree': metrics['out_degree'].get(nid, 0),
                'pagerank': round(metrics['pagerank'].get(nid, 0), 8),
                'hub_score': round(metrics['hub_score'].get(nid, 0), 8),
                'component_id': metrics['component_id'].get(nid, -1),
                'is_orphan': nid in metrics['orphans'],
                'is_bridge': nid in metrics['bridges'],
            }

        real_nodes = list(self.nodes.keys())
        top_pagerank = sorted(real_nodes, key=lambda n: metrics['pagerank'].get(n, 0), reverse=True)[:30]
        top_hub = sorted(real_nodes, key=lambda n: metrics['hub_score'].get(n, 0), reverse=True)[:30]
        top_in_degree = sorted(real_nodes, key=lambda n: metrics['in_degree'].get(n, 0), reverse=True)[:30]
        top_out_degree = sorted(real_nodes, key=lambda n: metrics['out_degree'].get(n, 0), reverse=True)[:30]

        type_dist = collections.Counter(n.get('entityType', '') for n in self.nodes.values())
        edge_type_dist = collections.Counter(e['key'] or 'body' for e in self.edges)

        return {
            'vault_dir': self.vault_dir,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'parse_seconds': round(self._parse_time, 3),
            'metric_seconds': round(self._metric_time, 3),
            'summary': {
                'node_count': metrics['node_count'],
                'phantom_count': metrics['phantom_count'],
                'edge_count': metrics['edge_count'],
                'unique_edge_count': metrics['unique_edge_count'],
                'component_count': metrics['component_count'],
                'component_sizes_top10': metrics['component_sizes'][:10],
                'orphan_count': len(metrics['orphans']),
                'bridge_count': len(metrics['bridges']),
                'entity_type_distribution': dict(type_dist.most_common()),
                'edge_type_distribution': dict(edge_type_dist.most_common()),
                'avg_in_degree': round(sum(metrics['in_degree'].get(n, 0) for n in real_nodes) / max(len(real_nodes), 1), 2),
                'avg_out_degree': round(sum(metrics['out_degree'].get(n, 0) for n in real_nodes) / max(len(real_nodes), 1), 2),
                'max_in_degree': max((metrics['in_degree'].get(n, 0) for n in real_nodes), default=0),
                'max_out_degree': max((metrics['out_degree'].get(n, 0) for n in real_nodes), default=0),
            },
            'top_pagerank': [{nid: round(metrics['pagerank'].get(nid, 0), 6)} for nid in top_pagerank],
            'top_hub_score': [{nid: round(metrics['hub_score'].get(nid, 0), 6)} for nid in top_hub],
            'top_in_degree': [{nid: metrics['in_degree'].get(nid, 0)} for nid in top_in_degree],
            'top_out_degree': [{nid: metrics['out_degree'].get(nid, 0)} for nid in top_out_degree],
            'orphans': metrics['orphans'],
            'bridges': metrics['bridges'][:50],
            'nodes': node_metrics,
            'edges': self.edges,
        }

    def to_summary(self, metrics: dict) -> dict:
        """Compact summary without full node/edge lists."""
        snap = self.to_snapshot(metrics)
        del snap['nodes']
        del snap['edges']
        return snap


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------

def diff_snapshots(before: dict, after: dict) -> dict:
    """Produce a structured diff between two graph snapshots."""
    b_nodes = set(before.get('nodes', {}).keys())
    a_nodes = set(after.get('nodes', {}).keys())

    added_nodes = sorted(a_nodes - b_nodes)
    removed_nodes = sorted(b_nodes - a_nodes)
    common_nodes = b_nodes & a_nodes

    b_edges = set((e['source'], e['target'], e.get('key', '')) for e in before.get('edges', []))
    a_edges = set((e['source'], e['target'], e.get('key', '')) for e in after.get('edges', []))

    added_edges = sorted(a_edges - b_edges)
    removed_edges = sorted(b_edges - a_edges)

    metric_changes = []
    for nid in sorted(common_nodes):
        bn = before['nodes'][nid]
        an = after['nodes'][nid]
        changes = {}
        for key in ('in_degree', 'out_degree', 'pagerank', 'hub_score', 'component_id', 'is_orphan', 'is_bridge'):
            bv = bn.get(key)
            av = an.get(key)
            if bv != av:
                changes[key] = {'before': bv, 'after': av}
        fm_changes = {}
        bfm = bn.get('frontmatter', {})
        afm = an.get('frontmatter', {})
        all_keys = set(list(bfm.keys()) + list(afm.keys()))
        for k in all_keys:
            if bfm.get(k) != afm.get(k):
                fm_changes[k] = {'before': bfm.get(k), 'after': afm.get(k)}
        if changes or fm_changes:
            entry = {'id': nid}
            if changes:
                entry['metric_changes'] = changes
            if fm_changes:
                entry['frontmatter_changes'] = fm_changes
            metric_changes.append(entry)

    bs = before.get('summary', {})
    as_ = after.get('summary', {})
    summary_delta = {}
    for k in set(list(bs.keys()) + list(as_.keys())):
        bv = bs.get(k)
        av = as_.get(k)
        if isinstance(bv, (int, float)) and isinstance(av, (int, float)):
            summary_delta[k] = {'before': bv, 'after': av, 'delta': round(av - bv, 4)}
        elif bv != av:
            summary_delta[k] = {'before': bv, 'after': av}

    return {
        'before_timestamp': before.get('timestamp', ''),
        'after_timestamp': after.get('timestamp', ''),
        'summary_delta': summary_delta,
        'added_nodes': added_nodes,
        'removed_nodes': removed_nodes,
        'added_node_count': len(added_nodes),
        'removed_node_count': len(removed_nodes),
        'added_edges': [{'source': s, 'target': t, 'key': k} for s, t, k in added_edges],
        'removed_edges': [{'source': s, 'target': t, 'key': k} for s, t, k in removed_edges],
        'added_edge_count': len(added_edges),
        'removed_edge_count': len(removed_edges),
        'node_changes': metric_changes,
        'changed_node_count': len(metric_changes),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Obsidian vault graph extraction & diff')
    parser.add_argument('vault_dir', nargs='?', help='Path to vault directory')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')
    parser.add_argument('--summary', action='store_true', help='Compact summary (no full node/edge lists)')
    parser.add_argument('--diff', nargs=2, metavar=('BEFORE', 'AFTER'),
                        help='Diff two snapshot JSON files')
    parser.add_argument('--indent', type=int, default=2, help='JSON indent (0=compact)')
    args = parser.parse_args()

    if args.diff:
        with open(args.diff[0]) as f:
            before = json.load(f)
        with open(args.diff[1]) as f:
            after = json.load(f)
        result = diff_snapshots(before, after)
    elif args.vault_dir:
        if not os.path.isdir(args.vault_dir):
            sys.exit(f"Not a directory: {args.vault_dir}")
        graph = VaultGraph(args.vault_dir)
        graph.build()
        metrics = graph.compute_metrics()
        if args.summary:
            result = graph.to_summary(metrics)
        else:
            result = graph.to_snapshot(metrics)
    else:
        parser.print_help()
        sys.exit(1)

    indent = args.indent if args.indent > 0 else None
    output = json.dumps(result, indent=indent, default=str)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Written to {args.output} ({len(output):,} bytes)", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
