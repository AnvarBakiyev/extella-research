"""Потребитель «чат-агент»: стандартный MCP-клиент по stdio вызывает инструмент solve_gsm."""
import asyncio, json, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main(q):
    p = StdioServerParameters(command=sys.executable, args=["mcp_server.py"])
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool("solve_gsm", {"question": q})
            print(res.content[0].text)

asyncio.run(main(sys.argv[1]))
