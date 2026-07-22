#!/bin/bash
# Validate both config files
set -e
cd "$(dirname "$0")/.."
[ -d "venv" ] && source venv/bin/activate

echo "=== Config Validation ==="
echo ""

for cfg in orchestrator/config/agents.yaml agentic_team/config/agents.yaml; do
    echo "Checking $cfg..."
    python3 - "$cfg" << 'PYEOF'
import yaml, sys
cfg_path = sys.argv[1]
with open(cfg_path) as f:
    c = yaml.safe_load(f)
for section in ["agents", "workflows", "settings"]:
    if section not in c:
        print("  MISSING: " + section)
        sys.exit(1)
agents = [k for k, v in c.get("agents", {}).items()
          if isinstance(v, dict) and v.get("enabled", True)]
workflows = list(c.get("workflows", {}).keys())
print("  Agents:    {} enabled ({})".format(len(agents), ", ".join(agents)))
print("  Workflows: {} ({})".format(len(workflows), ", ".join(workflows)))
print("  OK")
PYEOF
    echo ""
done
