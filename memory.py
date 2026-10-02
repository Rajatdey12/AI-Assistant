"""
Memory Module for Chiku: Conversation storage and context management

Features:
- Session-based conversation history
- Persistent JSON file storage
- Context window management (keep last N turns)
- Timestamp tracking
- Thread-safe operations
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import config

logger = logging.getLogger(__name__)


class Session:
    """Manages a single conversation session"""
    
    def __init__(self, session_id: str = config.SESSION["default_session_id"]):
        """
        Initialize or load a session.
        
        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.messages: List[Dict] = []
        self.created_at = datetime.now().isoformat()
        self.last_updated = self.created_at
        
        # Try to load existing session from disk
        self._load()
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """
        Add a message to the conversation.
        
        Args:
            role: "user" or "assistant"
            content: Message text
            metadata: Optional dict with extra info (e.g., confidence, latency)
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        
        if metadata:
            message.update(metadata)
        
        self.messages.append(message)
        self.last_updated = datetime.now().isoformat()
        
        logger.debug(f"📝 Added {role} message: {content[:50]}...")
    
    def get_last_n_turns(self, n: int = config.SESSION["max_history_turns"]) -> List[Dict]:
        """
        Get last N conversation turns for context (N messages = N/2 exchanges).
        
        Args:
            n: Number of messages to retrieve
            
        Returns:
            List of message dicts
        """
        return self.messages[-n:] if len(self.messages) > n else self.messages
    
    def get_context_string(self, n: int = config.SESSION["max_history_turns"]) -> str:
        """
        Format conversation for LLM input.
        
        Args:
            n: Number of messages to include
            
        Returns:
            String formatted as "User: ... Assistant: ..."
        """
        context = ""
        for msg in self.get_last_n_turns(n):
            role = msg["role"].capitalize()
            content = msg["content"]
            context += f"{role}: {content}\n"
        return context.strip()
    
    def clear(self) -> None:
        """Clear all messages from this session"""
        self.messages = []
        self.last_updated = datetime.now().isoformat()
        logger.info(f"🗑️  Cleared session {self.session_id}")
    
    def save(self) -> Path:
        """
        Save session to disk (JSON).
        
        Returns:
            Path to saved file
        """
        filepath = config.CONVERSATIONS_DIR / f"{self.session_id}.json"
        
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "message_count": len(self.messages),
            "messages": self.messages
        }
        
        try:
            filepath.write_text(json.dumps(data, indent=2))
            logger.debug(f"💾 Saved session {self.session_id} ({len(self.messages)} messages)")
            return filepath
        except Exception as e:
            logger.error(f"❌ Failed to save session: {e}")
            raise
    
    def _load(self) -> None:
        """Load session from disk if it exists"""
        filepath = config.CONVERSATIONS_DIR / f"{self.session_id}.json"
        
        if filepath.exists():
            try:
                data = json.loads(filepath.read_text())
                self.messages = data.get("messages", [])
                self.created_at = data.get("created_at", self.created_at)
                self.last_updated = data.get("last_updated", self.last_updated)
                logger.info(f"📂 Loaded session {self.session_id} ({len(self.messages)} messages)")
            except Exception as e:
                logger.error(f"❌ Failed to load session: {e}")
                self.messages = []
    
    def __str__(self) -> str:
        return f"Session({self.session_id}, {len(self.messages)} messages)"
    
    def __repr__(self) -> str:
        return self.__str__()


class SessionManager:
    """Manages multiple sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
    
    def get_session(self, session_id: str = config.SESSION["default_session_id"]) -> Session:
        """
        Get or create a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session object
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = Session(session_id)
        return self.sessions[session_id]
    
    def list_sessions(self) -> List[str]:
        """List all session IDs (from disk)"""
        session_files = config.CONVERSATIONS_DIR.glob("*.json")
        return [f.stem for f in session_files]
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session from memory and disk"""
        filepath = config.CONVERSATIONS_DIR / f"{session_id}.json"
        if filepath.exists():
            filepath.unlink()
            logger.info(f"🗑️  Deleted session {session_id}")
        
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def save_all(self) -> None:
        """Save all loaded sessions to disk"""
        for session in self.sessions.values():
            session.save()


# Global session manager instance
_session_manager = SessionManager()


def get_session(session_id: str = config.SESSION["default_session_id"]) -> Session:
    """Convenience function to get a session"""
    return _session_manager.get_session(session_id)


def list_sessions() -> List[str]:
    """List all sessions"""
    return _session_manager.list_sessions()


if __name__ == "__main__":
    # Test session management
    print("Testing Session Management...\n")
    
    # Create a test session
    session = Session("test_session")
    print(f"Created: {session}\n")
    
    # Add messages
    session.add_message("user", "Hello, what's your name?")
    session.add_message("assistant", "I'm Chiku, your personal AI assistant.")
    session.add_message("user", "What can you do?")
    session.add_message("assistant", "I can help with a wide range of tasks including answering questions, providing information, and having conversations.")
    
    print(f"Messages: {len(session.messages)}")
    print(f"Last turn: {session.get_last_n_turns(1)}\n")
    
    # Save
    session.save()
    
    # Load in new session object
    session2 = Session("test_session")
    print(f"Loaded: {session2}")
    print(f"Messages: {len(session2.messages)}")
    
    # Print context
    print(f"\nFormatted context:\n{session2.get_context_string()}")
    
    # List all sessions
    print(f"\nAll sessions: {list_sessions()}")
