"""Agent-facing interfaces for AndroGuard.

The package deliberately keeps the protocol layer small and dependency-light:
``HeadlessAPI`` exposes the existing skills as typed tools, while
``UIAgentController`` provides a control surface for the terminal UI.
"""

from androguard.agent.headless import HeadlessAPI
from androguard.agent.protocol import AgentError, ToolRegistry, ToolSpec
from androguard.agent.ui import UIAgentController


def build_agent_api(include_ui: bool = False) -> HeadlessAPI:
    """Build a headless API, optionally including GUI automation tools.

    The default is a dependency-light, pure headless API.  Set ``include_ui``
    to expose the ``ui.*`` tools used to automate the terminal UI.
    """
    return HeadlessAPI(include_ui=include_ui)


__all__ = [
    "AgentError",
    "HeadlessAPI",
    "ToolRegistry",
    "ToolSpec",
    "UIAgentController",
    "build_agent_api",
]
