from app.data.decisiontree_type import DecisionTree

# initialized during startup
decision_tree: DecisionTree | None = None

# session cache
session_agents = {}

# tool cache
cached_tools = []
tools_last_updated = None

# token usage
session_token_usage = {}