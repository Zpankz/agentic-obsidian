const http = require("http");
const { execSync } = require("child_process");
const url = require("url");

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

  const handler = routes[routeKey];
  if (!handler) {
    return json(res, 404, {
      error: "Not found",
      endpoints: Object.keys(routes),
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
