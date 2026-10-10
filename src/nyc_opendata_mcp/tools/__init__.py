"""MCP tool and resource modules for NYC Open Data.

Importing these submodules registers tools/resources on the shared
``app.mcp`` MCPServer instance via decorator side-effects.
"""

# Import all tool modules to register them
from . import (
    catalog,
    datastore,
    geo,
    government,
    mobility,
    realtime,
    waste_intel,
    waste_datasets,
)
