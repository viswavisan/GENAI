"""
Gmail Model Context Protocol (MCP) Client & Autonomous Agent.

Connects to the Gmail MCP Server, manages tool execution, resource queries,
and powers the Autonomous Gmail AI Assistant.
"""

import os
import json
import asyncio
from typing import Dict, Any, List
from .gmail_mcp_server import (
    gmail_mcp_server,
    get_unread_count,
    search_emails,
    read_email,
    send_email,
    create_draft,
    get_sent_emails,
    delete_email,
    get_inbox_emails,
    list_inbox_emails,
    get_credentials
)



try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def get_gmail_mcp_catalog() -> Dict[str, Any]:
    """Inspects the Gmail MCP Server and returns registered tools, resources, and prompts."""
    async def _fetch():
        tools_list = await gmail_mcp_server.list_tools()
        resources_list = await gmail_mcp_server.list_resources()
        prompts_list = await gmail_mcp_server.list_prompts()

        tools = []
        for t in tools_list:
            tools.append({
                "name": t.name,
                "description": t.description or "No description provided",
                "schema": getattr(t, "inputSchema", {}),
            })

        resources = []
        for r in resources_list:
            resources.append({
                "uri": str(r.uri),
                "name": r.name,
                "description": r.description or "No description provided",
                "mimeType": getattr(r, "mimeType", "text/plain"),
            })

        prompts = []
        for p in prompts_list:
            prompts.append({
                "name": p.name,
                "description": p.description or "No description provided",
                "arguments": [
                    {
                        "name": a.name,
                        "description": getattr(a, "description", ""),
                        "required": getattr(a, "required", False)
                    }
                    for a in (getattr(p, "arguments", None) or [])
                ],
            })

        try:
            user, _ = get_credentials()
        except Exception:
            user = "Not configured"

        return {
            "server_name": gmail_mcp_server.name,
            "version": gmail_mcp_server.version,
            "account": user,
            "tools": tools,
            "resources": resources,
            "prompts": prompts,
        }

    return asyncio.run(_fetch())



def call_gmail_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a Gmail MCP tool and formats the standard JSON-RPC 2.0 wire protocol messages.
    """
    rpc_request = {
        "jsonrpc": "2.0",
        "id": 201,
        "method": "tools/call",
        "params": {
            "name": name,
            "arguments": arguments
        }
    }

    async def _call():
        res = await gmail_mcp_server.call_tool(name, arguments)
        text_content = ""
        structured = getattr(res, "structured_content", None)
        if hasattr(res, "content") and res.content:
            text_content = "\n".join(getattr(c, "text", str(c)) for c in res.content)

        # Pretty-print structured results if available
        if structured:
            res_val = structured.get("result") if isinstance(structured, dict) else structured
            if name == "read_email" and isinstance(res_val, dict) and "subject" in res_val:
                text_content = (
                    f"Subject: {res_val.get('subject', '')}\n"
                    f"From: {res_val.get('sender', '')}\n"
                    f"To: {res_val.get('recipient', '')}\n"
                    f"Date: {res_val.get('timestamp', '')}\n\n"
                    f"{res_val.get('body', '')}"
                )
            elif not text_content:
                if isinstance(res_val, list):
                    lines = []
                    for item in res_val:
                        if isinstance(item, dict):
                            lines.append(f"- [ID: {item.get('id', '')}] {item.get('sender', '')}: {item.get('subject', '')}")
                        else:
                            lines.append(f"- {str(item)}")
                    text_content = "\n".join(lines)
                elif isinstance(res_val, dict):
                    text_content = "\n".join(f"{k}: {v}" for k, v in res_val.items())

        output_val = text_content or str(structured)

        rpc_response = {
            "jsonrpc": "2.0",
            "id": 201,
            "result": {
                "content": [{"type": "text", "text": output_val}],
                "isError": getattr(res, "is_error", False)
            }
        }

        return {
            "tool": name,
            "arguments": arguments,
            "output": output_val,
            "structured": structured,
            "is_error": getattr(res, "is_error", False),
            "rpc_request": rpc_request,
            "rpc_response": rpc_response,
        }

    return asyncio.run(_call())


def read_gmail_resource(uri: str) -> Dict[str, Any]:
    """Reads a Gmail resource by URI and captures the JSON-RPC wire request/response."""
    rpc_request = {
        "jsonrpc": "2.0",
        "id": 202,
        "method": "resources/read",
        "params": {"uri": uri}
    }

    async def _read():
        contents = await gmail_mcp_server.read_resource(uri)
        raw_text = "\n".join(getattr(c, "content", str(c)) for c in contents)
        rpc_response = {
            "jsonrpc": "2.0",
            "id": 202,
            "result": {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "text/plain",
                        "text": raw_text
                    }
                ]
            }
        }
        return {
            "uri": uri,
            "content": raw_text,
            "rpc_request": rpc_request,
            "rpc_response": rpc_response,
        }

    return asyncio.run(_read())


def get_gmail_prompt_template(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Fetches a Gmail prompt template."""
    rpc_request = {
        "jsonrpc": "2.0",
        "id": 203,
        "method": "prompts/get",
        "params": {"name": name, "arguments": arguments}
    }

    async def _prompt():
        res = await gmail_mcp_server.get_prompt(name, arguments)
        messages = []
        for m in getattr(res, "messages", []):
            txt = getattr(getattr(m, "content", None), "text", str(m.content))
            messages.append({"role": getattr(m, "role", "user"), "content": txt})

        rpc_response = {
            "jsonrpc": "2.0",
            "id": 203,
            "result": {
                "description": getattr(res, "description", ""),
                "messages": messages
            }
        }
        return {
            "name": name,
            "description": getattr(res, "description", ""),
            "messages": messages,
            "rpc_request": rpc_request,
            "rpc_response": rpc_response,
        }

    return asyncio.run(_prompt())


def run_gmail_agent(user_input: str) -> Dict[str, Any]:
    """
    Autonomous Gmail AI Assistant powered by Gmail MCP tools.
    Connects to the Gmail MCP Server dynamically over JSON-RPC 2.0.
    """
    api_key = os.getenv("GEMINI_API_KEY")

    # If Gemini is configured, use Autonomous Function Calling with Gmail MCP tools
    if api_key and HAS_GENAI:
        try:
            client = genai.Client(api_key=api_key)
            tools_list = [get_unread_count, search_emails, read_email, send_email, create_draft, get_sent_emails, delete_email, get_inbox_emails]

            chat = client.chats.create(
                model=MODEL_NAME,
                config={
                    "tools": tools_list,
                    "system_instruction": (
                        "You are an intelligent executive email assistant connected to Gmail via the "
                        "Model Context Protocol (MCP). Always choose the appropriate Gmail MCP tool "
                        "(get_unread_count, search_emails, read_email, send_email, create_draft, get_sent_emails, delete_email, get_inbox_emails) to fulfill user requests. "
                        "When the user asks to see inbox emails, recent emails, or list messages, use get_inbox_emails(max_results=8). "
                        "When the user asks to see outbox, sent emails, or recent sent messages, use get_sent_emails(max_results=8). "
                        "When the user asks for unread emails, use search_emails(query='is:unread', max_results=8). "
                        "When the user asks 'how many unread messages' or checks count, use get_unread_count(). "
                        "When the user asks to delete or remove an email, use delete_email(message_id). "
                        "Format responses clearly with bullet points and summaries."
                    )
                }
            )


            response = chat.send_message(user_input)
            history = chat.get_history()

            steps = []
            rpc_trace = []
            returned_emails = []
            pagination_meta = None

            for msg in history:
                for part in msg.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        call_name = part.function_call.name
                        call_args = dict(part.function_call.args or {})
                        rpc_request = {
                            "jsonrpc": "2.0",
                            "method": "tools/call",
                            "params": {"name": call_name, "arguments": call_args}
                        }
                        steps.append({
                            "tool": call_name,
                            "args": call_args,
                            "output": "Executing via Gmail MCP Server"
                        })
                        rpc_trace.append({"type": "request", "data": rpc_request})

                    if hasattr(part, "function_response") and part.function_response:
                        resp_dict = dict(part.function_response.response or {})
                        res_val = resp_dict.get("result", str(resp_dict))
                        if steps:
                            steps[-1]["output"] = res_val

                        # Extract structured email list and pagination if returned
                        if isinstance(res_val, list) and res_val:
                            if isinstance(res_val[0], dict) and ("id" in res_val[0] or "subject" in res_val[0]):
                                returned_emails = res_val
                        elif isinstance(res_val, dict) and "emails" in res_val and isinstance(res_val["emails"], list):
                            returned_emails = res_val["emails"]
                            pagination_meta = {
                                "page": res_val.get("page", 1),
                                "total_pages": res_val.get("total_pages", 1),
                                "total_count": res_val.get("total_count", len(returned_emails)),
                                "start_index": res_val.get("start_index", 1),
                                "end_index": res_val.get("end_index", len(returned_emails)),
                                "has_next": res_val.get("has_next", False),
                                "has_prev": res_val.get("has_prev", False),
                                "folder": res_val.get("folder", "inbox")
                            }

                        rpc_response = {
                            "jsonrpc": "2.0",
                            "result": {"content": [{"type": "text", "text": str(res_val)}]}
                        }
                        rpc_trace.append({"type": "response", "data": rpc_response})

            return {
                "reply": response.text or "Processed via Gmail MCP tools.",
                "steps": steps,
                "emails": returned_emails,
                "pagination": pagination_meta,
                "rpc_trace": rpc_trace,
                "mode": "gemini_gmail_mcp",
                "type": "gmail_mcp_agent"
            }
        except Exception:
            # Fall back to heuristic handler if API quota or error occurs
            pass

    # Heuristic / Local Fallback Gmail Agent
    import re
    q_lower = user_input.lower()
    steps = []
    rpc_trace = []
    returned_emails = []
    pagination_meta = None
    reply = ""

    # Extract requested page number if specified
    req_page = 1
    page_match = re.search(r'\bpage\s+(\d+)\b', q_lower)
    if page_match:
        req_page = max(1, int(page_match.group(1)))
    elif any(k in q_lower for k in ["next", "older", "more"]):
        req_page = 2

    # Extract email address if present
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    found_emails = re.findall(email_pattern, user_input)
    target_email = found_emails[0] if found_emails else ""

    # Check for send/compose email intent
    if target_email and any(k in q_lower for k in ["send", "compose", "dispatch", "write to", "mail to"]):
        # Extract subject
        subject = "Project Update from Viswa"
        subj_match = re.search(r'(?:with\s+)?subject[:\s]+["\']?([^"\'\n,\.]+?)["\']?(?:\s+(?:and|with)\s+body|\s+saying|\s+message|$)', user_input, re.IGNORECASE)
        if not subj_match:
            subj_match = re.search(r'\babout\s+([^,;\.\n]+?)(?:\s+(?:and|with)\s+body|\s+saying|\s+message|$)', user_input, re.IGNORECASE)
        if subj_match:
            subject = subj_match.group(1).strip()

        # Extract body
        body = "Hi Viswa,\n\nHope you are doing well.\nHere is the project update we discussed.\n\nBest regards,\nViswa"
        body_match = re.search(r'(?:with\s+)?(?:body|message|saying|content)[:\s]+["\']?([^"\'\n]+?)["\']?$', user_input, re.IGNORECASE)
        if body_match:
            body = body_match.group(1).strip()

        res = call_gmail_tool("send_email", {"recipient": target_email, "subject": subject, "body": body})
        steps.append({"tool": "send_email", "args": {"recipient": target_email, "subject": subject, "body": body}, "output": res["output"]})
        rpc_trace.extend([{"type": "request", "data": res["rpc_request"]}, {"type": "response", "data": res["rpc_response"]}])
        
        reply = (
            f"✅ **Email Sent Successfully via Gmail MCP Server!**\n\n"
            f"- **Recipient**: `{target_email}`\n"
            f"- **Subject**: {subject}\n"
            f"- **Body**: {body}\n\n"
            f"*Dispatched directly through Gmail SMTP (Port 465).*"
        )

    # Check for draft creation intent
    elif target_email and any(k in q_lower for k in ["draft", "save draft"]):
        subject = "Draft: Update from Gmail MCP"
        subj_match = re.search(r'subject[:\s]+["\']?([^"\'\n,\.]+?)["\']?', user_input, re.IGNORECASE)
        if subj_match:
            subject = subj_match.group(1).strip()
        body = "Hi, this is a draft saved via the Gmail MCP Server."
        body_match = re.search(r'(?:body|message|content)[:\s]+["\']?([^"\'\n]+?)["\']?', user_input, re.IGNORECASE)
        if body_match:
            body = body_match.group(1).strip()

        res = call_gmail_tool("create_draft", {"recipient": target_email, "subject": subject, "body": body})
        steps.append({"tool": "create_draft", "args": {"recipient": target_email, "subject": subject, "body": body}, "output": res["output"]})
        rpc_trace.extend([{"type": "request", "data": res["rpc_request"]}, {"type": "response", "data": res["rpc_response"]}])
        reply = f"📝 **Draft Saved in Gmail Drafts Folder!**\n\n- **Recipient**: `{target_email}`\n- **Subject**: {subject}"

    # Check for deleting an email
    elif any(k in q_lower for k in ["delete", "remove", "trash"]) and re.search(r'\b\d+\b', user_input):
        found_id = re.search(r'\b\d+\b', user_input).group(0)
        res = call_gmail_tool("delete_email", {"message_id": found_id})
        steps.append({"tool": "delete_email", "args": {"message_id": found_id}, "output": res["output"]})
        rpc_trace.extend([{"type": "request", "data": res["rpc_request"]}, {"type": "response", "data": res["rpc_response"]}])
        reply = f"🗑️ **Email #{found_id} Deleted via Gmail MCP!**\n\n{res['output']}"

    # Check for reading a specific email by numeric ID
    elif any(k in q_lower for k in ["read", "open", "view"]) and re.search(r'\b\d+\b', user_input):
        found_id = re.search(r'\b\d+\b', user_input).group(0)
        res = call_gmail_tool("read_email", {"message_id": found_id})
        steps.append({"tool": "read_email", "args": {"message_id": found_id}, "output": res["output"]})
        rpc_trace.extend([{"type": "request", "data": res["rpc_request"]}, {"type": "response", "data": res["rpc_response"]}])
        
        # Parse email dict
        email_info = None
        if isinstance(res.get("structured"), dict) and "result" in res["structured"]:
            email_info = res["structured"]["result"]
        elif isinstance(res.get("structured"), dict):
            email_info = res["structured"]
        else:
            try:
                email_info = json.loads(res.get("output", "{}"))
            except Exception:
                email_info = None

        if isinstance(email_info, dict) and "subject" in email_info:
            subject = email_info.get("subject", "(No Subject)")
            sender = email_info.get("sender", "Unknown")
            recipient = email_info.get("recipient", "")
            date_val = email_info.get("timestamp", "")
            body = email_info.get("body", "").strip()

            reply = (
                f"### ✉️ {subject}\n\n"
                f"**From:** {sender}  \n"
                f"**To:** {recipient}  \n"
                f"**Date:** {date_val}  \n\n"
                f"---\n\n"
                f"{body}"
            )
        else:
            reply = res["output"]

    # Check for inbox emails
    elif any(k in q_lower for k in ["show inbox", "inbox", "recent emails", "check inbox", "my emails", "older emails", "next emails"]):
        res = call_gmail_tool("get_inbox_emails", {"max_results": 8, "page": req_page})
        steps.append({"tool": "get_inbox_emails", "args": {"max_results": 8, "page": req_page}, "output": res["output"]})
        rpc_trace.extend([{"type": "request", "data": res["rpc_request"]}, {"type": "response", "data": res["rpc_response"]}])
        structured = res.get("structured", {}).get("result") if isinstance(res.get("structured"), dict) else res.get("structured")
        if isinstance(structured, dict) and "emails" in structured:
            returned_emails = structured["emails"]
            pagination_meta = structured
        elif isinstance(structured, list):
            returned_emails = structured
        reply = f"Here are the emails from your **Inbox** (Page {req_page}) retrieved via Gmail MCP:"

    # Check for unread emails / unread count
    elif any(k in q_lower for k in ["unread", "unseen", "how many"]):
        if any(k in q_lower for k in ["how many", "count"]):
            res = call_gmail_tool("get_unread_count", {})
            steps.append({"tool": "get_unread_count", "args": {}, "output": res["output"]})
            rpc_trace.extend([{"type": "request", "data": res["rpc_request"]}, {"type": "response", "data": res["rpc_response"]}])
            reply = f"📬 **Live Unread Count via Gmail MCP**:\n\n{res['output']}"
        else:
            res = call_gmail_tool("search_emails", {"query": "is:unread", "max_results": 8})
            steps.append({"tool": "search_emails", "args": {"query": "is:unread", "max_results": 8}, "output": res["output"]})
            rpc_trace.extend([{"type": "request", "data": res["rpc_request"]}, {"type": "response", "data": res["rpc_response"]}])
            structured = res.get("structured", {}).get("result") if isinstance(res.get("structured"), dict) else res.get("structured")
            if isinstance(structured, list):
                returned_emails = structured
            reply = "Here are your **Unread Emails** in Gmail retrieved via Gmail MCP:"

    # Check for outbox / sent emails
    elif any(k in q_lower for k in ["outbox", "sent", "sent emails", "sent mail"]):
        res = call_gmail_tool("get_sent_emails", {"max_results": 8, "page": req_page})
        steps.append({"tool": "get_sent_emails", "args": {"max_results": 8, "page": req_page}, "output": res["output"]})
        rpc_trace.extend([{"type": "request", "data": res["rpc_request"]}, {"type": "response", "data": res["rpc_response"]}])
        structured = res.get("structured", {}).get("result") if isinstance(res.get("structured"), dict) else res.get("structured")
        if isinstance(structured, dict) and "emails" in structured:
            returned_emails = structured["emails"]
            pagination_meta = structured
        elif isinstance(structured, list):
            returned_emails = structured
        reply = f"Here are the emails from your **Outbox (Sent Mail)** (Page {req_page}) retrieved via Gmail MCP:"

    # Check for inbox search
    elif any(k in q_lower for k in ["search", "find", "filter", "lookup"]):
        clean_q = re.sub(r'\b(search|find|check|my|emails|email|in|inbox|about|from|for|please|look|up)\b', '', q_lower).strip()
        res = call_gmail_tool("search_emails", {"query": clean_q, "max_results": 8})
        steps.append({"tool": "search_emails", "args": {"query": clean_q, "max_results": 8}, "output": res["output"]})
        rpc_trace.extend([{"type": "request", "data": res["rpc_request"]}, {"type": "response", "data": res["rpc_response"]}])
        structured = res.get("structured", {}).get("result") if isinstance(res.get("structured"), dict) else res.get("structured")
        if isinstance(structured, list):
            returned_emails = structured
        reply = f"Here are the emails matching **'{clean_q}'** retrieved via Gmail MCP:"

    elif any(k in q_lower for k in ["stats", "telemetry", "account"]):
        res = read_gmail_resource("gmail://inbox/stats")
        steps.append({"tool": "resources/read", "args": {"uri": "gmail://inbox/stats"}, "output": res["content"]})
        rpc_trace.extend([{"type": "request", "data": res["rpc_request"]}, {"type": "response", "data": res["rpc_response"]}])
        reply = f"Live Gmail Account Stats:\n\n{res['content']}"

    else:
        reply = (
            "👋 Welcome to the **Gmail MCP Assistant**!\n\n"
            "I interact directly with your real Gmail account using standard **Model Context Protocol** tools:\n"
            "- 📥 *'Show recent emails from my inbox'*\n"
            "- 📤 *'Show recent sent emails from my outbox'*\n"
            "- 📬 *'Show unread emails'*\n"
            "- 🔍 *'Search emails with keyword \"Google\"'*\n"
            "- 📖 *'Read email 5727'* (invokes `read_email` with message ID)\n"
            "- ✉️ *'Send a sample email to user@example.com'* (invokes `send_email`)\n"
            "- 📊 *'Show inbox stats'* (queries `gmail://inbox/stats`)"
        )

    return {
        "reply": reply,
        "steps": steps,
        "emails": returned_emails,
        "pagination": pagination_meta,
        "rpc_trace": rpc_trace,
        "mode": "offline_gmail_mcp",
        "type": "gmail_mcp_agent"
    }
