const http = require("http");
const { execSync } = require("child_process");
const url = require("url");
const fs = require("fs");
const path = require("path");

const PORT = process.env.PORT || 3000;
const API_TOKEN = process.env.API_TOKEN || "";
const DISPLAY = process.env.DISPLAY || ":99";

// ─── Helpers ────────────────────────────────────────────────────────────────

function obsidian(command) {
  try {
    const result = execSync(`DISPLAY=${DISPLAY} obsidian ${command}`, {
      timeout: 15000,
      encoding: "utf-8",
      env: { ...process.env, DISPLAY },
    });
    return result.trim();
  } catch (err) {
    throw new Error(err.stderr || err.message);
  }
}

function json(res, statusCode, data) {
  res.writeHead(statusCode, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data));
}

function getBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch {
        reject(new Error("Invalid JSON body"));
      }
    });
  });
}

function authenticate(req) {
  // exe.dev proxy injects X-ExeDev-Email for authenticated users
  if (req.headers["x-exedev-email"]) return true;

  // Bearer token auth
  if (API_TOKEN) {
    const auth = req.headers.authorization || "";
    return auth === `Bearer ${API_TOKEN}`;
  }

  // No auth configured — allow localhost only
  const remote = req.socket.remoteAddress;
  return remote === "127.0.0.1" || remote === "::1" || remote === "::ffff:127.0.0.1";
}

// ─── Graph Analytics Engine ──────────────────────────────────────────────────

function obsidianEval(code) {
  try {
    const escaped = code.replace(/"/g, '\\"');
    const result = execSync(
      `DISPLAY=${DISPLAY} obsidian eval code="${escaped}"`,
      { timeout: 30000, encoding: 'utf-8', env: { ...process.env, DISPLAY }, maxBuffer: 10 * 1024 * 1024 }
    );
    // Strip the "=> " prefix from eval output
    const trimmed = result.trim().replace(/^=> /, '');
    try { return JSON.parse(trimmed); } catch { return trimmed; }
  } catch (err) {
    throw new Error(err.stderr || err.message);
  }
}

/**
 * Get the full graph state from Obsidian's metadata cache.
 * Uses file-based transfer to handle large vaults (2500+ nodes).
 * Returns { nodes: [{path, frontmatter, out_links}], edges: [{from, to}] }
 */
let _graphCache = null;
let _graphCacheTime = 0;
const GRAPH_CACHE_TTL = 30000; // 30 seconds

function getGraphState() {
  const now = Date.now();
  if (_graphCache && (now - _graphCacheTime) < GRAPH_CACHE_TTL) {
    return _graphCache;
  }

  const fs = require('fs');
  const tmpFile = '/tmp/obsidian-graph-state.json';
  
  // Write graph state to temp file via eval (avoids stdout size limits)
  obsidianEval(
    `const fs = require("fs"); const cache = app.metadataCache; const files = app.vault.getMarkdownFiles(); const nodes = []; const edges = []; for (const f of files) { const meta = cache.getFileCache(f); const fm = meta && meta.frontmatter ? meta.frontmatter : {}; const links = (meta && meta.links ? meta.links : []).map(l => { const r = cache.getFirstLinkpathDest(l.link, f.path); return r ? r.path : null; }).filter(Boolean); nodes.push({ path: f.path, basename: f.basename, fm: fm, mtime: f.stat ? f.stat.mtime : 0 }); for (const target of [...new Set(links)]) { if (target !== f.path) edges.push({from: f.path, to: target}); } } fs.writeFileSync("${tmpFile}", JSON.stringify({nodes: nodes, edges: edges})); "wrote " + nodes.length + " nodes"`
  );
  
  // Read from temp file
  try {
    const data = fs.readFileSync(tmpFile, 'utf-8');
    _graphCache = JSON.parse(data);
    _graphCacheTime = now;
    return _graphCache;
  } catch (err) {
    throw new Error('Failed to read graph state from ' + tmpFile + ': ' + err.message);
  }
}

/**
 * Run the analytics computation script inside Obsidian.
 * Returns summary JSON.
 */
function runAnalyticsCompute() {
  const fs = require('fs');
  const vaultPath = process.env.OBSIDIAN_VAULT || '/home/exedev/pkg';
  const scriptPath = vaultPath + '/ops/scripts/graph-analytics.js';
  const code = fs.readFileSync(scriptPath, 'utf-8');
  // Execute via eval
  try {
    const result = execSync(
      `DISPLAY=${DISPLAY} obsidian eval code="$(cat '${scriptPath}')"`,
      { timeout: 60000, encoding: 'utf-8', env: { ...process.env, DISPLAY }, maxBuffer: 10 * 1024 * 1024, shell: '/bin/bash' }
    );
    const trimmed = result.trim();
    // May contain [error] lines from frontmatter processing
    const lines = trimmed.split('\n');
    const lastLine = lines[lines.length - 1].replace(/^=> /, '');
    try { return JSON.parse(lastLine); } catch { return { raw: trimmed }; }
  } catch (err) {
    throw new Error('Analytics computation failed: ' + (err.stderr || err.message));
  }
}

/**
 * MCMC Traversal Engine
 * 
 * Given a query, finds the optimal reading order through the knowledge graph
 * using Metropolis-Hastings with graph-informed proposals.
 *
 * The energy function balances:
 *   - Relevance to query (keyword match score)
 *   - Information value (priority_score × confidence_gap)
 *   - Token cost (penalize long files)
 *   - Edge coherence (prefer connected traversals)
 */
function mcmcTraverse(graphState, query, options = {}) {
  const {
    maxNodes = 10,
    iterations = 500,
    burnIn = 50,
    thinning = 3,
    temperature = 1.0
  } = options;

  const { nodes, edges } = graphState;
  const N = nodes.length;
  if (N === 0) return { path: [], scores: {} };

  // Build adjacency
  const pathIdx = {};
  nodes.forEach((n, i) => pathIdx[n.path] = i);
  const adj = Array.from({length: N}, () => new Set());
  for (const e of edges) {
    const i = pathIdx[e.from], j = pathIdx[e.to];
    if (i !== undefined && j !== undefined) {
      adj[i].add(j);
      adj[j].add(i); // undirected for traversal
    }
  }

  // Relevance scoring (TF-IDF-like keyword matching)
  const queryTerms = query.toLowerCase().split(/\s+/).filter(t => t.length > 2);
  const relevance = new Array(N).fill(0);
  for (let i = 0; i < N; i++) {
    const n = nodes[i];
    const text = [
      n.basename,
      n.fm.description || '',
      (n.fm.topics || []).join(' '),
      (n.fm.domain || []).join(' ')
    ].join(' ').toLowerCase();
    for (const term of queryTerms) {
      if (text.includes(term)) relevance[i] += 1;
    }
    // Boost by pagerank
    relevance[i] += (n.fm.pagerank || 0) * 2;
  }
  // Normalize
  const maxRel = Math.max(...relevance, 0.001);
  for (let i = 0; i < N; i++) relevance[i] /= maxRel;

  // Information value: priority × confidence gap
  const infoValue = nodes.map(n => {
    const pri = n.fm.priority_score || 0;
    const conf = typeof n.fm.confidence === 'number' ? n.fm.confidence : 0.5;
    return pri * (1 - conf);
  });
  const maxInfo = Math.max(...infoValue, 0.001);
  for (let i = 0; i < N; i++) infoValue[i] /= maxInfo;

  // Energy function for a traversal path
  function energy(path) {
    if (path.length === 0) return Infinity;
    let E = 0;
    for (let k = 0; k < path.length; k++) {
      const i = path[k];
      // Reward relevance and info value
      E -= relevance[i] * 0.4;
      E -= infoValue[i] * 0.4;
      // Penalize disconnected transitions
      if (k > 0 && !adj[path[k-1]].has(i)) {
        E += 0.3; // penalty for jumping
      }
      // Small penalty for node count (token budget)
      E += 0.05;
    }
    // Penalize duplicate visits
    const unique = new Set(path);
    E += (path.length - unique.size) * 2;
    return E;
  }

  // Initialize: top nodes by relevance + info
  const scored = nodes.map((_, i) => ({ i, s: relevance[i] * 0.5 + infoValue[i] * 0.5 }))
    .sort((a, b) => b.s - a.s);
  let currentPath = scored.slice(0, Math.min(maxNodes, N)).map(x => x.i);
  let currentEnergy = energy(currentPath);

  // Track best
  let bestPath = [...currentPath];
  let bestEnergy = currentEnergy;

  // MCMC iterations
  const samples = [];
  for (let iter = 0; iter < iterations; iter++) {
    // Propose: random mutation
    const proposedPath = [...currentPath];
    const moveType = Math.random();

    if (moveType < 0.3 && proposedPath.length > 1) {
      // Swap two positions
      const a = Math.floor(Math.random() * proposedPath.length);
      const b = Math.floor(Math.random() * proposedPath.length);
      [proposedPath[a], proposedPath[b]] = [proposedPath[b], proposedPath[a]];
    } else if (moveType < 0.6 && proposedPath.length < maxNodes) {
      // Add a neighbor of a random current node
      const src = proposedPath[Math.floor(Math.random() * proposedPath.length)];
      const neighbors = [...adj[src]];
      if (neighbors.length > 0) {
        const newNode = neighbors[Math.floor(Math.random() * neighbors.length)];
        const insertPos = Math.floor(Math.random() * (proposedPath.length + 1));
        proposedPath.splice(insertPos, 0, newNode);
      }
    } else if (moveType < 0.8 && proposedPath.length > 2) {
      // Remove a random node
      const removeIdx = Math.floor(Math.random() * proposedPath.length);
      proposedPath.splice(removeIdx, 1);
    } else {
      // Replace a node with a random graph neighbor
      const idx = Math.floor(Math.random() * proposedPath.length);
      const neighbors = [...adj[proposedPath[idx]]];
      if (neighbors.length > 0) {
        proposedPath[idx] = neighbors[Math.floor(Math.random() * neighbors.length)];
      } else {
        // Replace with a random high-relevance node
        proposedPath[idx] = scored[Math.floor(Math.random() * Math.min(20, scored.length))].i;
      }
    }

    const proposedEnergy = energy(proposedPath);

    // Metropolis-Hastings acceptance
    const deltaE = proposedEnergy - currentEnergy;
    if (deltaE < 0 || Math.random() < Math.exp(-deltaE / temperature)) {
      currentPath = proposedPath;
      currentEnergy = proposedEnergy;
    }

    if (currentEnergy < bestEnergy) {
      bestPath = [...currentPath];
      bestEnergy = currentEnergy;
    }

    // Collect samples after burn-in with thinning
    if (iter >= burnIn && (iter - burnIn) % thinning === 0) {
      samples.push({ path: [...currentPath], energy: currentEnergy });
    }
  }

  // Deduplicate best path
  const seen = new Set();
  const dedupPath = bestPath.filter(i => {
    if (seen.has(i)) return false;
    seen.add(i);
    return true;
  });

  // Build result
  const result = dedupPath.map((i, rank) => {
    const n = nodes[i];
    const prevConnected = rank > 0 ? adj[dedupPath[rank-1]].has(i) : true;
    return {
      rank: rank + 1,
      path: n.path,
      relevance: Math.round(relevance[i] * 1000) / 1000,
      info_value: Math.round(infoValue[i] * 1000) / 1000,
      pagerank: n.fm.pagerank || 0,
      confidence: n.fm.confidence,
      priority_score: n.fm.priority_score,
      cluster: n.fm.cluster_id,
      edge_connected: prevConnected
    };
  });

  return {
    query,
    traversal: result,
    energy: Math.round(bestEnergy * 1000) / 1000,
    samples_collected: samples.length,
    acceptance_rate: Math.round(samples.filter((s, i) => 
      i === 0 || s.energy !== samples[i-1]?.energy
    ).length / Math.max(samples.length, 1) * 100) / 100,
    mcmc_params: { iterations, burnIn, thinning, temperature, maxNodes }
  };
}

/**
 * Smart read: reads a file and appends neighborhood analytics context
 */
function smartRead(fileArg, pathArg) {
  // Get the file content
  const target = pathArg ? `path="${pathArg}"` : `file="${fileArg}"`;
  const content = obsidian(`read ${target}`);

  // Get neighborhood analytics via eval
  const filePath = pathArg || '';
  const fileName = fileArg || '';
  const neighborhood = obsidianEval(`
    (async () => {
      const cache = app.metadataCache;
      const files = app.vault.getMarkdownFiles();
      const target = files.find(f => 
        f.path === '${filePath}' || f.basename === '${fileName}'
      );
      if (!target) return JSON.stringify({error: 'not found'});
      const meta = cache.getFileCache(target);
      const fm = meta?.frontmatter || {};
      const outLinks = (meta?.links || []).map(l => {
        const r = cache.getFirstLinkpathDest(l.link, target.path);
        if (!r) return null;
        const rfm = cache.getFileCache(r)?.frontmatter || {};
        return {
          path: r.path,
          confidence: rfm.confidence,
          priority: rfm.priority_score,
          pagerank: rfm.pagerank,
          cluster: rfm.cluster_id
        };
      }).filter(Boolean);
      const backlinks = [];
      for (const f of files) {
        if (f.path === target.path) continue;
        const fmeta = cache.getFileCache(f);
        for (const l of (fmeta?.links || [])) {
          const r = cache.getFirstLinkpathDest(l.link, f.path);
          if (r && r.path === target.path) {
            const rfm = fmeta?.frontmatter || {};
            backlinks.push({
              path: f.path,
              confidence: rfm.confidence,
              priority: rfm.priority_score,
              pagerank: rfm.pagerank,
              cluster: rfm.cluster_id
            });
            break;
          }
        }
      }
      return JSON.stringify({
        self: {
          path: target.path,
          node_type: fm.node_type,
          confidence: fm.confidence,
          priority_score: fm.priority_score,
          pagerank: fm.pagerank,
          eigenvector_centrality: fm.eigenvector_centrality,
          cluster_id: fm.cluster_id,
          delta_class: fm.delta_class,
          in_degree: fm.in_degree,
          out_degree: fm.out_degree,
          staleness_days: fm.staleness_days
        },
        outgoing: outLinks.sort((a,b) => (b.priority||0) - (a.priority||0)),
        incoming: backlinks.sort((a,b) => (b.pagerank||0) - (a.pagerank||0)),
        suggested_next: [...outLinks, ...backlinks]
          .sort((a,b) => {
            const aScore = (a.priority||0) * (1 - (a.confidence||0.5));
            const bScore = (b.priority||0) * (1 - (b.confidence||0.5));
            return bScore - aScore;
          }).slice(0, 3).map(x => x.path)
      });
    })()
  `);

  return { content, analytics: neighborhood };
}

// ─── Routes ─────────────────────────────────────────────────────────────────

const routes = {
  "GET /health": () => {
    let obsidianOk = false;
    try {
      obsidian("version");
      obsidianOk = true;
    } catch {}
    return {
      status: obsidianOk ? "healthy" : "degraded",
      obsidian: obsidianOk,
      timestamp: new Date().toISOString(),
    };
  },

  "GET /version": () => ({ version: obsidian("version") }),

  "GET /vault": () => {
    const raw = obsidian("vault");
    const info = {};
    raw.split("\n").forEach((line) => {
      const [key, ...rest] = line.split("\t");
      if (key && rest.length) info[key.trim()] = rest.join("\t").trim();
    });
    return info;
  },

  "GET /files": (query) => {
    const args = [];
    if (query.folder) args.push(`folder=${query.folder}`);
    if (query.ext) args.push(`ext=${query.ext}`);
    if (query.total) args.push("total");
    const raw = obsidian(`files ${args.join(" ")}`);
    return { files: raw.split("\n").filter(Boolean) };
  },

  "GET /read": (query) => {
    if (!query.file && !query.path) throw new Error("file or path required");
    const target = query.path ? `path="${query.path}"` : `file="${query.file}"`;
    return { content: obsidian(`read ${target}`) };
  },

  "GET /search": (query) => {
    if (!query.q) throw new Error("q (query) parameter required");
    const args = [`query="${query.q}"`];
    if (query.limit) args.push(`limit=${query.limit}`);
    if (query.matches) args.push("matches");
    return { results: obsidian(`search ${args.join(" ")}`) };
  },

  "GET /tags": (query) => {
    const args = ["all"];
    if (query.counts) args.push("counts");
    if (query.sort) args.push(`sort=${query.sort}`);
    const raw = obsidian(`tags ${args.join(" ")}`);
    return { tags: raw.split("\n").filter(Boolean) };
  },

  "GET /tasks": (query) => {
    const args = [];
    if (query.daily) args.push("daily");
    else args.push("all");
    if (query.todo) args.push("todo");
    if (query.done) args.push("done");
    return { tasks: obsidian(`tasks ${args.join(" ")}`) };
  },

  "POST /create": async (query, body) => {
    const args = [];
    if (body.name) args.push(`name="${body.name}"`);
    if (body.path) args.push(`path="${body.path}"`);
    if (body.content) args.push(`content="${body.content}"`);
    if (body.template) args.push(`template="${body.template}"`);
    if (body.overwrite) args.push("overwrite");
    args.push("silent");
    return { result: obsidian(`create ${args.join(" ")}`) };
  },

  "POST /append": async (query, body) => {
    if (!body.content) throw new Error("content required");
    const args = [`content="${body.content}"`];
    if (body.file) args.push(`file="${body.file}"`);
    if (body.path) args.push(`path="${body.path}"`);
    return { result: obsidian(`append ${args.join(" ")}`) };
  },

  "POST /daily/append": async (query, body) => {
    if (!body.content) throw new Error("content required");
    return {
      result: obsidian(`daily:append content="${body.content}" silent`),
    };
  },

  "POST /command": async (query, body) => {
    if (!body.command) throw new Error("command required");
    return { result: obsidian(body.command) };
  },

  // ─── Graph Analytics Routes ─────────────────────────────────────────────

  "GET /analytics/graph": () => {
    return getGraphState();
  },

  "POST /analytics/compute": async () => {
    const result = runAnalyticsCompute();
    return { status: 'computed', result };
  },

  "GET /analytics/summary": () => {
    let nodes, edges;
    // Try snapshot file first (pre-computed, reliable)
    try {
      const fs = require('fs');
      const snapPath = '/home/exedev/agentic-obsidian/snapshots/gkg-latest.json';
      if (fs.existsSync(snapPath)) {
        const snap = JSON.parse(fs.readFileSync(snapPath, 'utf-8'));
        nodes = snap.nodes || [];
        edges = snap.edges || [];
      }
    } catch(e) { /* fall through */ }
    // Fallback to live graph
    if (!nodes) {
      try {
        const raw = getGraphState();
        const graph = typeof raw === 'string' ? JSON.parse(raw) : raw;
        nodes = graph.nodes || [];
        edges = graph.edges || [];
      } catch(e) { return { error: 'No graph data available: ' + e.message }; }
    }
    const knowledge = nodes.filter(n => n.fm && ['knowledge', 'moc', 'layer', 'evidence'].includes(n.fm.node_type));
    const clusters = {};
    for (const n of knowledge) {
      const c = n.fm.cluster_id || 'unclustered';
      if (!clusters[c]) clusters[c] = { count: 0, avg_confidence: 0, avg_priority: 0, members: [] };
      clusters[c].count++;
      clusters[c].avg_confidence += (n.fm.confidence || 0);
      clusters[c].avg_priority += (n.fm.priority_score || 0);
      clusters[c].members.push(n.basename);
    }
    for (const c of Object.values(clusters)) {
      c.avg_confidence = Math.round(c.avg_confidence / c.count * 100) / 100;
      c.avg_priority = Math.round(c.avg_priority / c.count * 100) / 100;
    }
    const orphans = nodes.filter(n => n.fm && (n.fm.in_degree || 0) === 0 && n.fm.node_type !== 'system').map(n => n.path);
    const deadends = nodes.filter(n => n.fm && (n.fm.out_degree || 0) === 0 && n.fm.node_type !== 'system').map(n => n.path);
    const weakest = knowledge
      .filter(n => n.fm.priority_score)
      .sort((a, b) => {
        const as = (a.fm.priority_score || 0) * (1 - (a.fm.confidence || 0.5));
        const bs = (b.fm.priority_score || 0) * (1 - (b.fm.confidence || 0.5));
        return bs - as;
      })
      .slice(0, 5)
      .map(n => ({
        path: n.path,
        priority: n.fm.priority_score,
        confidence: n.fm.confidence,
        delta_class: n.fm.delta_class,
        urgency: Math.round((n.fm.priority_score || 0) * (1 - (n.fm.confidence || 0.5)) * 1000) / 1000
      }));
    return {
      total_nodes: nodes.length,
      total_edges: edges.length,
      knowledge_nodes: knowledge.length,
      clusters,
      orphan_count: orphans.length,
      deadend_count: deadends.length,
      weakest_nodes: weakest
    };
  },

  "POST /traverse": async (query, body) => {
    if (!body.query) throw new Error('query required');
    const graph = getGraphState();
    return mcmcTraverse(graph, body.query, {
      maxNodes: body.max_nodes || 10,
      iterations: body.iterations || 500,
      burnIn: body.burn_in || 50,
      thinning: body.thinning || 3,
      temperature: body.temperature || 1.0
    });
  },

  "GET /read/smart": (query) => {
    if (!query.file && !query.path) throw new Error('file or path required');
    return smartRead(query.file || '', query.path || '');
  },

  "GET /analytics/node": (query) => {
    if (!query.path && !query.file) throw new Error('path or file required');
    // Get node-specific analytics
    const graph = getGraphState();
    const { nodes, edges } = graph;
    const target = nodes.find(n => 
      n.path === query.path || n.basename === query.file
    );
    if (!target) throw new Error('Node not found');
    const outEdges = edges.filter(e => e.from === target.path);
    const inEdges = edges.filter(e => e.to === target.path);
    const outNeighbors = outEdges.map(e => {
      const n = nodes.find(x => x.path === e.to);
      return n ? { path: n.path, pagerank: n.fm.pagerank, confidence: n.fm.confidence, cluster: n.fm.cluster_id } : null;
    }).filter(Boolean);
    const inNeighbors = inEdges.map(e => {
      const n = nodes.find(x => x.path === e.from);
      return n ? { path: n.path, pagerank: n.fm.pagerank, confidence: n.fm.confidence, cluster: n.fm.cluster_id } : null;
    }).filter(Boolean);
    return {
      node: {
        path: target.path,
        node_type: target.fm.node_type,
        domain: target.fm.domain,
        confidence: target.fm.confidence,
        priority_score: target.fm.priority_score,
        pagerank: target.fm.pagerank,
        eigenvector_centrality: target.fm.eigenvector_centrality,
        cluster_id: target.fm.cluster_id,
        delta_class: target.fm.delta_class,
        in_degree: target.fm.in_degree,
        out_degree: target.fm.out_degree
      },
      outgoing: outNeighbors,
      incoming: inNeighbors,
      neighborhood_size: outNeighbors.length + inNeighbors.length
    };
  },
};

// ─── Server ─────────────────────────────────────────────────────────────────

const server = http.createServer(async (req, res) => {
  const parsed = url.parse(req.url, true);
  const routeKey = `${req.method} ${parsed.pathname}`;

  // CORS
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  if (req.method === "OPTIONS") return json(res, 200, {});

  // Health check is always public
  if (routeKey !== "GET /health" && !authenticate(req)) {
    return json(res, 401, { error: "Unauthorized" });
  }

  // Serve dashboard
  if (req.method === 'GET' && (parsed.pathname === '/dashboard' || parsed.pathname === '/dashboard/')) {
    const dashPath = '/home/exedev/dashboard/index.html';
    try {
      const html = fs.readFileSync(dashPath, 'utf-8');
      res.writeHead(200, { 'Content-Type': 'text/html' });
      return res.end(html);
    } catch { return json(res, 500, { error: 'Dashboard not found' }); }
  }

  const handler = routes[routeKey];
  if (!handler) {
    return json(res, 404, {
      error: "Not found",
      endpoints: [...Object.keys(routes), 'GET /dashboard'],
    });
  }

  try {
    const body = req.method === "POST" ? await getBody(req) : {};
    const result = await handler(parsed.query, body);
    json(res, 200, result);
  } catch (err) {
    json(res, 500, { error: err.message });
  }
});

server.listen(PORT, () => {
  console.log(`[obsidian-api] Listening on port ${PORT}`);
  console.log(`[obsidian-api] Auth: ${API_TOKEN ? "bearer token" : "localhost-only"}`);
});
