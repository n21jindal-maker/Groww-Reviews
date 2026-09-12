import os
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from src.delivery.mcp_client import MCPLangChainWrapper

async def run_delivery_agent(pulse_md: str, config: Dict[str, Any]):
    """
    Connects to the remote MCP server, gets delivery tools (Google Docs, Gmail),
    and executes the delivery tasks using an LLM agent.
    """
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
        
        from langchain_core.prompts import MessagesPlaceholder
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an autonomous delivery agent. Your job is to publish a Weekly Pulse report using the provided tools."),
            ("user", """
Please deliver the following Weekly Pulse report.

Task 1: Append the report to the Google Document with ID: {doc_id}
Task 2: Create a draft email to {to_email} with the subject "{subject}".
The body of the email should contain the pulse report AND a link to the Google Doc: https://docs.google.com/document/d/{doc_id}/edit

Report Content:
{pulse}
"""),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        agent = create_tool_calling_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        
        print("Starting delivery agent...")
        result = await agent_executor.ainvoke({
            "doc_id": doc_id,
            "to_email": to_email,
            "subject": subject,
            "pulse": pulse_md
        })
        
        print("\nDelivery complete!")
        print(result.get("output", ""))
        
    except Exception as e:
        print(f"Delivery failed: {e}")
        print("Fallback: Pulse could not be delivered automatically.")
    finally:
        await wrapper.disconnect()
