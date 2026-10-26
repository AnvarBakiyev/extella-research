from mcp.server.mcpserver import MCPServer
from solver import solve

mcp = MCPServer("gsm-solver")

@mcp.tool()
def solve_gsm(question: str) -> dict:
    """Solve a grade-school math word problem; returns the numeric answer."""
    return solve(question)

if __name__ == "__main__":
    mcp.run()
