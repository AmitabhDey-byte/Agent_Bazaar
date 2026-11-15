"""Run each available phase gate; missing implementations are BLOCKED, never passing."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[1]
forge = shutil.which("forge") or str(Path.home() / ".foundry/bin" / ("forge.exe" if os.name == "nt" else "forge"))
python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
checks = [
    ("forge test", [forge, "test", "--root", str(root / "contracts")], root / "contracts/foundry.toml"),
    ("pytest", [str(python), "-m", "pytest", "api/tests", "-q"], root / "api/tests"),
    ("next build", [shutil.which("node") or "node", str(root / "web/node_modules/next/dist/bin/next"), "build", "web"], root / "web/package.json"),
    ("playwright smoke", [shutil.which("node") or "node", str(root / "node_modules/@playwright/test/cli.js"), "test", "--config=playwright.config.ts"], root / "playwright.config.ts"),
]
results = []
for label, command, required in checks:
    if not required.exists():
        result = {"check": label, "status": "blocked", "reason": f"Implementation missing: {required.relative_to(root)}"}
    else:
        try:
            completed = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=600)
            result = {"check": label, "status": "passed" if completed.returncode == 0 else "failed", "exit_code": completed.returncode, "output": completed.stdout + completed.stderr}
        except (OSError, subprocess.TimeoutExpired) as error:
            result = {"check": label, "status": "failed", "reason": str(error)}
    results.append(result)
    print(f"{label}: {result['status']} - {result.get('reason', result.get('output', '').strip())}", flush=True)
destination = root / "docs/phase-checks.json"
destination.parent.mkdir(exist_ok=True)
destination.write_text(json.dumps({"checked_at": datetime.now(timezone.utc).isoformat(), "checks": results}, indent=2) + "\n", encoding="utf-8")
sys.exit(int(any(item["status"] != "passed" for item in results)))
