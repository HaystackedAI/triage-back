from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from dataclasses import dataclass, asdict, field

from app.observability import http_logging, server_logging

# --- Start of Inlined Decision Tree Logic ---

@dataclass
class ConversationState:
    """Tracks the state of a user's conversation through the decision tree"""
    session_id: str
    current_node_id: str
    user_responses: Dict[str, str] = field(default_factory=dict)
    reasoning_trail: List[str] = field(default_factory=list)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    chat_mode: bool = False
    completed: bool = False
    outcome: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    last_user_input: str = ""

@dataclass
class DecisionNode:
    """Represents a single node in the decision tree"""
    id: str
    topic: str
    question: str
    ui_display: str
    response_options: List[str]
    should_reason: bool
    reasoning_rules: str
    additional_reasoning: str
    required: bool = True
    dependencies: List[str] = None
    children: List[str] = None
    is_terminal: bool = False
    outcome: Optional[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.children is None:
            self.children = []


class DecisionTree:
    """Manages the decision tree logic and conversation states, self-contained within main.py."""
    
    def __init__(self, data_dict: dict = None):
        self.nodes: Dict[str, DecisionNode] = {}
        self.conversations: Dict[str, ConversationState] = {}
        if data_dict:
            self.load_from_dict(data_dict)

    def load_from_dict(self, data: dict):
        """Load decision tree data from dictionary"""
        try:
            for node_id, node_data in data['nodes'].items():
                self.nodes[node_id] = DecisionNode(**node_data)

            http_logging.logger.info(f"Loaded {len(self.nodes)} decision tree nodes")
        except Exception as e:
            http_logging.logger.error(f"Failed to load decision tree data: {e}")
            raise

    def start_session(self, session_id: str, chat_mode: bool = False) -> None:
        """Start a new decision tree session."""
        if session_id in self.conversations:
            return

        self.conversations[session_id] = ConversationState(
            session_id=session_id,
            current_node_id="start",
            chat_mode=chat_mode
        )
        http_logging.logger.info(f"Started new session {session_id} in chat_mode={chat_mode}")

    def set_current_node(self, session_id: str, node_id: str) -> bool:
        """Forcefully set the current node for a session."""
        if session_id in self.conversations and node_id in self.nodes:
            old_node = self.conversations[session_id].current_node_id
            self.conversations[session_id].current_node_id = node_id
            self.conversations[session_id].last_updated = datetime.now()
            http_logging.logger.info(f"Session {session_id} current node manually set to {node_id}")
            server_logging.info(f"NODE TRANSITION: {session_id} - {old_node} -> {node_id}", level="info", details={
                "session_id": session_id,
                "old_node": old_node,
                "new_node": node_id,
                "timestamp": datetime.now().isoformat()
            })
            return True
        http_logging.warning(f"Failed to set node for session {session_id} to {node_id}. Session or node not found.")
        server_logging.warning(f"NODE TRANSITION FAILED: {session_id} - target: {node_id}", level="warning", details={
            "session_id": session_id,
            "target_node": node_id,
            "session_exists": session_id in self.conversations,
            "node_exists": node_id in self.nodes
        })
        return False

