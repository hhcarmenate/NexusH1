#!/usr/bin/env python3
"""
Nexus H1 — Google Gemini Integration Module (v2)
Uses google-genai (the new official SDK)
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Callable
from pathlib import Path

from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# New Google GenAI SDK
from google import genai
from google.genai import types

# Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_MODEL = "gemini-2.5-flash"
MAX_HISTORY = 50

CONVERSATIONS_DIR = Path("memory/conversations")
CONVERSATIONS_DIR.mkdir(exist_ok=True)


class GeminiMemory:
    """Persistent conversation memory."""
    
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.file_path = CONVERSATIONS_DIR / f"gemini_{session_id}.json"
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
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        msg.update(kwargs)
        self.messages.append(msg)
        
        if len(self.messages) > MAX_HISTORY:
            system_msgs = [m for m in self.messages if m.get("role") == "system"]
            other_msgs = [m for m in self.messages if m.get("role") != "system"]
            other_msgs = other_msgs[-(MAX_HISTORY - len(system_msgs)):]
            self.messages = system_msgs + other_msgs
        
        self.save()
    
    def get_messages(self) -> List[Dict]:
        return self.messages.copy()
    
    def clear(self):
        self.messages = []
        self.save()


class GeminiTool:
    """Callable tool for Gemini."""
    
    def __init__(self, name: str, description: str, parameters: Dict, handler: Callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
    
    def to_declaration(self) -> types.FunctionDeclaration:
        """Convert to Gemini FunctionDeclaration."""
        # Clean parameters: remove 'default' fields from properties
        clean_params = self._clean_schema(self.parameters)
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=clean_params,
        )
    
    def _clean_schema(self, schema: Dict) -> Dict:
        """Remove unsupported fields like 'default' from schema."""
        if not isinstance(schema, dict):
            return schema
        
        cleaned = {}
        for key, value in schema.items():
            if key == "default":
                continue  # Skip default values
            elif key == "properties" and isinstance(value, dict):
                cleaned[key] = {k: self._clean_schema(v) for k, v in value.items()}
            elif key in ["items", "additionalProperties"] and isinstance(value, dict):
                cleaned[key] = self._clean_schema(value)
            elif isinstance(value, list):
                cleaned[key] = [self._clean_schema(item) if isinstance(item, dict) else item for item in value]
            else:
                cleaned[key] = value
        return cleaned


class NexusGemini:
    """Main Gemini AI interface for Nexus H1."""
    
    def __init__(self, model: str = DEFAULT_MODEL, session_id: str = "default"):
        self.model_name = model
        self.memory = GeminiMemory(session_id)
        self.tools: Dict[str, GeminiTool] = {}
        self.client = None
        
        self._init_client()
        self._set_system_prompt()
    
    def _init_client(self):
        if not GEMINI_API_KEY:
            return
        try:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            print(f"Failed to init Gemini client: {e}")
    
    def _set_system_prompt(self):
        system_prompt = """You are Nexus H1, a personal assistant for Henry. 
You are helpful, direct, slightly witty (Jarvis-style), and efficient.

Your capabilities:
- Read and send emails (Gmail) — use get_emails/send_email tools
- Archive emails — use archive_emails with natural descriptions like 'promotions', 'social media notifications', 'newsletters', 'old emails'
- Send WhatsApp and Telegram messages — use send_whatsapp/send_telegram tools
- Manage calendar events and reminders — use get_calendar_events/create_reminder tools
- Create and read Notion notes/pages — use search_notion/create_notion_page tools
- Query Notion databases — use query_notion_database tool
- Check server status (Pi5/Nextcloud) — use get_server_status tool
- Speak text aloud (TTS) — use speak_text tool
- Answer questions and have natural conversations

IMPORTANT: When Henry asks about the server, pi, raspberry, nextcloud, or private cloud in ANY way, ALWAYS use the get_server_status tool. Do NOT say you cannot check it.

When the get_server_status tool returns data, present it EXACTLY as provided. Do NOT rewrite or reformat it. The tool already returns a beautifully formatted message with emojis and metrics.

Rules:
- Be concise unless asked for detail
- ALWAYS use tools when the user asks about emails, calendar, Notion, WhatsApp, or Telegram
- NEVER say you cannot do something if you have a tool for it — USE THE TOOL
- Address the user as Henry
- If you don't know something, say so
- For time-sensitive tasks, use the calendar integration
"""
        if not any(m.get("role") == "system" for m in self.memory.messages):
            self.memory.add("system", system_prompt)
    
    def register_tool(self, tool: GeminiTool):
        self.tools[tool.name] = tool
    
    def _call_tool(self, name: str, arguments: Dict) -> str:
        if name not in self.tools:
            return f"Error: Tool '{name}' not found."
        try:
            result = self.tools[name].handler(**arguments)
            if isinstance(result, (dict, list)):
                return json.dumps(result, default=str)
            return str(result)
        except Exception as e:
            return f"Error executing {name}: {str(e)}"
    
    def _build_system_instruction(self) -> str:
        system_msgs = [m["content"] for m in self.memory.messages if m.get("role") == "system"]
        return "\n\n".join(system_msgs)
    
    def _build_contents(self) -> List[types.Content]:
        """Convert memory to Gemini Content objects."""
        contents = []
        for m in self.memory.messages:
            if m.get("role") == "system":
                continue
            role = "user" if m["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=m.get("content", ""))]
            ))
        return contents
    
    def chat(self, message: str) -> str:
        if not self.client:
            return "❌ Gemini not configured. Set GEMINI_API_KEY in .env"
        
        self.memory.add("user", message)
        
        system_instruction = self._build_system_instruction()
        contents = self._build_contents()
        
        # Prepare tools
        tools = None
        if self.tools:
            declarations = [t.to_declaration() for t in self.tools.values()]
            tools = [types.Tool(function_declarations=declarations)]
        
        try:
            # Generate response
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                top_p=0.95,
                max_output_tokens=2048,
                tools=tools,
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )
            
            # Handle function calls (up to 5 iterations)
            max_iterations = 5
            last_raw_result = None
            last_tool_name = None
            
            for _ in range(max_iterations):
                if not response.candidates or not response.candidates[0].content.parts:
                    break
                
                part = response.candidates[0].content.parts[0]
                
                if not part.function_call:
                    break
                
                fc = part.function_call
                tool_name = fc.name
                tool_args = dict(fc.args) if fc.args else {}
                
                print(f"[Gemini] Calling tool: {tool_name}({tool_args})")
                
                # Execute tool
                result = self._call_tool(tool_name, tool_args)
                last_tool_name = tool_name
                
                # For server status, capture raw result for direct output
                if tool_name == "get_server_status":
                    last_raw_result = result
                
                # Send result back to model
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(
                        function_response=types.FunctionResponse(
                            name=tool_name,
                            response={"result": result},
                        )
                    )]
                ))
                
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )
            
            # If we called get_server_status, return raw formatted output directly
            if last_tool_name == "get_server_status" and last_raw_result:
                reply = last_raw_result
            else:
                reply = response.text
                if not reply:
                    reply = "I processed your request but couldn't generate a response. Please try again."
            
            self.memory.add("assistant", reply)
            return reply
            
        except Exception as e:
            return f"❌ Gemini Error: {str(e)}"
    
    def clear_memory(self):
        self.memory.clear()
        self._set_system_prompt()
    
    def get_history(self) -> List[Dict]:
        return self.memory.get_messages()


# Default tools
def _create_default_tools(ai: NexusGemini):
    ai.register_tool(GeminiTool(
        name="get_emails",
        description="Get recent emails from Gmail. Returns list of emails with subject, from, date.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search query, e.g., 'is:unread' or 'from:boss@company.com'"},
                "max_results": {"type": "integer", "description": "Number of emails to return"},
            },
        },
        handler=lambda query="is:unread", max_results=5: _safe_call("integrations.gmail", "list_messages", max_results=max_results, query=query),
    ))
    
    ai.register_tool(GeminiTool(
        name="archive_emails",
        description="Archive emails from Gmail. Provide a natural language description of which emails to archive (e.g., 'promotions', 'social media notifications', 'newsletters', 'emails older than 30 days'). The system will translate this into the appropriate Gmail search and archive matching emails.",
        parameters={
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Natural language description of emails to archive, e.g., 'promotions', 'social media notifications', 'newsletters from LinkedIn'"},
            },
            "required": ["description"],
        },
        handler=lambda description: _archive_emails_natural(description),
    ))
    
    ai.register_tool(GeminiTool(
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
    
    ai.register_tool(GeminiTool(
        name="get_calendar_events",
        description="Get upcoming calendar events.",
        parameters={
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look ahead"},
            },
        },
        handler=lambda days=7: _safe_call("integrations.google_calendar", "get_upcoming_events", days=days),
    ))
    
    ai.register_tool(GeminiTool(
        name="create_reminder",
        description="Create a quick calendar reminder.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Reminder text"},
                "minutes_from_now": {"type": "integer", "description": "Minutes until reminder"},
            },
            "required": ["text"],
        },
        handler=lambda text, minutes_from_now=30: _safe_call("integrations.google_calendar", "create_quick_reminder", text=text, minutes_from_now=minutes_from_now),
    ))
    
    ai.register_tool(GeminiTool(
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
    
    ai.register_tool(GeminiTool(
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
    
    ai.register_tool(GeminiTool(
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
    
    ai.register_tool(GeminiTool(
        name="create_notion_page",
        description="Create a new page/note in Notion. Requires a parent database_id or page_id.",
        parameters={
            "type": "object",
            "properties": {
                "parent_id": {"type": "string", "description": "Database ID or Page ID where to create the note"},
                "title": {"type": "string", "description": "Title of the note"},
                "content": {"type": "string", "description": "Body/content of the note"},
            },
            "required": ["parent_id", "title", "content"],
        },
        handler=lambda parent_id, title, content: _safe_call(
            "integrations.notion", "create_page",
            parent_id=parent_id,
            properties={"Name": {"title": [{"text": {"content": title}}]}},
            content_blocks=[{"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]}}]
        ),
    ))
    
    ai.register_tool(GeminiTool(
        name="query_notion_database",
        description="Query a Notion database to get entries.",
        parameters={
            "type": "object",
            "properties": {
                "database_id": {"type": "string", "description": "The Notion database ID"},
                "filter_status": {"type": "string", "description": "Optional: filter by status name"},
            },
        },
        handler=lambda database_id, filter_status=None: _safe_call(
            "integrations.notion", "query_database",
            database_id=database_id,
            filter_criteria={"property": "Status", "select": {"equals": filter_status}} if filter_status else None,
            page_size=50,
        ),
    ))
    
    ai.register_tool(GeminiTool(
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
    
    ai.register_tool(GeminiTool(
        name="get_current_time",
        description="Get current date and time.",
        parameters={"type": "object", "properties": {}},
        handler=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)"),
    ))
    
    ai.register_tool(GeminiTool(
        name="get_server_status",
        description="Check the status of the private cloud server (Pi5/Nextcloud). Returns a formatted status message with CPU, memory, disk, temperature, uptime, and Docker containers. Present this result directly to the user without rewriting.",
        parameters={"type": "object", "properties": {}},
        handler=lambda: _safe_call("integrations.pi_monitor", "get_quick_status"),
    ))
    
    ai.register_tool(GeminiTool(
        name="clear_conversation",
        description="Clear the current conversation history.",
        parameters={"type": "object", "properties": {}},
        handler=lambda: ai.clear_memory() or "Conversation history cleared.",
    ))


def _translate_to_gmail_query(description: str) -> str:
    """Translate natural language description into Gmail search query."""
    desc_lower = description.lower()
    
    # Promotions / spam-like
    if any(word in desc_lower for word in ["promoci", "promocion", "promotion", "spam", "ads", "publicidad", "oferta", "sale", "discount"]):
        return "category:promotions"
    
    # Social media
    if any(word in desc_lower for word in ["social", "redes", "facebook", "instagram", "twitter", "linkedin", "tiktok", "youtube", "notificacion social"]):
        return "category:social"
    
    # Newsletters / updates
    if any(word in desc_lower for word in ["newsletter", "boletin", "update", "actualizacion", "novedad", "digest", "weekly", "daily"]):
        return "category:updates"
    
    # Forums
    if any(word in desc_lower for word in ["forum", "foro", "community", "comunidad", "group", "grupo"]):
        return "category:forums"
    
    # Old emails
    if any(word in desc_lower for word in ["old", "viejo", "antiguo", "older than", "mas viejo", "30 days", "7 days"]):
        if "30" in desc_lower:
            return "older_than:30d"
        elif "7" in desc_lower or "week" in desc_lower:
            return "older_than:7d"
        else:
            return "older_than:30d"
    
    # Read emails
    if any(word in desc_lower for word in ["read", "leido", "visto", "already read"]):
        return "is:read"
    
    # Specific sender patterns
    if any(word in desc_lower for word in ["noreply", "no-reply", "notification", "notificacion", "alert", "alerta"]):
        return "from:noreply OR from:no-reply OR from:notification OR from:notificaciones"
    
    # Fallback: try to use description as-is (might be a Gmail query already)
    return description


def _archive_emails_natural(description: str, max_results: int = 50) -> str:
    """Archive emails based on natural language description."""
    try:
        import importlib
        module = importlib.import_module("integrations.gmail")
        list_func = getattr(module, "list_messages")
        archive_func = getattr(module, "archive")
        
        query = _translate_to_gmail_query(description)
        print(f"[Gmail] Translating '{description}' -> query: '{query}'")
        
        emails = list_func(max_results=max_results, query=query)
        if not emails:
            return f"📭 No encontré correos de tipo '{description}' para archivar."
        
        archived_count = 0
        errors = []
        for email in emails:
            try:
                archive_func(email["id"])
                archived_count += 1
            except Exception as e:
                errors.append(f"{email.get('subject', 'Unknown')}: {e}")
        
        result = f"✅ Archivados {archived_count}/{len(emails)} correos de '{description}'"
        if errors:
            result += f"\n⚠️ Errores: {len(errors)}"
        return result
    except Exception as e:
        return f"❌ Error archivando correos: {str(e)}"


def _safe_call(module_name: str, function_name: str, **kwargs):
    try:
        import importlib
        module = importlib.import_module(module_name)
        func = getattr(module, function_name)
        return func(**kwargs)
    except Exception as e:
        return {"error": str(e), "hint": f"Make sure {module_name} is configured."}


def create_gemini(session_id: str = "default") -> NexusGemini:
    ai = NexusGemini(session_id=session_id)
    _create_default_tools(ai)
    return ai


if __name__ == "__main__":
    ai = create_gemini()
    print("Nexus H1 Gemini Module (v2)")
    print("Registered tools:", list(ai.tools.keys()))
    print("\nTest with: ai.chat('Hello, what can you do?')")
