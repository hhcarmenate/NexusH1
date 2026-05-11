#!/usr/bin/env python3
"""
Nexus H1 — AI Conversational Module
Integrates LLM (OpenAI/Claude) with tool use and memory.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Callable
from pathlib import Path

# Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = "gpt-4o"
DEFAULT_TEMPERATURE = 0.7
MAX_HISTORY = 50

# Conversation history storage
CONVERSATIONS_DIR = Path("memory/conversations")
CONVERSATIONS_DIR.mkdir(exist_ok=True)


class ConversationMemory:
    """Persistent conversation memory per session/user."""
    
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.file_path = CONVERSATIONS_DIR / f"{session_id}.json"
        self.messages: List[Dict] = []
        self._load()
    
    def _load(self):
        if self.file_path.exists():
            try:
                data = json.loads(self.file_path.read_text())
                self.messages = data.get("messages", [])
            except Exception:
                self.messages = []
    
    def save(self):
        self.file_path.write_text(json.dumps({
            "session_id": self.session_id,
            "updated_at": datetime.now().isoformat(),
            "messages": self.messages,
        }, indent=2))
    
    def add(self, role: str, content: str, **kwargs):
        """Add a message to history."""
        msg = {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        msg.update(kwargs)
        self.messages.append(msg)
        
        # Trim to max history
        if len(self.messages) > MAX_HISTORY:
            # Keep system message if present, then trim from the oldest
            system_msgs = [m for m in self.messages if m["role"] == "system"]
            other_msgs = [m for m in self.messages if m["role"] != "system"]
            other_msgs = other_msgs[-(MAX_HISTORY - len(system_msgs)):]
            self.messages = system_msgs + other_msgs
        
        self.save()
    
    def get_messages(self, for_api: bool = True) -> List[Dict]:
        """Get messages formatted for API."""
        if for_api:
            return [
                {"role": m["role"], "content": m["content"], **{k: v for k, v in m.items() if k in ["name", "tool_calls", "tool_call_id"]}}
                for m in self.messages
            ]
        return self.messages.copy()
    
    def clear(self):
        """Clear conversation history."""
        self.messages = []
        self.save()


class Tool:
    """Represents a callable tool for the AI."""
    
    def __init__(self, name: str, description: str, parameters: Dict, handler: Callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
    
    def to_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }


class NexusAI:
    """Main AI interface for Nexus H1."""
    
    def __init__(self, model: str = DEFAULT_MODEL, session_id: str = "default"):
        self.model = model
        self.memory = ConversationMemory(session_id)
        self.tools: Dict[str, Tool] = {}
        self.client = None
        
        if OPENAI_API_KEY:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=OPENAI_API_KEY)
            except ImportError:
                pass
        
        # Set system prompt
        self._set_system_prompt()
    
    def _set_system_prompt(self):
        """Set Nexus H1 system personality."""
        system_prompt = """You are Nexus H1, a personal assistant for Henry. 
You are helpful, direct, slightly witty (Jarvis-style), and efficient.

Your capabilities:
- Read and send emails (Gmail)
- Send WhatsApp and Telegram messages
- Manage calendar events and reminders
- Create and read Notion notes
- Speak text aloud (TTS)
- Answer questions and have natural conversations

Rules:
- Be concise unless asked for detail
- Use tools when needed, don't make up information
- Address the user as Henry
- Maintain context across the conversation
- If you don't know something, say so
- For time-sensitive tasks, use the calendar integration
"""
        # Only set if no system message exists
        if not any(m["role"] == "system" for m in self.memory.messages):
            self.memory.add("system", system_prompt)
    
    def register_tool(self, tool: Tool):
        """Register a tool for the AI to use."""
        self.tools[tool.name] = tool
    
    def _call_tool(self, name: str, arguments: Dict) -> str:
        """Execute a tool by name."""
        if name not in self.tools:
            return f"Error: Tool '{name}' not found."
        
        try:
            result = self.tools[name].handler(**arguments)
            if isinstance(result, (dict, list)):
                return json.dumps(result, default=str)
            return str(result)
        except Exception as e:
            return f"Error executing {name}: {str(e)}"
    
    def chat(self, message: str) -> str:
        """Send a message and get AI response."""
        if not self.client:
            return "❌ AI not configured. Set OPENAI_API_KEY in .env"
        
        # Add user message
        self.memory.add("user", message)
        
        # Prepare messages and tools
        messages = self.memory.get_messages(for_api=True)
        tools_schema = [t.to_schema() for t in self.tools.values()] if self.tools else None
        
        # Call API
        try:
            if tools_schema:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools_schema,
                    tool_choice="auto",
                    temperature=DEFAULT_TEMPERATURE,
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=DEFAULT_TEMPERATURE,
                )
            
            assistant_msg = response.choices[0].message
            
            # Check for tool calls
            if assistant_msg.tool_calls:
                # Add assistant message with tool calls
                self.memory.add(
                    "assistant",
                    assistant_msg.content or "",
                    tool_calls=[tc.model_dump() for tc in assistant_msg.tool_calls]
                )
                
                # Execute tools
                tool_results = []
                for tc in assistant_msg.tool_calls:
                    tool_name = tc.function.name
                    tool_args = json.loads(tc.function.arguments)
                    result = self._call_tool(tool_name, tool_args)
                    
                    self.memory.add(
                        "tool",
                        result,
                        tool_call_id=tc.id,
                        name=tool_name,
                    )
                    tool_results.append(result)
                
                # Get final response after tool execution
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.memory.get_messages(for_api=True),
                    temperature=DEFAULT_TEMPERATURE,
                )
                
                reply = final_response.choices[0].message.content
                self.memory.add("assistant", reply)
                return reply
            
            else:
                reply = assistant_msg.content
                self.memory.add("assistant", reply)
                return reply
                
        except Exception as e:
            error_msg = f"❌ AI Error: {str(e)}"
            return error_msg
    
    def clear_memory(self):
        """Clear conversation memory."""
        self.memory.clear()
        self._set_system_prompt()
    
    def get_history(self) -> List[Dict]:
        """Get conversation history."""
        return self.memory.get_messages(for_api=False)


# Default tool implementations for Nexus H1

def _create_default_tools(ai: NexusAI):
    """Register default tools for Nexus H1."""
    
    # Gmail tools
    ai.register_tool(Tool(
        name="get_emails",
        description="Get recent emails from Gmail. Returns list of emails with subject, from, date.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search query, e.g., 'is:unread' or 'from:boss@company.com'"},
                "max_results": {"type": "integer", "description": "Number of emails to return", "default": 5},
            },
        },
        handler=lambda query="is:unread", max_results=5: _safe_call("integrations.gmail", "list_messages", max_results=max_results, query=query),
    ))
    
    ai.register_tool(Tool(
        name="send_email",
        description="Send an email via Gmail.",
        parameters={
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body text"},
            },
            "required": ["to", "subject", "body"],
        },
        handler=lambda to, subject, body: _safe_call("integrations.gmail", "send_message", to=to, subject=subject, body=body),
    ))
    
    # Calendar tools
    ai.register_tool(Tool(
        name="get_calendar_events",
        description="Get upcoming calendar events.",
        parameters={
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look ahead", "default": 7},
            },
        },
        handler=lambda days=7: _safe_call("integrations.calendar", "get_upcoming_events", days=days),
    ))
    
    ai.register_tool(Tool(
        name="create_reminder",
        description="Create a quick calendar reminder.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Reminder text"},
                "minutes_from_now": {"type": "integer", "description": "Minutes until reminder", "default": 30},
            },
            "required": ["text"],
        },
        handler=lambda text, minutes_from_now=30: _safe_call("integrations.calendar", "create_quick_reminder", text=text, minutes_from_now=minutes_from_now),
    ))
    
    # WhatsApp tool
    ai.register_tool(Tool(
        name="send_whatsapp",
        description="Send a WhatsApp message. Phone should include country code (e.g., '1234567890').",
        parameters={
            "type": "object",
            "properties": {
                "phone": {"type": "string", "description": "Phone number with country code"},
                "message": {"type": "string", "description": "Message text"},
            },
            "required": ["phone", "message"],
        },
        handler=lambda phone, message: _safe_call("integrations.whatsapp", "send", to=phone, message=message),
    ))
    
    # Telegram tool
    ai.register_tool(Tool(
        name="send_telegram",
        description="Send a Telegram message to a chat.",
        parameters={
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "Chat ID or username"},
                "message": {"type": "string", "description": "Message text"},
            },
            "required": ["chat_id", "message"],
        },
        handler=lambda chat_id, message: _safe_call("integrations.telegram", "send_message", chat_id=chat_id, text=message),
    ))
    
    # Notion tool
    ai.register_tool(Tool(
        name="search_notion",
        description="Search Notion pages and databases.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
        },
        handler=lambda query="": _safe_call("integrations.notion", "search", query=query),
    ))
    
    # Voice tool
    ai.register_tool(Tool(
        name="speak_text",
        description="Speak text aloud using TTS.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to speak"},
            },
            "required": ["text"],
        },
        handler=lambda text: _safe_call("integrations.voice", "say", text=text),
    ))
    
    # System tools
    ai.register_tool(Tool(
        name="get_current_time",
        description="Get current date and time.",
        parameters={"type": "object", "properties": {}},
        handler=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)"),
    ))
    
    ai.register_tool(Tool(
        name="clear_conversation",
        description="Clear the current conversation history.",
        parameters={"type": "object", "properties": {}},
        handler=lambda: ai.clear_memory() or "Conversation history cleared.",
    ))


def _safe_call(module_name: str, function_name: str, **kwargs):
    """Safely call an integration function."""
    try:
        import importlib
        module = importlib.import_module(module_name)
        func = getattr(module, function_name)
        return func(**kwargs)
    except Exception as e:
        return {"error": str(e), "hint": f"Make sure {module_name} is configured and {function_name} is available."}


# Factory
def create_ai(session_id: str = "default") -> NexusAI:
    """Create Nexus AI with default tools."""
    ai = NexusAI(session_id=session_id)
    _create_default_tools(ai)
    return ai


if __name__ == "__main__":
    ai = create_ai()
    print("Nexus H1 AI Module")
    print("Registered tools:", list(ai.tools.keys()))
    print("\nTest with: ai.chat('Hello, what can you do?')")
