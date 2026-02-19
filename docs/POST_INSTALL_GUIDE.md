# Post-Install Guide: Insider CLI & Sync Setup

After running `install.sh`, you have a headless Obsidian instance on a virtual framebuffer — but the **CLI doesn't work yet** and **Sync isn't connected**. This guide covers the steps required to close those gaps.

## What `install.sh` gives you

| Component | State after install |
|---|---|
| Obsidian 1.11.7 AppImage | ✅ Extracted to `/opt/obsidian/squashfs-root/` |
| Xvfb virtual display | ✅ Running on `:99` |
| systemd services | ✅ `obsidian.service` + `obsidian-api.service` |
| CLI symlink | ✅ `/usr/local/bin/obsidian` |
| HTTP API | ✅ Port 3000 |
| Cron jobs | ✅ Heartbeat (5m) + backup (daily 3am) |
| **CLI commands** | ❌ Require 1.12+ insider `.asar` |
| **Obsidian account** | ❌ Not authenticated |
| **Obsidian Sync** | ❌ Not connected |

## What's missing and why

1. **Insider build** — The CLI (`obsidian help`, `obsidian search`, etc.) was introduced in Obsidian 1.12 (Catalyst beta). The public AppImage is 1.11.7 and has no CLI. Without the insider `.asar`, running `DISPLAY=:99 obsidian help` produces only Electron log noise.

2. **Authentication** — Sync requires an Obsidian account token stored in the renderer's `localStorage`. This isn't something `install.sh` can do.

3. **Sync connection** — A remote vault must be created or selected, and the local sync plugin must be configured with the vault's ID, host, encryption password, and salt.

---

## Step 1: Upgrade to Obsidian 1.12+ (Insider Build)

The insider `.asar` is cryptographically signed and hash-verified. You **cannot** download it directly via `curl` — the download URL at `releases.obsidian.md` only works through Obsidian's built-in Electron `net` module. Instead, you trigger Obsidian's own auto-updater.

### How the update mechanism works

1. Obsidian fetches [`desktop-releases.json`](https://raw.githubusercontent.com/obsidianmd/obsidian-releases/master/desktop-releases.json) from GitHub
2. If `insider` is `true` in config, it reads the `beta` branch of that JSON
3. It downloads the `.asar.gz` from `releases.obsidian.md`
4. Verifies SHA-256 hash + RSA signature against a hardcoded Dynalist certificate
5. Decompresses and saves to `~/.config/obsidian/obsidian-<version>.asar`
6. On next launch, Obsidian loads the updated package automatically

### Procedure

```bash
# 1. Set insider: true in the Obsidian config
python3 -c "
import json
cfg_path = '$HOME/.config/obsidian/obsidian.json'
with open(cfg_path) as f:
    cfg = json.load(f)
cfg['insider'] = True
with open(cfg_path, 'w') as f:
    json.dump(cfg, f, indent=2)
"

# 2. Restart Obsidian to trigger the auto-updater
sudo systemctl restart obsidian
sleep 15

# 3. Verify the insider build was downloaded
ls ~/.config/obsidian/obsidian-1.*.asar
# Expected: obsidian-1.12.2.asar (or newer)

# 4. Verify CLI works
DISPLAY=:99 obsidian version
# Expected: 1.12.2 (installer 1.11.7)

DISPLAY=:99 obsidian help
# Expected: full CLI help output
```

### Verification via logs

```bash
tail -20 ~/.config/obsidian/obsidian.log
```

Successful update looks like:
```
Checking for update using Github
Success.
Latest version is 1.12.2 (insider)
Downloading update from https://releases.obsidian.md/release/obsidian-1.12.2.asar.gz
Verifying hash & signature. Size= 8321788
Saving file
Update complete.
Loaded updated app package /home/user/.config/obsidian/obsidian-1.12.2.asar
App is up to date.
```

> **Note**: The insider build requires an active Obsidian Catalyst license. Without one, the updater downloads the public version which has no CLI.

---

## Step 2: Authenticate with Obsidian Account

Sync requires an authenticated account token. The token must be stored in the renderer's `localStorage` under the key `obsidian-account`.

### API authentication

> **Critical**: The Obsidian API at `api.obsidian.md` is behind Cloudflare. Requests without browser-like headers receive HTTP 1010 (Access Denied). You **must** include `User-Agent`, `Origin`, and `Referer` headers.

```bash
# Sign in (from the VM, e.g., via curl or Python)
curl -s -X POST https://api.obsidian.md/user/signin \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36' \
  -H 'Origin: https://obsidian.md' \
  -H 'Referer: https://obsidian.md/' \
  -d '{"email": "your@email.com", "password": "your-password"}'
```

Response:
```json
{"token": "abc123...", "email": "your@email.com", "name": "Your Name", "license": "vip"}
```

### Store token in Obsidian

```bash
# Inject the token into the running Obsidian renderer
DISPLAY=:99 obsidian eval code="
localStorage.setItem('obsidian-account', JSON.stringify({
  email: 'your@email.com',
  name: 'Your Name',
  token: 'abc123...',
  license: 'vip'
}));
'done'
"
```

### Restart to apply

The `Vw` account singleton is module-scoped and initialized **once** from `localStorage` at app startup. Setting `localStorage` mid-session does **not** update it. You must restart:

```bash
sudo systemctl restart obsidian
sleep 10
```

---

## Step 3: Connect Obsidian Sync

### List remote vaults

Use the token from Step 2:

```bash
curl -s -X POST https://api.obsidian.md/vault/list \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36' \
  -H 'Origin: https://obsidian.md' \
  -d '{"token": "abc123...", "supported_encryption_version": 3}'
```

Response includes vault `id`, `name`, `host`, `password`, `salt`, `encryption_version`.

### Create a remote vault (if needed)

```bash
curl -s -X POST https://api.obsidian.md/vault/create \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36' \
  -H 'Origin: https://obsidian.md' \
  -d '{"token": "abc123...", "name": "my-vault", "keyhash": null, "salt": null, "region": "North America", "encryption_version": 3}'
```

Response returns the full vault object including server-generated `password` and `salt`.

### Connect the local vault

> **Critical gotcha**: The `host` parameter must be the bare hostname (e.g., `sync-49.obsidian.md`), **not** a full URL. The sync plugin's `getHost()` method prepends `wss://` automatically. Passing `wss://sync-49.obsidian.md` results in `wss://wss://sync-49.obsidian.md` and connection failure.

```bash
DISPLAY=:99 obsidian eval code="
var sync = app.internalPlugins.plugins.sync.instance;
sync.setup(
  'VAULT_ID',
  'VAULT_NAME',
  'PASSWORD',
  'SALT',
  'sync-XX.obsidian.md',   // bare hostname, NO wss:// prefix!
  3                        // encryption version
).then(function() {
  sync.saveData();
  require('fs').writeFileSync('/tmp/sync-result.json', JSON.stringify({ok: true}));
}).catch(function(e) {
  require('fs').writeFileSync('/tmp/sync-result.json', JSON.stringify({error: e.message}));
});
'connecting...'
"

sleep 5
cat /tmp/sync-result.json
```

### Restart and verify

```bash
sudo systemctl restart obsidian
sleep 10
DISPLAY=:99 obsidian sync:status
```

Expected output:
```
status: synced
vault: my-vault
vault size: X KB
account usage: X GB / 10.00 GB
```

---

## Quick Reference

### Key file locations

| File | Purpose |
|---|---|
| `~/.config/obsidian/obsidian.json` | Main config (vaults, insider flag) |
| `~/.config/obsidian/obsidian.log` | App log (update status, errors) |
| `~/.config/obsidian/obsidian-X.Y.Z.asar` | Insider build package |
| `/opt/obsidian/squashfs-root/` | Extracted AppImage (base installer) |
| `/opt/obsidian/api/server.js` | HTTP API server |

### Required API headers (Cloudflare bypass)

```
User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36
Origin: https://obsidian.md
Referer: https://obsidian.md/
Content-Type: application/json
```

### Key CLI commands

```bash
DISPLAY=:99 obsidian version        # Check version
DISPLAY=:99 obsidian help            # Full CLI help
DISPLAY=:99 obsidian sync:status     # Sync status
DISPLAY=:99 obsidian files           # List vault files
DISPLAY=:99 obsidian eval code="..." # Execute JS in renderer
```

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| CLI outputs only log noise | Missing insider `.asar` | Run Step 1 |
| `Login failed` from API | Bad credentials or missing headers | Add Cloudflare bypass headers |
| Sync status: `Not logged in` | Token not in `Vw` singleton | Set localStorage + restart Obsidian |
| Sync status: `Unable to connect` | Double `wss://` in host | Set host to bare hostname only |
| Updater says "App is up to date" at 1.11.7 | `insider` not set to `true` | Update `obsidian.json` + restart |
| `.asar` download 404 via curl | Normal — only works via Electron `net` | Use Obsidian's own updater |
