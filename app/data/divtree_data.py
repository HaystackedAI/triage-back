# Decision Tree Data - MINIMAL VERSION for LLM-focused testing
# Single node that loops on itself - allows free-form conversation

DECISION_TREE_DATA = {
    "nodes": {
        "start": {
            "id": "start",
            "topic": "Financial Strategy Assistant",
            "question": "Hello! How can I help you today?",
            "ui_display": "💬 **Financial Strategy Assistant** - Ask me anything!",
            "response_options": [
                "I have a question",
                "Continue conversation"
            ],
            "should_reason": False,
            "reasoning_rules": "",
            "additional_reasoning": "",
            "required": False,
            "dependencies": [],
            "children": [],  # No children - free-form chat
            "is_terminal": False,
            "outcome": None
        }
    }
}
