"""Entry point for python -m context_dashboard."""

import os

from context_dashboard.app import _auto_seed_if_empty, app

_auto_seed_if_empty()
host = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
port = int(os.environ.get("DASHBOARD_PORT", "5003"))
debug = os.environ.get("DASHBOARD_DEBUG", "false").lower() in ("true", "1", "yes")
app.run(host=host, port=port, debug=debug)
