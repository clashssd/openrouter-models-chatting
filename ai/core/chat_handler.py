# ai/core/chat_handler.py
# imports
import time
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import logging
from utils import CodeHighlighter, TokenCounter

# base logger
logger = logging.getLogger("my_app")

# Global variables (will be set by main.py)
fallback_manager = None
stream_handler = None


# class chatsession
class ChatSession:
    """Single chat session with a model"""

    def __init__(
        self, model_id: str, profile: str = None, config: Dict[str, Any] = None
    ):
        self.model_id = model_id
        self.profile = profile
        self.config = config or {}
        self.messages: List[Dict[str, str]] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.fallback_manager = fallback_manager
        self.total_tokens = 0
        self.message_count = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.highlighter = CodeHighlighter()
        self.token_counter = TokenCounter()
        self.command_history: List[str] = []
        self.history_index = -1

    def chat_with_fallback(
        self, model_id: str, messages: list, config: Dict[str, Any] = None
    ) -> Optional[str]:
        """Chat with automatic fallback"""
        if self.fallback_manager:
            return self.fallback_manager.chat_with_fallback(
                primary_model=model_id, messages=messages, config=config
            )
        else:
            # Fallback to direct chat
            if config:
                return self.api_checker.chat_with_config(
                    model_id, messages[-1]["content"], config
                )
            else:
                return self.api_checker.chat_completion_with_history(model_id, messages)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the session"""
        self.messages.append({"role": role, "content": content})
        self.message_count += 1
        self.updated_at = datetime.now().isoformat()

    def get_messages(self) -> List[Dict[str, str]]:
        """Get all messages in the session"""
        return self.messages

    def get_last_message(self) -> Optional[Dict[str, str]]:
        """Get the last message in the session"""
        return self.messages[-1] if self.messages else None

    def clear(self) -> None:
        """Clear all messages"""
        self.messages = []
        self.message_count = 0
        self.updated_at = datetime.now().isoformat()

    def add_command_to_history(self, command: str) -> None:
        """Add command to history"""
        self.command_history.append(command)
        self.history_index = len(self.command_history)

    def get_previous_command(self) -> Optional[str]:
        """Get previous command from history"""
        if not self.command_history or self.history_index <= 0:
            return None
        self.history_index -= 1
        return self.command_history[self.history_index]

    def get_next_command(self) -> Optional[str]:
        """Get next command from history"""
        if (
            not self.command_history
            or self.history_index >= len(self.command_history) - 1
        ):
            return None
        self.history_index += 1
        return self.command_history[self.history_index]

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        duration = 0
        if self.created_at and self.updated_at:
            created = datetime.fromisoformat(self.created_at)
            updated = datetime.fromisoformat(self.updated_at)
            duration = (updated - created).total_seconds()

        total_tokens = self.input_tokens + self.output_tokens
        cost = self.token_counter.estimate_cost(
            self.input_tokens, self.output_tokens, self.model_id
        )

        return {
            "model": self.model_id,
            "profile": self.profile or "default",
            "messages": self.message_count,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": total_tokens,
            "duration_seconds": duration,
            "estimated_cost": cost.get("total_cost", 0),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization"""
        return {
            "model_id": self.model_id,
            "profile": self.profile,
            "config": self.config,
            "messages": self.messages,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_tokens": self.total_tokens,
            "message_count": self.message_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatSession":
        """Create session from dictionary"""
        session = cls(
            model_id=data.get("model_id", "unknown"),
            profile=data.get("profile"),
            config=data.get("config", {}),
        )
        session.messages = data.get("messages", [])
        session.created_at = data.get("created_at", datetime.now().isoformat())
        session.updated_at = data.get("updated_at", session.created_at)
        session.total_tokens = data.get("total_tokens", 0)
        session.message_count = data.get("message_count", len(session.messages))
        return session


class ChatManager:
    """Manager for chat sessions"""

    def __init__(self, sessions_dir: str = "chat_sessions", fallback_manager_param=None, stream_handler_param=None):
    # allow passing fallback_manager and stream_handler from callers (e.g. main.py)
    # and update module-level globals for backward compatibility with existing code
        global fallback_manager, stream_handler
        if fallback_manager_param is not None:
            fallback_manager = fallback_manager_param
        if stream_handler_param is not None:
            stream_handler = stream_handler_param

    self.sessions_dir = Path(sessions_dir)
    self.sessions_dir.mkdir(parents=True, exist_ok=True)
    self.current_session: Optional[ChatSession] = None
    self.sessions: Dict[str, ChatSession] = {}
    # use the module globals (may have been updated above)
    self.fallback_manager = fallback_manager
    self.stream_handler = stream_handler
    self._load_all_sessions()

    def create_streaming_session(
        self, model_id: str, profile: str = None, config: Dict[str, Any] = None
    ) -> str:
        """Create a new streaming chat session"""
        session_id = f"chat_{int(time.time())}"
        self.current_session = ChatSession(model_id, profile, config)
        self.sessions[session_id] = self.current_session
        # Create streaming session
        if self.stream_handler:
            streaming_session = self.stream_handler.StreamingChatSession(self.stream_handler, model_id)
            self.current_session.streaming_session = streaming_session
            self.current_session.streaming_enabled = True
        self._save_session(session_id)
        return session_id

    def create_session(
        self, model_id: str, profile: str = None, config: Dict[str, Any] = None
    ) -> str:
        """Create a new chat session"""
        session_id = f"chat_{int(time.time())}"
        self.current_session = ChatSession(model_id, profile, config)
        self.sessions[session_id] = self.current_session
        self._save_session(session_id)
        logger.info(f"Created session {session_id} with model {model_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID"""
        return self.sessions.get(session_id)

    def get_current_session(self) -> Optional[ChatSession]:
        """Get the current active session"""
        return self.current_session

    def set_current_session(self, session_id: str) -> bool:
        """Set a session as the current active session"""
        if session_id in self.sessions:
            self.current_session = self.sessions[session_id]
            return True
        return False

    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """Add a message to a session"""
        session = self.get_session(session_id)
        if session:
            session.add_message(role, content)
            self._save_session(session_id)
            return True
        return False

    def clear_session(self, session_id: str) -> bool:
        """Clear all messages from a session"""
        session = self.get_session(session_id)
        if session:
            session.clear()
            self._save_session(session_id)
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            session_path = self.sessions_dir / f"{session_id}.json"
            if session_path.exists():
                session_path.unlink()
            if self.current_session and self.current_session == self.sessions.get(
                session_id
            ):
                self.current_session = None
            return True
        return False

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions with metadata"""
        sessions_list = []
        for session_id, session in self.sessions.items():
            sessions_list.append(
                {
                    "id": session_id,
                    "model_id": session.model_id,
                    "profile": session.profile,
                    "message_count": session.message_count,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                }
            )
        return sorted(sessions_list, key=lambda x: x["updated_at"], reverse=True)

    def save_session(self, session_id: str) -> bool:
        """Save a session to file"""
        return self._save_session(session_id)

    def _save_session(self, session_id: str) -> bool:
        """Internal method to save a session"""
        session = self.get_session(session_id)
        if not session:
            return False
        session_path = self.sessions_dir / f"{session_id}.json"
        try:
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"session_id": session_id, **session.to_dict()},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            return True
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
            return False

    def _load_all_sessions(self) -> None:
        """Load all sessions from files"""
        for session_path in self.sessions_dir.glob("*.json"):
            try:
                with open(session_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    session_id = data.get("session_id", session_path.stem)
                    self.sessions[session_id] = ChatSession.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load session {session_path}: {e}")

    def export_session(
        self, session_id: str, format: str = "markdown"
    ) -> Optional[str]:
        """Export a session in various formats"""
        session = self.get_session(session_id)
        if not session:
            return None
        if format == "markdown":
            return self._export_markdown(session)
        elif format == "json":
            return self._export_json(session)
        elif format == "text":
            return self._export_text(session)
        else:
            return None

    def _export_markdown(self, session: ChatSession) -> str:
        """Export session as markdown"""
        lines = []
        lines.append("# Chat Session")
        lines.append(f"**Model:** {session.model_id}")
        lines.append(f"**Profile:** {session.profile or 'Default'}")
        lines.append(f"**Created:** {session.created_at}")
        lines.append(f"**Messages:** {session.message_count}")
        lines.append("\n---\n")
        for msg in session.messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                lines.append(f"**🧑 User:**\n\n{content}\n")
            elif role == "assistant":
                lines.append(f"**🤖 Assistant:**\n\n{content}\n")
            elif role == "system":
                lines.append(f"**⚙️ System:**\n\n{content}\n")
            lines.append("---\n")
        return "\n".join(lines)

    def _export_json(self, session: ChatSession) -> str:
        """Export session as JSON"""
        return json.dumps(session.to_dict(), indent=2, ensure_ascii=False)

    def _export_text(self, session: ChatSession) -> str:
        """Export session as plain text"""
        lines = []
        lines.append(f"Chat Session - {session.model_id}")
        lines.append("=" * 50)
        for msg in session.messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            lines.append(f"\n[{role}]\n{content}\n")
            lines.append("-" * 30)
        return "\n".join(lines)
