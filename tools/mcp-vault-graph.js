#!/usr/bin/env node
/**
 * mcp-vault-graph.js — HTTP MCP server for vault graph analytics + diff.
 * 
 * Wraps: graph-extract.py, obaq, treemd, obsidian CLI, turbovault
 * Provides nuanced graph diff calculations with automatic context injection.
 * 
 * Endpoints:
 *   POST /mcp — MCP JSON-RPC (tools/list, tools/call)
 *   GET /health
 * 
 * Port: 3100 (configurable via PORT env)
 */
const http = require('http');
const { execSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const PORT = parseInt(process.env.PORT || '3100');
const GKG_VAULT = process.env.GKG_VAULT || '/home/exedev/gkg';
const PKG_VAULT = process.env.PKG_VAULT || '/home/exedev/pkg';
const TOOLS_DIR = path.dirname(__filename);
const GRAPH_SCRIPT = path.join(TOOLS_DIR, 'graph-extract.py');
const SNAPSHOTS_DIR = '/home/exedev/agentic-obsidian/snapshots';

// Ensure snapshots dir exists
try { fs.mkdirSync(SNAPSHOTS_DIR, { recursive: true }); } catch(e) {}

// ── Helper: run command ─────────────────────────────────────────────
function run(cmd, opts = {}) {
  try {
    return execSync(cmd, { 
      encoding: 'utf8', 
      timeout: opts.timeout || 120000,
      maxBuffer: 50 * 1024 * 1024,
      env: { ...process.env, DISPLAY: ':99' },
    }).trim();
  } catch(e) {
    return JSON.stringify({ error: e.message, stderr: (e.stderr || '').slice(0, 500) });
  }
}

function runJSON(cmd, opts) {
  const out = run(cmd, opts);
  try { return JSON.parse(out); }
  catch(e) { return { error: 'parse_error', raw: out.slice(0, 1000) }; }
}

function vaultPath(name) {
  if (name === 'pkg') return PKG_VAULT;
  if (name === 'gkg') return GKG_VAULT;
  return GKG_VAULT; // default
}

// ── Snapshot cache ───────────────────────────────────────────────────
const snapshotCache = {};

function getLatestSnapshot(vault) {
  const vp = vaultPath(vault);
  const tag = path.basename(vp);
  const snapFile = path.join(SNAPSHOTS_DIR, `${tag}-latest.json`);
  if (fs.existsSync(snapFile)) {
    try { return JSON.parse(fs.readFileSync(snapFile, 'utf8')); } catch(e) {}
  }
  return null;
}

function saveSnapshot(vault, snap) {
  const vp = vaultPath(vault);
  const tag = path.basename(vp);
  const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  
  // Save timestamped
  const tsFile = path.join(SNAPSHOTS_DIR, `${tag}-${ts}.json`);
  fs.writeFileSync(tsFile, JSON.stringify(snap));
  
  // Save as latest
  const latestFile = path.join(SNAPSHOTS_DIR, `${tag}-latest.json`);
  
  // Rotate: if latest exists, rename to previous
  if (fs.existsSync(latestFile)) {
    const prevFile = path.join(SNAPSHOTS_DIR, `${tag}-previous.json`);
    try { fs.copyFileSync(latestFile, prevFile); } catch(e) {}
  }
  fs.writeFileSync(latestFile, JSON.stringify(snap));
  return tsFile;
}

// ── Tool Implementations ─────────────────────────────────────────────
const TOOLS = {
  // ── Graph Analytics ───────────────────────────────────────
  'graph_snapshot': {
    description: 'Take a full graph snapshot of a vault. Computes PageRank, hub scores, components, orphans. Returns stats + top nodes (full node list excluded by default for token efficiency).',
    inputSchema: {
      type: 'object',
      properties: {
        vault: { type: 'string', description: 'Vault name: gkg or pkg', default: 'gkg' },
        include_nodes: { type: 'boolean', description: 'Include full node list (large!)', default: false },
      },
    },
    handler: (args) => {
      const vault = args.vault || 'gkg';
      const flag = args.include_nodes ? '' : '--summary';
      const snap = runJSON(`python3 ${GRAPH_SCRIPT} ${vaultPath(vault)} ${flag}`, { timeout: 180000 });
      if (!snap.error) saveSnapshot(vault, snap);
      return snap;
    },
  },

  'graph_diff': {
    description: 'Compute diff between current vault state and last snapshot. Shows added/removed nodes, content changes, link topology shifts, PageRank delta. Essential for understanding what changed.',
    inputSchema: {
      type: 'object',
      properties: {
        vault: { type: 'string', description: 'Vault name', default: 'gkg' },
      },
    },
    handler: (args) => {
      const vault = args.vault || 'gkg';
      const vp = vaultPath(vault);
      const tag = path.basename(vp);
      
      // Get previous snapshot
      const prevFile = path.join(SNAPSHOTS_DIR, `${tag}-previous.json`);
      if (!fs.existsSync(prevFile)) {
        // No previous — take first snapshot
        const snap = runJSON(`python3 ${GRAPH_SCRIPT} ${vp}`, { timeout: 180000 });
        if (!snap.error) saveSnapshot(vault, snap);
        return { message: 'First snapshot taken. Run again after changes to see diff.', stats: snap.summary };
      }
      
      // Take new snapshot
      const newSnap = runJSON(`python3 ${GRAPH_SCRIPT} ${vp}`, { timeout: 180000 });
      if (newSnap.error) return newSnap;
      
      const newFile = path.join(SNAPSHOTS_DIR, `${tag}-new-tmp.json`);
      fs.writeFileSync(newFile, JSON.stringify(newSnap));
      
      const diff = runJSON(`python3 ${GRAPH_SCRIPT} --diff ${prevFile} ${newFile}`);
      
      // Save new as latest (rotating previous)
      saveSnapshot(vault, newSnap);
      try { fs.unlinkSync(newFile); } catch(e) {}
      
      return diff;
    },
  },

  'graph_context': {
    description: 'Generate agent-injectable context from vault graph. Optionally filtered by query. Returns compact structured data optimized for LLM consumption.',
    inputSchema: {
      type: 'object',
      properties: {
        vault: { type: 'string', default: 'gkg' },
        query: { type: 'string', description: 'Focus query (e.g. "pharmacology", "cardiovascular")' },
        max_nodes: { type: 'number', default: 50 },
      },
    },
    handler: (args) => {
      const vault = args.vault || 'gkg';
      const q = args.query ? `--query "${args.query.replace(/"/g, '\\"')}"` : '';
      const n = args.max_nodes || 50;
      // Context = snapshot summary + query-filtered node list
      const snap = runJSON(`python3 ${GRAPH_SCRIPT} ${vaultPath(vault)} --summary`, { timeout: 180000 });
      if (snap.error) return snap;
      // If query, filter top_pagerank by query match
      let focus = snap.top_pagerank || [];
      if (args.query) {
        const qLower = args.query.toLowerCase();
        // Get full snapshot for query filtering
        const full = runJSON(`python3 ${GRAPH_SCRIPT} ${vaultPath(vault)}`, { timeout: 180000 });
        if (full.nodes) {
          focus = full.nodes
            .filter(nd => {
              const id = (nd.id || '').toLowerCase();
              const t = (nd.title || '').toLowerCase();
              const sec = (nd.section || '').toLowerCase();
              return id.includes(qLower) || t.includes(qLower) || sec.includes(qLower);
            })
            .sort((a, b) => (b.pagerank || 0) - (a.pagerank || 0))
            .slice(0, n)
            .map(nd => ({ id: nd.id, type: nd.entity_type, pagerank: nd.pagerank, in_degree: nd.in_degree, title: (nd.title || '').slice(0, 120) }));
        }
      }
      return { vault: path.basename(vaultPath(vault)), stats: snap.summary, focus_nodes: focus.slice(0, n), top_hubs: snap.top_hubs, orphans: snap.orphans };
    },
  },

  'graph_profile': {
    description: 'Generate comprehensive vault profile in markdown. Entity types, schema coverage, top hubs, PageRank leaders, orphans, component analysis.',
    inputSchema: {
      type: 'object',
      properties: {
        vault: { type: 'string', default: 'gkg' },
      },
    },
    handler: (args) => {
      const vault = args.vault || 'gkg';
      const snap = runJSON(`python3 ${GRAPH_SCRIPT} ${vaultPath(vault)} --summary`, { timeout: 180000 });
      if (snap.error) return snap;
      // Format as markdown
      const s = snap.summary || {};
      const lines = [
        `# Vault Profile: ${path.basename(vaultPath(vault))}`,
        `*Generated: ${snap.timestamp}*\n`,
        '## Overview',
        `| Metric | Value |`, `|--------|-------|`,
        `| Nodes | ${s.node_count} |`,
        `| Edges | ${s.edge_count} |`,
        `| Components | ${s.component_count} |`,
        `| Largest component | ${(s.component_sizes_top10||[])[0] || 0} |`,
        `| Orphans | ${s.orphan_count} |`,
        `| Bridges | ${s.bridge_count} |`,
        `| Avg in-degree | ${s.avg_in_degree} |`,
        `| Max in-degree | ${s.max_in_degree} |`,
        '',
        '## Entity Types',
        '| Type | Count |', '|------|-------|',
        ...Object.entries(s.entity_type_distribution || {}).sort((a,b) => b[1]-a[1]).map(([t,c]) => `| ${t||'(none)'} | ${c} |`),
        '',
        '## Edge Types',
        '| Type | Count |', '|------|-------|',
        ...Object.entries(s.edge_type_distribution || {}).sort((a,b) => b[1]-a[1]).map(([t,c]) => `| ${t} | ${c} |`),
        '',
        '## Top PageRank',
        '| Node | PR |', '|------|-------|',
        ...(snap.top_pagerank || []).slice(0, 15).map(o => { const [k,v] = Object.entries(o)[0]; return `| ${k} | ${v} |`; }),
        '',
        '## Top Hubs',
        ...(snap.top_hubs || []).slice(0, 15).map(o => { const [k,v] = Object.entries(o)[0]; return `- ${k}: ${v}`; }),
      ];
      return { content: lines.join('\n') };
    },
  },

  // ── Bases Query (obaq) ───────────────────────────────────
  'bases_query': {
    description: 'Query vault using Obsidian Bases .base files via obaq CLI. Evaluates formulas, filters, sorts. Returns structured JSON with columns and rows.',
    inputSchema: {
      type: 'object',
      properties: {
        vault: { type: 'string', default: 'gkg' },
        base_file: { type: 'string', description: 'Path to .base file relative to vault (e.g. LO/lo.base, SAQ/saq.base)' },
        format: { type: 'string', enum: ['json', 'csv', 'md'], default: 'json' },
      },
      required: ['base_file'],
    },
    handler: (args) => {
      const vault = args.vault || 'gkg';
      const fmt = args.format || 'json';
      const baseFile = path.join(vaultPath(vault), args.base_file);
      const result = run(`obaq -d ${vaultPath(vault)} -e '@${baseFile}' -f ${fmt}`, { timeout: 60000 });
      if (fmt === 'json') {
        try { return JSON.parse(result); } catch(e) { return { raw: result.slice(0, 2000) }; }
      }
      return { content: result.slice(0, 10000) };
    },
  },

  'bases_eval': {
    description: 'Evaluate an inline Bases YAML query against the vault. Useful for ad-hoc queries without a .base file.',
    inputSchema: {
      type: 'object',
      properties: {
        vault: { type: 'string', default: 'gkg' },
        query: { type: 'string', description: 'Bases YAML query (e.g. "filters:\n  and:\n    - file.inFolder(\\"LO\\")\nviews:\n  - type: table")' },
        format: { type: 'string', enum: ['json', 'csv', 'md'], default: 'json' },
      },
      required: ['query'],
    },
    handler: (args) => {
      const vault = args.vault || 'gkg';
      const fmt = args.format || 'json';
      // Write query to temp file
      const tmpFile = '/tmp/obaq-inline-query.yaml';
      fs.writeFileSync(tmpFile, args.query);
      const result = run(`obaq -d ${vaultPath(vault)} -e '@${tmpFile}' -f ${fmt}`, { timeout: 60000 });
      if (fmt === 'json') {
        try { return JSON.parse(result); } catch(e) { return { raw: result.slice(0, 2000) }; }
      }
      return { content: result.slice(0, 10000) };
    },
  },

  // ── Markdown Analysis (treemd) ────────────────────────────
  'md_tree': {
    description: 'Show heading tree structure of a markdown file using treemd. Useful for understanding document organization.',
    inputSchema: {
      type: 'object',
      properties: {
        vault: { type: 'string', default: 'gkg' },
        file: { type: 'string', description: 'File path relative to vault' },
      },
      required: ['file'],
    },
    handler: (args) => {
      const vault = args.vault || 'gkg';
      const filePath = path.join(vaultPath(vault), args.file);
      return { tree: run(`treemd --tree ${filePath}`) };
    },
  },

  'md_section': {
    description: 'Extract a specific section from a markdown file by heading name.',
    inputSchema: {
      type: 'object',
      properties: {
        vault: { type: 'string', default: 'gkg' },
        file: { type: 'string', description: 'File path relative to vault' },
        section: { type: 'string', description: 'Heading text to extract' },
      },
      required: ['file', 'section'],
    },
    handler: (args) => {
      const vault = args.vault || 'gkg';
      const filePath = path.join(vaultPath(vault), args.file);
      return { content: run(`treemd -s "${args.section.replace(/"/g, '\\"')}" ${filePath}`) };
    },
  },

  // ── Obsidian CLI Passthrough ───────────────────────────────
  'obsidian_search': {
    description: 'Search the active Obsidian vault using the built-in search engine.',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search query' },
      },
      required: ['query'],
    },
    handler: (args) => {
      return { results: run(`DISPLAY=:99 obsidian search query="${args.query.replace(/"/g, '\\"')}"`) };
    },
  },

  'obsidian_read': {
    description: 'Read a file from the active Obsidian vault.',
    inputSchema: {
      type: 'object',
      properties: {
        file: { type: 'string', description: 'File name (without .md)' },
      },
      required: ['file'],
    },
    handler: (args) => {
      return { content: run(`DISPLAY=:99 obsidian read file="${args.file.replace(/"/g, '\\"')}"`) };
    },
  },

  'obsidian_eval': {
    description: 'Evaluate JavaScript in the Obsidian renderer context. Access app.vault, app.metadataCache, etc.',
    inputSchema: {
      type: 'object',
      properties: {
        code: { type: 'string', description: 'JavaScript code to evaluate' },
      },
      required: ['code'],
    },
    handler: (args) => {
      return { result: run(`DISPLAY=:99 obsidian eval code="${args.code.replace(/"/g, '\\"').replace(/\n/g, ';')}"`) };
    },
  },

  // ── Cross-Vault Intelligence ───────────────────────────────
  'cross_vault_context': {
    description: 'Generate combined context from both gkg (knowledge graph) and pkg (learning system) vaults. Useful for understanding the full learning architecture.',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Focus query' },
        max_nodes: { type: 'number', default: 30 },
      },
    },
    handler: (args) => {
      const q = args.query ? `--query "${args.query.replace(/"/g, '\\"')}"` : '';
      const n = args.max_nodes || 30;
      const gkg = runJSON(`python3 ${GRAPH_SCRIPT} ${GKG_VAULT} --summary`, { timeout: 180000 });
      const pkg = runJSON(`python3 ${GRAPH_SCRIPT} ${PKG_VAULT} --summary`, { timeout: 180000 });
      return { gkg: { summary: gkg.summary, top_pagerank: (gkg.top_pagerank||[]).slice(0, n) }, pkg: { summary: pkg.summary, top_pagerank: (pkg.top_pagerank||[]).slice(0, n) } };
    },
  },

  'vault_node_detail': {
    description: 'Get detailed analytics for a specific node: its frontmatter, links, neighborhood, PageRank, and suggested related nodes.',
    inputSchema: {
      type: 'object',
      properties: {
        vault: { type: 'string', default: 'gkg' },
        node_id: { type: 'string', description: 'Node ID (file stem, e.g. AP23B14)' },
      },
      required: ['node_id'],
    },
    handler: (args) => {
      const vault = args.vault || 'gkg';
      const snap = getLatestSnapshot(vault);
      if (!snap || !snap.nodes) {
        // Take fresh snapshot (full, with nodes)
        const fresh = runJSON(`python3 ${GRAPH_SCRIPT} ${vaultPath(vault)}`, { timeout: 180000 });
        if (fresh.error) return fresh;
        saveSnapshot(vault, fresh);
        return findNode(fresh, args.node_id);
      }
      return findNode(snap, args.node_id);
    },
  },

  // ── PEX Interview Integration ───────────────────────────────
  'pex_vertex_resolve': {
    description: 'Resolve a PEX vertex equation to concrete gkg vault nodes. Returns matching LOs, SAQs with pass rates, and examiner comments. Use during PROBE/DIG/FILL phases.',
    inputSchema: {
      type: 'object',
      properties: {
        vertex: { type: 'string', description: 'Vertex name or keywords (e.g. "Fick", "clearance extraction", "Starling capillary")' },
        include_saq: { type: 'boolean', description: 'Include matching SAQs with pass rates', default: true },
        max_results: { type: 'number', default: 20 },
      },
      required: ['vertex'],
    },
    handler: (args) => {
      const vertex = args.vertex;
      const maxR = args.max_results || 20;
      // Search via turbovault for BM25 results
      const searchResult = runJSON(`curl -s -X POST http://localhost:3200/mcp -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search","arguments":{"query":"${vertex.replace(/'/g, '')}","limit":${maxR}}}}'`);
      let tvResults = [];
      try {
        const inner = JSON.parse(searchResult?.result?.content?.[0]?.text || '{}');
        tvResults = inner.data || [];
      } catch(e) {}
      
      // Also get graph context for PageRank-weighted results
      const graphCtx = runJSON(`python3 ${GRAPH_SCRIPT} ${GKG_VAULT} --summary`, { timeout: 60000 });
      
      return {
        vertex: vertex,
        turbovault_matches: tvResults.slice(0, maxR).map(r => ({
          path: r.path || r.name,
          score: r.score,
        })),
        graph_stats: graphCtx?.summary ? {
          total_nodes: graphCtx.summary.node_count,
          total_edges: graphCtx.summary.edge_count,
        } : null,
      };
    },
  },

  'pex_saq_for_vertex': {
    description: 'Find SAQs related to a PEX vertex, ranked by difficulty (lowest pass rate first). Returns SAQ IDs, pass rates, titles, and examiner comments. Essential for FILL phase model response generation.',
    inputSchema: {
      type: 'object',
      properties: {
        vertex_keywords: { type: 'string', description: 'Keywords for the vertex topic' },
        max_pass_rate: { type: 'number', description: 'Filter to SAQs below this pass rate %', default: 50 },
        limit: { type: 'number', default: 10 },
      },
      required: ['vertex_keywords'],
    },
    handler: (args) => {
      const kw = args.vertex_keywords.replace(/"/g, '\\"');
      const maxPR = args.max_pass_rate || 50;
      const limit = args.limit || 10;
      // Use obaq to query SAQs filtered by pass rate
      const query = `filters:\n  and:\n    - file.inFolder("SAQ")\n    - note.entityType == "SAQ"\n    - note.passRate < ${maxPR}\nviews:\n  - type: table\n    order:\n      - file.name\n      - note.passRate\n      - note.title\n      - note.college\n    sort:\n      - property: note.passRate\n        direction: ASC`;
      const tmpFile = '/tmp/pex-saq-query.yaml';
      fs.writeFileSync(tmpFile, query);
      const result = run(`obaq -d ${GKG_VAULT} -e '@${tmpFile}' -f json`, { timeout: 60000 });
      let parsed;
      try { parsed = JSON.parse(result); } catch(e) { return { error: 'parse_error', raw: result.slice(0, 500) }; }
      
      // Filter by keyword match in title
      const kwLower = kw.toLowerCase().split(/\s+/);
      const rows = (parsed.rows || []).filter(r => {
        const title = String(r['note.title'] || '');
        const titleLower = title.toLowerCase();
        return kwLower.some(k => titleLower.includes(k));
      }).slice(0, limit);
      
      return {
        query: kw,
        max_pass_rate: maxPR,
        total_matching: rows.length,
        saqs: rows.map(r => ({
          pass_rate: r['note.passRate'],
          title: String(r['note.title'] || '').slice(0, 150),
          college: String(r['note.college'] || ''),
        })),
      };
    },
  },

  'pex_session_state': {
    description: 'Get current PEX Interview session state (scores, gaps, vertex statuses). Returns the session tracker JSON.',
    inputSchema: { type: 'object', properties: {} },
    handler: () => {
      const sessionFile = path.join(PKG_VAULT, 'ops', 'sessions', 'pex-session.json');
      if (!fs.existsSync(sessionFile)) {
        return { active: false, message: 'No active PEX session. Run session_tracker.py init first.' };
      }
      try {
        return JSON.parse(fs.readFileSync(sessionFile, 'utf8'));
      } catch(e) {
        return { error: e.message };
      }
    },
  },

  'pex_session_command': {
    description: 'Execute a PEX session tracker command (init, score, status, gaps, fill, retest, export).',
    inputSchema: {
      type: 'object',
      properties: {
        command: { type: 'string', description: 'Full command args (e.g. "score --vertex Flow=\u0394P/R --level L2 --score 3")' },
      },
      required: ['command'],
    },
    handler: (args) => {
      const script = path.join(PKG_VAULT, 'ops', 'skills', 'pex-interview', 'scripts', 'session_tracker.py');
      return { output: run(`PKG_VAULT=${PKG_VAULT} python3 ${script} ${args.command}`) };
    },
  },

  'pex_graph_generate': {
    description: 'Generate a mermaid knowledge graph from current PEX session state. Types: round, dig, summary, ascii.',
    inputSchema: {
      type: 'object',
      properties: {
        type: { type: 'string', enum: ['round', 'dig', 'summary', 'ascii'], default: 'round' },
        vertex: { type: 'string', description: 'Required for dig type' },
      },
    },
    handler: (args) => {
      const script = path.join(PKG_VAULT, 'ops', 'skills', 'pex-interview', 'scripts', 'graph_generator.py');
      const vertexArg = args.vertex ? `--vertex "${args.vertex}"` : '';
      return { mermaid: run(`PKG_VAULT=${PKG_VAULT} python3 ${script} --type ${args.type || 'round'} ${vertexArg}`) };
    },
  },

  // ── Snapshot Management ───────────────────────────────────
  'snapshot_list': {
    description: 'List all stored graph snapshots with timestamps and stats.',
    inputSchema: { type: 'object', properties: {} },
    handler: () => {
      const files = fs.readdirSync(SNAPSHOTS_DIR)
        .filter(f => f.endsWith('.json'))
        .sort()
        .map(f => {
          const stat = fs.statSync(path.join(SNAPSHOTS_DIR, f));
          return { file: f, size: stat.size, modified: stat.mtime.toISOString() };
        });
      return { snapshots: files };
    },
  },
};

function findNode(snap, nodeId) {
  const node = snap.nodes.find(n => n.id === nodeId);
  if (!node) return { error: `Node '${nodeId}' not found` };
  
  // Find neighborhood
  const linksTo = node.links_out;
  const linksFrom = snap.nodes
    .filter(n => n.links_out.includes(nodeId))
    .map(n => n.id);
  
  // Suggested related (shared links)
  const linkSet = new Set([...linksTo, ...linksFrom]);
  const related = snap.nodes
    .filter(n => n.id !== nodeId && !linkSet.has(n.id))
    .map(n => ({
      id: n.id,
      shared: n.links_out.filter(l => linksTo.includes(l)).length + 
              linksTo.filter(l => n.links_out.includes(l)).length,
      type: n.entity_type,
    }))
    .filter(n => n.shared > 0)
    .sort((a, b) => b.shared - a.shared)
    .slice(0, 10);
  
  return {
    node: {
      id: node.id,
      path: node.path,
      entity_type: node.entity_type,
      title: node.title,
      frontmatter_keys: node.frontmatter_keys,
      college: node.college,
      in_degree: node.in_degree,
      out_degree: node.out_degree,
      pagerank: node.pagerank,
      hub_score: node.hub_score,
      component: node.component,
    },
    links_to: linksTo,
    links_from: linksFrom.slice(0, 50),
    suggested_related: related,
  };
}

// ── MCP Protocol Handler ────────────────────────────────────────────
function handleMCP(body) {
  const { jsonrpc, id, method, params } = body;
  
  if (method === 'initialize') {
    return {
      jsonrpc: '2.0', id,
      result: {
        protocolVersion: '2024-11-05',
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: 'vault-graph', version: '1.0.0' },
      },
    };
  }
  
  if (method === 'tools/list') {
    const tools = Object.entries(TOOLS).map(([name, def]) => ({
      name,
      description: def.description,
      inputSchema: def.inputSchema,
    }));
    return { jsonrpc: '2.0', id, result: { tools } };
  }
  
  if (method === 'tools/call') {
    const { name, arguments: args } = params || {};
    const tool = TOOLS[name];
    if (!tool) {
      return { jsonrpc: '2.0', id, error: { code: -32601, message: `Unknown tool: ${name}` } };
    }
    try {
      const result = tool.handler(args || {});
      return {
        jsonrpc: '2.0', id,
        result: {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
          isError: false,
        },
      };
    } catch(e) {
      return {
        jsonrpc: '2.0', id,
        result: {
          content: [{ type: 'text', text: JSON.stringify({ error: e.message }) }],
          isError: true,
        },
      };
    }
  }
  
  // Handle notifications (no response needed)
  if (method === 'notifications/initialized') {
    return null;
  }
  
  return { jsonrpc: '2.0', id, error: { code: -32601, message: `Unknown method: ${method}` } };
}

// ── HTTP Server ──────────────────────────────────────────────────────
const server = http.createServer((req, res) => {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }
  
  if (req.url === '/health' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ 
      status: 'healthy', 
      tools: Object.keys(TOOLS).length,
      vaults: { gkg: GKG_VAULT, pkg: PKG_VAULT },
      timestamp: new Date().toISOString(),
    }));
    return;
  }
  
  if (req.url === '/mcp' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        const parsed = JSON.parse(body);
        const response = handleMCP(parsed);
        if (response === null) {
          // Notification — no response
          res.writeHead(204);
          res.end();
          return;
        }
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(response));
      } catch(e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }
  
  res.writeHead(404);
  res.end('Not found');
});

server.listen(PORT, () => {
  console.log(`vault-graph MCP server on http://localhost:${PORT}/mcp`);
  console.log(`Tools: ${Object.keys(TOOLS).join(', ')}`);
  console.log(`Vaults: gkg=${GKG_VAULT}, pkg=${PKG_VAULT}`);
});
