class AIAnalysisError(Exception):
    """Raised when AI (Azure OpenAI) analysis fails."""

class NotificationDispatchError(Exception):
    """Raised when delivery to a channel fails."""
