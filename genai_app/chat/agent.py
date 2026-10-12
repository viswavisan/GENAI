"""
Re-exporting from modular backends for backward compatibility.
"""
from .backends.limited_agent import run_limited_agent, LIMITED_TOOLS_METADATA as TOOL_METADATA
from .backends.universal_agent import run_system_command, propose_universal_action as propose_agent_action, execute_confirmed_command
