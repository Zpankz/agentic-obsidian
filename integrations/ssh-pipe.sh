#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# ssh-pipe.sh — SSH helpers for remote Obsidian CLI
#
# Source this file to get helper functions:
#   source ssh-pipe.sh
#   obs my-vm search query="meeting notes"
# ─────────────────────────────────────────────────────────────────────────────

# Set your default VM hostname
OBS_HOST="${OBS_HOST:-}"

obs() {
  local host="${OBS_HOST}"
  if [ -z "$host" ]; then
    echo "Set OBS_HOST first: export OBS_HOST=myvm.exe.xyz"
    return 1
  fi
  ssh "$host" "DISPLAY=:99 obsidian $*"
}

obs-read()   { obs "read file=\"$1\""; }
obs-search() { obs "search query=\"$*\""; }
obs-daily()  { obs "daily:append content=\"$*\" silent"; }
obs-create() { obs "create name=\"$1\" content=\"$2\" silent"; }
obs-files()  { obs "files"; }
obs-tags()   { obs "tags all counts"; }
obs-tasks()  { obs "tasks all"; }
obs-beat()   { obs "read file=heartbeat"; }
