"""Rich UI components."""

from .status_bar import RichStatusBar
from .message_display import MessageDisplay
from .tool_display import ToolDisplay

# New rich components
try:
    from .input_handler import RichInputHandler
    from .approval_dialog import ApprovalDialog
    __all__ = ["RichStatusBar", "MessageDisplay", "ToolDisplay", "RichInputHandler", "ApprovalDialog"]
except ImportError:
    # Fall back to legacy components if new ones aren't available
    __all__ = ["RichStatusBar", "MessageDisplay", "ToolDisplay"]
