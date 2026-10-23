"""
Clean, modular views for GenAI Studio.
Separated into 3 clear functional groups:
1. GenAI Chat (Online Gemini & Offline Ollama)
2. Agentic AI Online (Limited Tools & Universal Terminal with Confirmation/Password)
3. Agentic AI Offline (Local Ollama Tool-Calling Agent)
"""

from django.shortcuts import render
from django.http import JsonResponse

# Group 1: GenAI Chat
from .backends.genai_chat import (
    generate_online_chat,
    generate_offline_chat
)

# Group 2: Agentic AI Online
from .backends.agentic_online import (
    run_online_limited_agent,
    ONLINE_LIMITED_TOOLS_METADATA,
    propose_universal_action,
    execute_confirmed_command
)

# Group 3: Agentic AI Offline
from .backends.agentic_offline import (
    run_offline_agent,
    OFFLINE_TOOLS_METADATA
)


# =====================================================================
# GROUP 1: GENAI CHAT (Conversational LLM - No Tools)
# =====================================================================

def chat_online_ui(request):
    """GenAI Online Chat interface (Google Gemini)."""
    return render(request, "chat/genai_online.html")


def chat_online_api(request):
    """API for GenAI Online Chat."""
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"error": "No input provided"}, status=400)
    try:
        return JsonResponse(generate_online_chat(q))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def chat_offline_ui(request):
    """GenAI Offline Chat interface (Local Ollama)."""
    return render(request, "chat/genai_offline.html")


def chat_offline_api(request):
    """API for GenAI Offline Chat."""
    q = request.GET.get("q", "").strip()
    model = request.GET.get("model", "llama3.2").strip()
    if not q:
        return JsonResponse({"error": "No input provided"}, status=400)
    try:
        return JsonResponse(generate_offline_chat(q, model_name=model))
    except ConnectionError as e:
        return JsonResponse({"error": str(e)}, status=503)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# =====================================================================
# GROUP 2: AGENTIC AI ONLINE (Cloud Gemini with Autonomous Tools)
# =====================================================================

def agent_online_limited_ui(request):
    """Agentic AI Online (Limited safe tools: clock, calc, weather, brightness)."""
    return render(request, "chat/agent_online_limited.html", {
        "tools": ONLINE_LIMITED_TOOLS_METADATA
    })


def agent_online_limited_api(request):
    """API for Agentic AI Online (Limited Tools)."""
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"error": "No prompt provided"}, status=400)
    try:
        return JsonResponse(run_online_limited_agent(q))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def agent_online_universal_ui(request):
    """Agentic AI Online (Universal PowerShell terminal with confirmation & password)."""
    return render(request, "chat/agent_online_universal.html")


def agent_online_universal_api(request):
    """API for Agentic AI Online (Universal Terminal with Human Confirmation)."""
    q = request.GET.get("q", "").strip()
    confirmed = request.GET.get("confirmed", "false").lower() == "true"
    command = request.GET.get("command", "").strip()
    password = request.GET.get("password", "").strip()

    if not q:
        return JsonResponse({"error": "No prompt provided"}, status=400)
    try:
        if confirmed and command:
            return JsonResponse(execute_confirmed_command(q, command, password=password))
        return JsonResponse(propose_universal_action(q))
    except PermissionError as e:
        return JsonResponse({"error": str(e), "auth_error": True}, status=403)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# =====================================================================
# GROUP 3: AGENTIC AI OFFLINE (Local Ollama Autonomous Tool Calling)
# =====================================================================

def agent_offline_ui(request):
    """Agentic AI Offline (Local Ollama tool-calling agent, zero internet)."""
    return render(request, "chat/agent_offline.html", {
        "tools": OFFLINE_TOOLS_METADATA
    })


def agent_offline_api(request):
    """API for Agentic AI Offline."""
    q = request.GET.get("q", "").strip()
    model = request.GET.get("model", "llama3.2").strip()
    if not q:
        return JsonResponse({"error": "No prompt provided"}, status=400)
    try:
        return JsonResponse(run_offline_agent(q, model_name=model))
    except ConnectionError as e:
        return JsonResponse({"error": str(e)}, status=503)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# =====================================================================
# GROUP 4: GMAIL MODEL CONTEXT PROTOCOL (Gmail MCP Studio)
# =====================================================================

from .backends.gmail_mcp_client import (
    get_gmail_mcp_catalog,
    call_gmail_tool,
    read_gmail_resource,
    get_gmail_prompt_template,
    run_gmail_agent
)
from .backends.gmail_mcp_server import get_credentials, search_emails, list_inbox_emails, delete_email


def gmail_mcp_ui(request):
    """Gmail MCP Studio Interface."""
    try:
        catalog = get_gmail_mcp_catalog()
    except Exception:
        catalog = {
            "server_name": "Gmail-MCP-Server",
            "version": "1.0.0",
            "account": "Configuration pending or offline",
            "tools": [],
            "resources": [],
            "prompts": [],
        }

    try:
        inbox_data = list_inbox_emails(page=1, page_size=8)
    except Exception:
        inbox_data = {
            "emails": [],
            "total_count": 0,
            "page": 1,
            "total_pages": 1,
            "start_index": 0,
            "end_index": 0
        }

    return render(request, "chat/gmail_mcp.html", {
        "server_name": catalog.get("server_name", "Gmail-MCP-Server"),
        "version": catalog.get("version", "1.0.0"),
        "account": catalog.get("account", "Offline / Pending"),
        "tools": catalog.get("tools", []),
        "resources": catalog.get("resources", []),
        "prompts": catalog.get("prompts", []),
        "sample_emails": inbox_data.get("emails", []),
        "total_emails": inbox_data.get("total_count", 0),
        "page": inbox_data.get("page", 1),
        "total_pages": inbox_data.get("total_pages", 1),
        "start_index": inbox_data.get("start_index", 0),
        "end_index": inbox_data.get("end_index", 0),
    })




def gmail_mcp_api(request):
    """API for Gmail MCP Studio: handles tools, resources, prompts, pagination, and autonomous agent."""
    action = request.GET.get("action", "").strip()

    try:
        if action == "list_emails":
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 8))
            return JsonResponse(list_inbox_emails(page=page, page_size=page_size))

        elif action == "delete_email":
            msg_id = (request.GET.get("id") or request.GET.get("message_id") or "").strip()
            if not msg_id:
                return JsonResponse({"error": "No email ID provided"}, status=400)
            return JsonResponse(delete_email(msg_id))

        elif action == "call_tool":
            tool_name = request.GET.get("name", "").strip()
            args_raw = request.GET.get("args", "{}")
            import json
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except Exception:
                args = {}
            if not tool_name:
                return JsonResponse({"error": "No tool name provided"}, status=400)
            return JsonResponse(call_gmail_tool(tool_name, args))

        elif action == "read_resource":
            uri = request.GET.get("uri", "").strip()
            if not uri:
                return JsonResponse({"error": "No URI provided"}, status=400)
            return JsonResponse(read_gmail_resource(uri))

        elif action == "get_prompt":
            prompt_name = request.GET.get("name", "").strip()
            args_raw = request.GET.get("args", "{}")
            import json
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except Exception:
                args = {}
            if not prompt_name:
                return JsonResponse({"error": "No prompt name provided"}, status=400)
            return JsonResponse(get_gmail_prompt_template(prompt_name, args))

        elif action == "catalog":
            return JsonResponse(get_gmail_mcp_catalog())

        else:
            q = request.GET.get("q", "").strip()
            if not q:
                return JsonResponse({"error": "No query provided"}, status=400)
            return JsonResponse(run_gmail_agent(q))

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# =====================================================================
# GROUP 5: RAG Studio (Retrieval-Augmented Generation)
# =====================================================================
from .backends.rag_service import kb, execute_rag_pipeline


def rag_ui(request):
    """RAG Studio Interface."""
    docs = kb.get_documents_summary()
    return render(request, "chat/rag_studio.html", {
        "documents": docs,
        "total_chunks": len(kb.chunks),
        "total_docs": len(docs),
    })


from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def rag_api(request):
    """API for RAG Studio (query, add_document, list_documents, reset, PDF & text file upload)."""
    import os
    import json
    import uuid
    from django.http.request import RawPostDataException

    # Parse action from GET, POST, or JSON body
    action = request.GET.get("action", "").strip() or request.POST.get("action", "").strip()
    data = {}
    if request.content_type == "application/json":
        try:
            if request.body:
                data = json.loads(request.body.decode("utf-8"))
                if not action and isinstance(data, dict):
                    action = data.get("action", "").strip()
        except (RawPostDataException, Exception):
            data = {}

    if action == "add_document":
        title = (data.get("title") or request.POST.get("title") or "").strip()
        category = (data.get("category") or request.POST.get("category") or "General").strip()
        content = (data.get("content") or request.POST.get("content") or "").strip()

        # Handle uploaded file (PDF, TXT, MD, CSV, etc.)
        uploaded_file = request.FILES.get("file") if hasattr(request, "FILES") else None
        if uploaded_file:
            fname = uploaded_file.name
            if not title:
                # Default title to file name without extension
                title = os.path.splitext(fname)[0].replace("_", " ").replace("-", " ").title()

            ext = os.path.splitext(fname)[1].lower()
            if ext == ".pdf":
                try:
                    import io
                    import pypdf
                    pdf_reader = pypdf.PdfReader(io.BytesIO(uploaded_file.read()))
                    pages_text = []
                    for page_num, page in enumerate(pdf_reader.pages, 1):
                        p_text = page.extract_text() or ""
                        if p_text.strip():
                            pages_text.append(f"[Page {page_num}]\n{p_text.strip()}")
                    content = "\n\n".join(pages_text).strip()
                    if not content:
                        return JsonResponse({
                            "error": "The uploaded PDF contains no extractable text. It may be a scanned image or protected."
                        }, status=400)
                except Exception as ex:
                    return JsonResponse({"error": f"Failed to extract text from PDF: {str(ex)}"}, status=400)
            elif ext in (".docx", ".doc"):
                try:
                    import io
                    import docx
                    doc = docx.Document(io.BytesIO(uploaded_file.read()))
                    extracted_parts = []
                    for p in doc.paragraphs:
                        text = p.text.strip()
                        if text:
                            extracted_parts.append(text)
                    for table in doc.tables:
                        for row in table.rows:
                            row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                            if row_cells:
                                dedup_cells = []
                                for c in row_cells:
                                    if not dedup_cells or c != dedup_cells[-1]:
                                        dedup_cells.append(c)
                                extracted_parts.append(" | ".join(dedup_cells))
                    content = "\n\n".join(extracted_parts).strip()
                    if not content:
                        return JsonResponse({
                            "error": "The uploaded Word document contains no extractable text."
                        }, status=400)
                except Exception as ex:
                    return JsonResponse({"error": f"Failed to extract text from Word document: {str(ex)}"}, status=400)
            elif ext in (".txt", ".md", ".csv", ".json", ".log", ".py", ".html"):
                try:
                    content = uploaded_file.read().decode("utf-8", errors="ignore").strip()
                except Exception as ex:
                    return JsonResponse({"error": f"Failed to read file: {str(ex)}"}, status=400)
            else:
                return JsonResponse({
                    "error": f"Unsupported file type '{ext}'. Please upload a PDF, DOCX, TXT, MD, or CSV file."
                }, status=400)

        if not title or not content:
            return JsonResponse({"error": "Title and document content (or an uploaded PDF/DOCX/text file) are required"}, status=400)

        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        res = kb.add_document(doc_id, title, content, category)
        return JsonResponse({
            "status": "ok",
            "document": res["document"],
            "chunks_created": res["chunks_created"],
            "total_chunks": len(kb.chunks),
            "total_docs": len(kb.documents)
        })

    elif action == "clear":
        kb.clear()
        return JsonResponse({
            "status": "ok",
            "message": "Knowledge base cleared",
            "documents": kb.get_documents_summary(),
            "total_chunks": 0,
            "total_docs": 0
        })

    elif action in ("reset", "reload", "reload_defaults"):
        kb.reset_defaults()
        return JsonResponse({
            "status": "ok",
            "message": "Knowledge base reloaded from documents folder",
            "documents": kb.get_documents_summary(),
            "total_chunks": len(kb.chunks),
            "total_docs": len(kb.documents)
        })

    elif action in ("delete_document", "remove_document"):
        doc_id = (data.get("doc_id") or request.GET.get("doc_id") or request.POST.get("doc_id") or "").strip()
        if not doc_id:
            return JsonResponse({"error": "Document ID required"}, status=400)
        success = kb.remove_document(doc_id)
        return JsonResponse({
            "status": "ok" if success else "not_found",
            "documents": kb.get_documents_summary(),
            "total_chunks": len(kb.chunks),
            "total_docs": len(kb.documents)
        })

    elif action == "documents":
        return JsonResponse({
            "documents": kb.get_documents_summary(),
            "total_chunks": len(kb.chunks),
            "total_docs": len(kb.documents)
        })

    else:
        q = request.GET.get("q", "").strip()
        if not q and request.method == "POST":
            q = (data.get("q") or request.POST.get("q") or "").strip()
        if not q:
            return JsonResponse({"error": "No query provided"}, status=400)
        top_k = int(request.GET.get("k", data.get("k", 4)))
        res = execute_rag_pipeline(q, top_k=top_k)
        return JsonResponse(res)


