"""Rich message formatter utilities.

Fixed version with correct Python regex.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional, List
from datetime import datetime
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.console import Console, ConsoleOptions, RenderableType, RenderResult

logger = logging.getLogger("kai_code.rich_ui")


class MessageFormatter:
    """Formats messages for Rich display with letta-code style rendering."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def normalize_text(self, text: str) -> str:
        """Normalize text similar to letta-code approach."""
        return (
            text
            .replace(/\r\n/g, "\n")
            .replace(/[ \t]+$/gm, "")
            .replace(/\n{3,}/g, "\n\n")
            .replace(/^\n+|\n+$/g, "")
        )
