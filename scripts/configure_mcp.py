"""Back up Codex configuration and append only missing requested MCP servers."""
from datetime import datetime, timezone
from pathlib import Path
import os
import tomllib

path = Path.home() / ".codex" / "config.toml"
original = path.read_bytes()
existing = tomllib.loads(original.decode("utf-8-sig"))
servers = {
    "context7": 'command = "npx"\nargs = ["-y", "@upstash/context7-mcp"]\nstartup_timeout_sec = 120\n',
    "playwright": 'command = "npx"\nargs = ["-y", "@playwright/mcp@latest"]\nstartup_timeout_sec = 120\n',
    "shadcn": 'command = "npx"\nargs = ["-y", "shadcn@latest", "mcp"]\nstartup_timeout_sec = 120\n',
    "github": 'url = "https://api.githubcopilot.com/mcp/"\nbearer_token_env_var = "GITHUB_PAT"\n',
}
missing = {name: value for name, value in servers.items() if name not in existing.get("mcp_servers", {})}
if not missing:
    print("No changes: all requested server names already exist.")
    raise SystemExit(0)
suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
backup = path.with_name(f"config.toml.agent-bazaar.{suffix}.bak")
with backup.open("xb") as file:
    file.write(original)
candidate = original.decode("utf-8-sig").rstrip() + "\n\n" + "\n".join(
    f"[mcp_servers.{name}]\n{value}" for name, value in missing.items()
)
parsed = tomllib.loads(candidate)
for name, value in existing.items():
    if name != "mcp_servers":
        assert parsed[name] == value, f"Existing setting changed: {name}"
for name, value in existing.get("mcp_servers", {}).items():
    assert parsed["mcp_servers"][name] == value, f"Existing MCP changed: {name}"
temporary = path.with_name(f"config.toml.agent-bazaar.{suffix}.tmp")
temporary.write_text(candidate, encoding="utf-8", newline="\n")
os.replace(temporary, path)
print(f"Backup: {backup}")
print("Added: " + ", ".join(missing))
print("Validated TOML; preserved all pre-existing settings and servers.")
