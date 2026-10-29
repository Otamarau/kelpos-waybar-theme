#!/usr/bin/env bash
# Always emit text so the indicator keeps its place when disconnected.
if tailscale status --json 2>/dev/null | jq -e '.BackendState == "Running"' >/dev/null 2>&1; then
  printf '%s\n' '{"text":" ","class":"connected","tooltip":"Tailscale connected"}'
else
  printf '%s\n' '{"text":" ","class":"disconnected","tooltip":"Tailscale disconnected"}'
fi
