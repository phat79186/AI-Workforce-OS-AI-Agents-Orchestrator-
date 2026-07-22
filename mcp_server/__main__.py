"""Allow ``python -m mcp_server`` to start the server or the REPL.

Usage:
    python -m mcp_server          # start the MCP server (default)
    python -m mcp_server repl     # start the interactive REPL
"""

import sys

if len(sys.argv) > 1 and sys.argv[1] == "repl":
    from mcp_server.repl import main

    main()
else:
    import runpy

    from mcp_server.server import *  # noqa: F401,F403

    runpy.run_module("mcp_server.server", run_name="__main__", alter_sys=True)
