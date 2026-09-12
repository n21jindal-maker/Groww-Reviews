import os
import sys
import io
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from src.delivery.mcp_client import MCPLangChainWrapper

async def run_delivery_agent(pulse_md: str, config: Dict[str, Any]):
    """
    Connects to the remote MCP server, gets delivery tools (Google Docs, Gmail),
    and executes the delivery tasks using an LLM agent.
    """
    # Reconfigure stdout for UTF-8 so emoji in pulse don't crash on Windows
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    mcp_config = config.get("mcp", {})
    sse_url = mcp_config.get("sse_url")
    doc_id = mcp_config.get("document_id")
    
    email_config = config.get("email", {})
    to_email = email_config.get("to")
    subject = email_config.get("subject_prefix", "Groww Weekly Pulse")
    
    if not sse_url:
        print("Error: MCP sse_url not found in config.")
        return
        
    wrapper = MCPLangChainWrapper(sse_url)
    
    try:
        print(f"Connecting to MCP server at {sse_url}...")
        await wrapper.connect()
        tools = await wrapper.get_tools()
        print(f"Retrieved {len(tools)} tools from MCP server.")
        
        # Use gemini-3.6-flash or whatever is configured for the generator
        gemini_config = config.get("gemini", {})
        model_name = gemini_config.get("model", "gemini-3.6-flash")
        
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.1
        )
        
        prompt_text = f"""You are an autonomous delivery agent. Your job is to publish a Weekly Pulse report using the provided tools.

Please deliver the following Weekly Pulse report.

Task 1: Append the report to the Google Document with ID: {doc_id}
Task 2: Create a draft email to {to_email} with the subject "{subject}".
The body of the email should contain the pulse report AND a link to the Google Doc: https://docs.google.com/document/d/{doc_id}/edit

Report Content:
{pulse_md}
"""
        
        agent_executor = create_react_agent(llm, tools)
        
        print("Starting delivery agent...")
        result = await agent_executor.ainvoke({
            "messages": [("user", prompt_text)]
        })
        
        print("\nDelivery complete!")
        last_message = result.get("messages", [])[-1] if "messages" in result else None
        if last_message:
            print(last_message.content)
        
    except Exception as e:
        print(f"Delivery failed: {e}")
        print("Fallback: Pulse could not be delivered automatically.")
    finally:
        await wrapper.disconnect()
