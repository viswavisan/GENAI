"""
Modular GenAI & Agentic AI Backends:
1. genai_chat: Conversational LLM chat (Online Gemini & Offline Ollama).
2. agentic_online: Cloud-based agentic workflows (Limited Tools & Universal Terminal with Password).
3. agentic_offline: 100% Offline local agentic workflows with Ollama tool calling.
"""

# Group 1: GenAI Chat
from .genai_chat import generate_online_chat, generate_offline_chat

# Group 2: Agentic AI Online
from .agentic_online import (
    run_online_limited_agent,
    ONLINE_LIMITED_TOOLS_METADATA,
    propose_universal_action,
    execute_confirmed_command
)

# Group 3: Agentic AI Offline
from .agentic_offline import (
    run_offline_agent,
    OFFLINE_TOOLS_METADATA
)
