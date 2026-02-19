#!/usr/bin/env python3
"""vault-profile.py — Generate a markdown vault profile from graph-extract output.

Produces a comprehensive vault profile document covering:
  - Entity type distribution & schema coverage
  - Link density and graph topology stats
  - Top hubs, orphans, bridges, clusters
  - College-level breakdowns
  - Suggested improvements

Usage:
  python vault-profile.py <vault_dir>                     # print markdown to stdout
  python vault-profile.py <vault_dir> -o profile.md       # save to file
  python vault-profile.py --from-snapshot snapshot.json    # use pre-computed snapshot

Requires: Python 3.8+, PyYAML, graph-extract.py in same directory
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Import graph-extract from same directory
_tools_dir = os.path.dirname(os.path.abspath(__file__))
_ge_path = os.path.join(_tools_dir, 'graph-extract.py')
spec = importlib.util.spec_from_file_location('graph_extract', _ge_path)
graph_extract = importlib.util.module_from_spec(spec)
# Prevent __main__ execution during import
graph_extract.__name__ = 'graph_extract'
sys.modules['graph_extract'] = graph_extract
spec.loader.exec_module(graph_extract)


# ---------------------------------------------------------------------------
# Schema definitions (expected fields per entity type)
# ---------------------------------------------------------------------------

EXPECTED_SCHEMA = {
    'SAQ': {
        'required': ['entityType', 'title', 'exam', 'college', 'year', 'sitting', 'question'],
        'recommended': ['passRate', 'lo.direct', 'saq.direct', 'saq.indirect', 'ec.expected', 'ec.errors'],
        'optional': ['ec.extra', 'elo.indirect', 'Title'],
    },
    'lo': {
        'required': ['entityType', 'college', 'title', 'aliases', 'summary', 'description', 'section'],
        'recommended': ['section.sub', 'topic', 'action', 'complexity', 'type.measurement', 'saq.direct'],
        'optional': ['lo.mapped', 'elo.indirect', 'variation', 'sectionanzca', 'Title'],
    },
    'index': {
        'required': ['entityType', 'Title'],
        'recommended': [],
        'optional': [],
    },
    'concept': {
        'required': ['entityType', 'title', 'college', 'summary', 'description'],
        'recommended': ['aliases', 'section', 'saq.direct', 'topic'],
        'optional': ['lo.mapped', 'complexity', 'action'],
    },
}


# ---------------------------------------------------------------------------
# Profile generator
# ---------------------------------------------------------------------------

class VaultProfiler:
    def __init__(self, snapshot: dict):
        self.snap = snapshot
        self.nodes = snapshot.get('nodes', {})
        self.edges = snapshot.get('edges', [])
        self.summary = snapshot.get('summary', {})

    def generate(self) -> str:
        lines = []
        w = lines.append

        w('# Vault Profile Report')
        w(f'Generated: {self.snap.get("timestamp", "unknown")}')
        w(f'Vault: `{self.snap.get("vault_dir", "unknown")}`')
        w(f'Parse time: {self.snap.get("parse_seconds", "?")}s | Metric time: {self.snap.get("metric_seconds", "?")}s')
        w('')

        self._section_overview(w)
        self._section_entity_types(w)
        self._section_schema_coverage(w)
        self._section_link_density(w)
        self._section_graph_topology(w)
        self._section_top_hubs(w)
        self._section_orphans(w)
        self._section_bridges(w)
        self._section_college_breakdown(w)
        self._section_saq_analysis(w)
        self._section_suggestions(w)

        return '\n'.join(lines)

    def _section_overview(self, w):
        s = self.summary
        w('## Overview')
        w('')
        w(f'| Metric | Value |')
        w(f'|--------|-------|')
        w(f'| Total nodes (files) | {s.get("node_count", 0):,} |')
        w(f'| Phantom nodes (referenced but no file) | {s.get("phantom_count", 0):,} |')
        w(f'| Total edges | {s.get("edge_count", 0):,} |')
        w(f'| Unique edges | {s.get("unique_edge_count", 0):,} |')
        w(f'| Connected components | {s.get("component_count", 0)} |')
        w(f'| Orphan nodes | {s.get("orphan_count", 0)} |')
        w(f'| Bridge nodes | {s.get("bridge_count", 0)} |')
        w(f'| Avg in-degree | {s.get("avg_in_degree", 0)} |')
        w(f'| Avg out-degree | {s.get("avg_out_degree", 0)} |')
        w(f'| Max in-degree | {s.get("max_in_degree", 0)} |')
        w(f'| Max out-degree | {s.get("max_out_degree", 0)} |')
        w(f'| Link density (edges/node) | {s.get("edge_count", 0) / max(s.get("node_count", 1), 1):.1f} |')
        w('')

    def _section_entity_types(self, w):
        dist = self.summary.get('entity_type_distribution', {})
        total = sum(dist.values())
        w('## Entity Type Distribution')
        w('')
        w('| Entity Type | Count | % |')
        w('|-------------|-------|---|')
        for et, cnt in sorted(dist.items(), key=lambda x: -x[1]):
            label = et if et else '(no type)'
            w(f'| {label} | {cnt:,} | {cnt/total*100:.1f}% |')
        w(f'| **Total** | **{total:,}** | **100%** |')
        w('')

    def _section_schema_coverage(self, w):
        w('## Schema Coverage')
        w('')
        w('Coverage of expected frontmatter fields per entity type.')
        w('')

        by_type: Dict[str, list] = collections.defaultdict(list)
        for nid, node in self.nodes.items():
            et = node.get('entityType', '') or '(no type)'
            by_type[et].append(node)

        for et in sorted(by_type.keys(), key=lambda x: -len(by_type[x])):
            nodes_of_type = by_type[et]
            total = len(nodes_of_type)
            schema = EXPECTED_SCHEMA.get(et, {})
            required = schema.get('required', [])
            recommended = schema.get('recommended', [])

            w(f'### {et} ({total:,} nodes)')
            w('')

            if not required and not recommended:
                field_counts: Dict[str, int] = collections.defaultdict(int)
                for node in nodes_of_type:
                    for k in node.get('frontmatter', {}).keys():
                        field_counts[k] += 1
                if field_counts:
                    w('| Field | Present | Coverage |')
                    w('|-------|---------|----------|')
                    for k, cnt in sorted(field_counts.items(), key=lambda x: -x[1])[:15]:
                        bar = self._bar(cnt / total)
                        w(f'| `{k}` | {cnt}/{total} | {bar} {cnt/total*100:.0f}% |')
                    w('')
                continue

            w('| Field | Tier | Present | Coverage |')
            w('|-------|------|---------|----------|')

            all_fields = [(f, 'required') for f in required] + [(f, 'recommended') for f in recommended]
            for field, tier in all_fields:
                cnt = sum(1 for n in nodes_of_type if field in n.get('frontmatter', {}))
                bar = self._bar(cnt / total)
                icon = '\u2705' if cnt == total else ('\u26a0\ufe0f' if cnt / total > 0.7 else '\u274c')
                w(f'| `{field}` | {tier} | {cnt}/{total} | {icon} {bar} {cnt/total*100:.0f}% |')
            w('')

            missing_required = []
            for field in required:
                cnt = sum(1 for n in nodes_of_type if field in n.get('frontmatter', {}))
                if cnt < total:
                    missing = [n['id'] for n in nodes_of_type if field not in n.get('frontmatter', {})][:5]
                    missing_required.append((field, total - cnt, missing))

            if missing_required:
                w(f'**Missing required fields:**')
                for field, cnt, examples in missing_required:
                    ex = ', '.join(f'`{e}`' for e in examples)
                    w(f'- `{field}`: {cnt} nodes missing (e.g. {ex})')
                w('')

    def _section_link_density(self, w):
        w('## Link Density & Edge Types')
        w('')
        edge_dist = self.summary.get('edge_type_distribution', {})
        total_edges = sum(edge_dist.values())
        w('| Edge Type | Count | % | Description |')
        w('|-----------|-------|---|-------------|')
        descriptions = {
            'saq.direct': 'Direct SAQ cross-references',
            'saq.indirect': 'Indirect SAQ cross-references',
            'lo.direct': 'SAQ \u2192 Learning Objective direct links',
            'elo.indirect': 'Equivalent LO indirect mappings',
            'body': 'Wikilinks in markdown body',
            'section': 'Section hierarchy links',
            'lo.mapped': 'LO cross-college mappings',
            'section.sub': 'Sub-section hierarchy links',
            'lo': 'General LO references',
            'lo.indirect': 'Indirect LO references',
            'resources': 'Resource references',
        }
        for et, cnt in sorted(edge_dist.items(), key=lambda x: -x[1]):
            desc = descriptions.get(et, '')
            w(f'| `{et}` | {cnt:,} | {cnt/max(total_edges,1)*100:.1f}% | {desc} |')
        w(f'| **Total** | **{total_edges:,}** | | |')
        w('')

        w('### Links per Entity Type')
        w('')
        by_type: Dict[str, list] = collections.defaultdict(list)
        for nid, node in self.nodes.items():
            et = node.get('entityType', '') or '(no type)'
            by_type[et].append(node)

        w('| Entity Type | Avg In | Avg Out | Max In | Max Out |')
        w('|-------------|--------|---------|--------|---------|')
        for et in sorted(by_type.keys(), key=lambda x: -len(by_type[x])):
            nodes = by_type[et]
            if not nodes:
                continue
            avg_in = sum(n.get('in_degree', 0) for n in nodes) / len(nodes)
            avg_out = sum(n.get('out_degree', 0) for n in nodes) / len(nodes)
            max_in = max(n.get('in_degree', 0) for n in nodes)
            max_out = max(n.get('out_degree', 0) for n in nodes)
            w(f'| {et} | {avg_in:.1f} | {avg_out:.1f} | {max_in} | {max_out} |')
        w('')

    def _section_graph_topology(self, w):
        s = self.summary
        w('## Graph Topology')
        w('')
        comp_sizes = s.get('component_sizes_top10', [])
        w(f'**Connected components:** {s.get("component_count", 0)}')
        w('')
        if comp_sizes:
            w('| Component | Size | % of vault |')
            w('|-----------|------|------------|')
            total = s.get('node_count', 1)
            for i, sz in enumerate(comp_sizes):
                label = 'Main' if i == 0 else f'#{i+1}'
                w(f'| {label} | {sz:,} | {sz/total*100:.1f}% |')
            w('')

        w('### Degree Distribution')
        w('')
        in_degs = [n.get('in_degree', 0) for n in self.nodes.values()]
        out_degs = [n.get('out_degree', 0) for n in self.nodes.values()]

        bins = [(0, 0), (1, 5), (6, 10), (11, 20), (21, 50), (51, 100), (101, 500), (501, 10000)]
        w('| Degree Range | In-degree (nodes) | Out-degree (nodes) |')
        w('|-------------|-------------------|-------------------|')
        for lo, hi in bins:
            in_cnt = sum(1 for d in in_degs if lo <= d <= hi)
            out_cnt = sum(1 for d in out_degs if lo <= d <= hi)
            if in_cnt > 0 or out_cnt > 0:
                label = f'{lo}' if lo == hi else f'{lo}-{hi}'
                w(f'| {label} | {in_cnt} | {out_cnt} |')
        w('')

    def _section_top_hubs(self, w):
        w('## Top Hubs')
        w('')

        w('### By PageRank')
        w('')
        w('| Rank | Node | PageRank | Type | In\u00b0 | Out\u00b0 |')
        w('|------|------|----------|------|-----|------|')
        for i, item in enumerate(self.snap.get('top_pagerank', [])[:20], 1):
            nid, pr = next(iter(item.items()))
            node = self.nodes.get(nid, {})
            et = node.get('entityType', '?')
            in_d = node.get('in_degree', 0)
            out_d = node.get('out_degree', 0)
            w(f'| {i} | `{nid}` | {pr:.6f} | {et} | {in_d} | {out_d} |')
        w('')

        w('### By Hub Score')
        w('')
        w('| Rank | Node | Hub Score | Type | Out\u00b0 |')
        w('|------|------|-----------|------|------|')
        for i, item in enumerate(self.snap.get('top_hub_score', [])[:15], 1):
            nid, hs = next(iter(item.items()))
            node = self.nodes.get(nid, {})
            et = node.get('entityType', '?')
            out_d = node.get('out_degree', 0)
            w(f'| {i} | `{nid}` | {hs:.6f} | {et} | {out_d} |')
        w('')

        w('### By In-Degree (most referenced)')
        w('')
        w('| Rank | Node | In-Degree | Type |')
        w('|------|------|-----------|------|')
        for i, item in enumerate(self.snap.get('top_in_degree', [])[:15], 1):
            nid, deg = next(iter(item.items()))
            node = self.nodes.get(nid, {})
            et = node.get('entityType', '?')
            w(f'| {i} | `{nid}` | {deg} | {et} |')
        w('')

    def _section_orphans(self, w):
        orphans = self.snap.get('orphans', [])
        w('## Orphan Nodes')
        w('')
        w(f'Nodes with no incoming or outgoing edges: **{len(orphans)}**')
        w('')
        if orphans:
            w('| Node | Type | Path |')
            w('|------|------|------|')
            for nid in orphans:
                node = self.nodes.get(nid, {})
                et = node.get('entityType', '?')
                path = node.get('path', '?')
                w(f'| `{nid}` | {et} | `{path}` |')
            w('')

    def _section_bridges(self, w):
        bridges = self.snap.get('bridges', [])
        w('## Bridge Nodes (Articulation Points)')
        w('')
        w(f'Nodes whose removal would disconnect the graph: **{len(bridges)}**')
        w('')
        if bridges:
            w('| Node | Type | In\u00b0 | Out\u00b0 | PageRank |')
            w('|------|------|-----|------|----------|')
            for nid in bridges[:30]:
                node = self.nodes.get(nid, {})
                et = node.get('entityType', '?')
                in_d = node.get('in_degree', 0)
                out_d = node.get('out_degree', 0)
                pr = node.get('pagerank', 0)
                w(f'| `{nid}` | {et} | {in_d} | {out_d} | {pr:.6f} |')
            w('')

    def _section_college_breakdown(self, w):
        w('## College Breakdown')
        w('')

        by_college: Dict[str, Dict[str, int]] = collections.defaultdict(lambda: collections.defaultdict(int))
        for nid, node in self.nodes.items():
            college = node.get('college', '') or '(none)'
            et = node.get('entityType', '') or '(no type)'
            by_college[college][et] += 1

        for college in sorted(by_college.keys()):
            types = by_college[college]
            total = sum(types.values())
            w(f'### {college} ({total:,} nodes)')
            w('')
            w('| Entity Type | Count |')
            w('|-------------|-------|')
            for et, cnt in sorted(types.items(), key=lambda x: -x[1]):
                w(f'| {et} | {cnt:,} |')
            w('')

    def _section_saq_analysis(self, w):
        w('## SAQ Analysis')
        w('')

        saqs = [n for n in self.nodes.values() if n.get('entityType') == 'SAQ']
        if not saqs:
            w('No SAQ nodes found.')
            w('')
            return

        pass_rates = []
        for n in saqs:
            pr = n.get('frontmatter', {}).get('passRate')
            if pr is not None:
                try:
                    pass_rates.append(float(pr))
                except (ValueError, TypeError):
                    pass

        if pass_rates:
            pass_rates.sort()
            avg_pr = sum(pass_rates) / len(pass_rates)
            median_pr = pass_rates[len(pass_rates) // 2]
            w(f'**Pass Rate Stats** (n={len(pass_rates)}):')
            w(f'- Mean: {avg_pr:.1f}%')
            w(f'- Median: {median_pr:.1f}%')
            w(f'- Min: {min(pass_rates):.0f}% | Max: {max(pass_rates):.0f}%')
            w(f'- <30%: {sum(1 for p in pass_rates if p < 30)} SAQs')
            w(f'- 30-50%: {sum(1 for p in pass_rates if 30 <= p < 50)} SAQs')
            w(f'- 50-70%: {sum(1 for p in pass_rates if 50 <= p < 70)} SAQs')
            w(f'- >70%: {sum(1 for p in pass_rates if p >= 70)} SAQs')
            w('')

        with_lo = sum(1 for n in saqs if n.get('frontmatter', {}).get('lo.direct'))
        with_saq_direct = sum(1 for n in saqs if n.get('frontmatter', {}).get('saq.direct'))
        w(f'**LO Coverage:**')
        w(f'- SAQs with `lo.direct`: {with_lo}/{len(saqs)} ({with_lo/len(saqs)*100:.0f}%)')
        w(f'- SAQs with `saq.direct`: {with_saq_direct}/{len(saqs)} ({with_saq_direct/len(saqs)*100:.0f}%)')
        w('')

        by_year: Dict[int, int] = collections.defaultdict(int)
        for n in saqs:
            yr = n.get('frontmatter', {}).get('year')
            if yr is not None:
                try:
                    by_year[int(yr)] += 1
                except (ValueError, TypeError):
                    pass

        if by_year:
            w('**SAQs by Year:**')
            w('')
            w('| Year | Count |')
            w('|------|-------|')
            for yr in sorted(by_year.keys()):
                w(f'| {yr} | {by_year[yr]} |')
            w('')

    def _section_suggestions(self, w):
        w('## Suggested Improvements')
        w('')

        suggestions = []
        s = self.summary

        orphan_count = s.get('orphan_count', 0)
        if orphan_count > 0:
            suggestions.append(
                f'\u26a0\ufe0f **{orphan_count} orphan nodes** have no links in or out. '
                f'Consider linking them into the graph or removing if obsolete.'
            )

        phantom_count = s.get('phantom_count', 0)
        if phantom_count > 0:
            suggestions.append(
                f'\u274c **{phantom_count} phantom nodes** are referenced by links but have no corresponding file. '
                f'These are broken links that need resolution.'
            )

        by_type: Dict[str, list] = collections.defaultdict(list)
        for nid, node in self.nodes.items():
            et = node.get('entityType', '')
            by_type[et].append(node)

        for et, schema in EXPECTED_SCHEMA.items():
            nodes_of_type = by_type.get(et, [])
            if not nodes_of_type:
                continue
            total = len(nodes_of_type)
            for field in schema.get('required', []):
                cnt = sum(1 for n in nodes_of_type if field in n.get('frontmatter', {}))
                gap = total - cnt
                if gap > 0:
                    suggestions.append(
                        f'📝 **{et}**: `{field}` missing from {gap} nodes ({gap/total*100:.0f}%). '
                        f'This is a required field.'
                    )
            for field in schema.get('recommended', []):
                cnt = sum(1 for n in nodes_of_type if field in n.get('frontmatter', {}))
                gap = total - cnt
                pct = gap / total * 100
                if pct > 30:
                    suggestions.append(
                        f'💡 **{et}**: `{field}` only present in {cnt/total*100:.0f}% of nodes. '
                        f'Consider enriching the remaining {gap} nodes.'
                    )

        comp_count = s.get('component_count', 0)
        if comp_count > 1:
            sizes = s.get('component_sizes_top10', [])
            small = sum(1 for sz in sizes[1:] if sz < 10)
            suggestions.append(
                f'🔗 **{comp_count} disconnected components** detected. '
                f'{small} small components could likely be connected to the main graph.'
            )

        bridge_count = s.get('bridge_count', 0)
        if bridge_count > 0:
            suggestions.append(
                f'🌉 **{bridge_count} bridge nodes** are single points of failure in the graph. '
                f'Adding redundant links around these nodes would improve graph resilience.'
            )

        saqs = by_type.get('SAQ', [])
        if saqs:
            with_lo = sum(1 for n in saqs if n.get('frontmatter', {}).get('lo.direct'))
            pct = with_lo / len(saqs) * 100
            if pct < 80:
                suggestions.append(
                    f'🎯 **SAQ \u2192 LO mapping**: Only {pct:.0f}% of SAQs have `lo.direct` links. '
                    f'Mapping the remaining {len(saqs) - with_lo} SAQs to learning objectives would '
                    f'greatly improve curriculum coverage analysis.'
                )

        if suggestions:
            for i, s in enumerate(suggestions, 1):
                w(f'{i}. {s}')
                w('')
        else:
            w('\u2705 No major issues detected. Vault graph is well-connected and schema coverage is good.')
            w('')

    @staticmethod
    def _bar(pct: float, width: int = 10) -> str:
        filled = round(pct * width)
        return '\u2588' * filled + '\u2591' * (width - filled)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Generate vault profile markdown')
    parser.add_argument('vault_dir', nargs='?', help='Path to vault directory')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')
    parser.add_argument('--from-snapshot', help='Use pre-computed snapshot JSON instead of scanning vault')
    args = parser.parse_args()

    if args.from_snapshot:
        with open(args.from_snapshot) as f:
            snapshot = json.load(f)
    elif args.vault_dir:
        if not os.path.isdir(args.vault_dir):
            sys.exit(f"Not a directory: {args.vault_dir}")
        print(f"Scanning vault: {args.vault_dir}", file=sys.stderr)
        g = graph_extract.VaultGraph(args.vault_dir)
        g.build()
        metrics = g.compute_metrics()
        snapshot = g.to_snapshot(metrics)
    else:
        parser.print_help()
        sys.exit(1)

    profiler = VaultProfiler(snapshot)
    md = profiler.generate()

    if args.output:
        with open(args.output, 'w') as f:
            f.write(md)
        print(f"Profile written to {args.output}", file=sys.stderr)
    else:
        print(md)


if __name__ == '__main__':
    main()
