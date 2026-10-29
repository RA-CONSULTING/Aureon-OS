"""Public read-only MCP server. Outside models call these tools. They do not become the reasoning."""

__all__ = ["SERVER_INSTRUCTIONS"]

SERVER_INSTRUCTIONS = (
    "MCP lets outside models call Aureon's tools. "
    "No outside model or API becomes Aureon's reasoning. "
    "The cognition runs in Aureon's own code. "
    "This server is read-only. It does not place orders, read keys, start circulation, "
    "self-code, self-repair, or write the repository or state/."
)
