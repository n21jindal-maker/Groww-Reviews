import asyncio
from src.delivery.mcp_client import MCPLangChainWrapper

async def main():
    sse_url = "https://mcp-server-production-acc6.up.railway.app/mcp/sse"
    wrapper = MCPLangChainWrapper(sse_url)
    await wrapper.connect()
    
    tools = await wrapper.get_tools()
    print(f"Available tools:")
    for t in tools:
        print(f"- {t.name}: {t.description}")
        print(f"  schema: {t.args_schema.schema()}")
    
    await wrapper.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
