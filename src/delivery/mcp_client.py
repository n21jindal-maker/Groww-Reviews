import asyncio
from typing import List, Callable, Any
from langchain_core.tools import StructuredTool
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
from pydantic import create_model, Field
import json

class MCPLangChainWrapper:
    def __init__(self, sse_url: str):
        self.sse_url = sse_url
        self._exit_stack = None
        self.session = None

    async def connect(self):
        from contextlib import AsyncExitStack
        self._exit_stack = AsyncExitStack()
        
        # Connect to the SSE endpoint
        streams = await self._exit_stack.enter_async_context(sse_client(self.sse_url))
        read_stream, write_stream = streams
        
        # Initialize session
        self.session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
        await self.session.initialize()

    async def get_tools(self) -> List[StructuredTool]:
        """Fetch MCP tools and wrap them as LangChain tools."""
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")
            
        result = await self.session.list_tools()
        tools = []
        
        for mcp_tool in result.tools:
            name = mcp_tool.name
            description = mcp_tool.description or ""
            input_schema = mcp_tool.inputSchema
            
            # Create a Pydantic model for the tool args based on JSON schema
            fields = {}
            properties = input_schema.get("properties", {})
            required = input_schema.get("required", [])
            
            for prop_name, prop_details in properties.items():
                prop_type_str = prop_details.get("type", "string")
                prop_desc = prop_details.get("description", "")
                
                # Map JSON schema types to Python types
                py_type = str
                if prop_type_str == "integer":
                    py_type = int
                elif prop_type_str == "boolean":
                    py_type = bool
                elif prop_type_str == "array":
                    py_type = list
                
                if prop_name in required:
                    fields[prop_name] = (py_type, Field(..., description=prop_desc))
                else:
                    fields[prop_name] = (py_type, Field(None, description=prop_desc))
                    
            ArgsSchema = create_model(f"{name}Args", **fields)
            
            # Create the dynamic function
            def create_tool_func(tool_name):
                async def tool_func(**kwargs) -> str:
                    try:
                        response = await self.session.call_tool(tool_name, arguments=kwargs)
                        if response.isError:
                            return f"Error: {response.content}"
                        result_text = []
                        for content in response.content:
                            if content.type == "text":
                                result_text.append(content.text)
                            else:
                                result_text.append(str(content))
                        return "\n".join(result_text)
                    except Exception as e:
                        return f"Execution error: {str(e)}"
                return tool_func

            lc_tool = StructuredTool.from_function(
                func=create_tool_func(name),
                coroutine=create_tool_func(name),
                name=name,
                description=description,
                args_schema=ArgsSchema
            )
            tools.append(lc_tool)
            
        return tools

    async def disconnect(self):
        if self._exit_stack:
            await self._exit_stack.aclose()
            self.session = None
