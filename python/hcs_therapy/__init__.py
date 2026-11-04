"""HCS Therapy Studio — local-first wellbeing, psychoeducation and research runtime.

Public contract: this package holds the *infrastructure* layer only. It never
contains clinical logic and never phones home. Every entry point is local.
"""

from __future__ import annotations

__all__ = ["__version__", "PRODUCT_NAME", "CREDIT"]

__version__ = "0.1.0"

PRODUCT_NAME = "HCS Therapy Studio"
CREDIT = "Made with love by hcsmedia and timfromhcs"
PACKAGE_DIST_NAME = "hcs-therapy-core"
IMPORT_NAMESPACE = "hcs_therapy"
CLI_NAME = "hcs-therapy"
MCP_COMMAND = "hcs-therapy-mcp"
