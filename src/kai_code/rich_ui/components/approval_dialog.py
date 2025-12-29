"""Rich approval dialog component.

Ported from letta-code with enhancements for kai-code security context.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List, Tuple
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.align import Align

from ..message_formatter import MessageFormatter

logger = logging.getLogger("kai_code.rich_ui")


class ApprovalDialog:
    """Rich approval dialog with context analysis and security information."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.formatter = MessageFormatter(console)
        
    def show_approval_dialog(
        self,
        tool_name: str,
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        width: int = 80
    ) -> Tuple[bool, str]:
        """Show approval dialog and return (approved, reason)."""
        
        print()
        
        # Header
        self.console.print(Panel(
            f"[bold yellow]⚠️[/bold yellow] [bold red]APPROVAL REQUIRED[/bold red]",
            border_style="red",
            padding=(0, 2)
        ))
        
        # Tool information
        tool_info = Table(title="Tool Call Information", box=None)
        tool_info.add_column("Property", style="cyan", width=20)
        tool_info.add_column("Value", style="white")
        
        tool_info.add_row("Tool Name", f"[bold]{tool_name}[/bold]")
        tool_info.add_row("Risk Level", self._get_tool_risk_level(tool_name))
        
        self.console.print(Panel(tool_info, border_style="yellow"))
        
        # Arguments
        if args:
            args_text = self.formatter.format_dict_table(args, width, "Tool Arguments")
            self.console.print(Panel(args_text, title="Arguments", border_style="yellow"))
        
        # Context analysis
        if context:
            context_panel = self._render_context_analysis(context, width)
            self.console.print(context_panel)
        
        # Security information
        security_panel = self._render_security_info(tool_name, args, width)
        self.console.print(security_panel)
        
        # Approval prompt
        self.console.print()
        self.console.print(Align.center(
            Text("[bold yellow]Do you want to approve this tool call?[/bold yellow]")
        ))
        
        # Show options
        self.console.print()
        self.console.print(Align.center(
            "[bold green]y[/bold green] / [bold red]n[/bold red]    [dim](or type a reason)[/dim]"
        ))
        self.console.print(Align.center(
            "[dim]Press Enter to approve, 'n' to deny, or type a reason to deny with explanation[/dim]"
        ))
        
        # Get user input
        while True:
            try:
                response = Prompt.ask(
                    "[bold]Your decision[/bold]",
                    console=self.console,
                    choices=["y", "n"],
                    default="n"
                ).strip().lower()
                
                if response in ["y", "yes", "approve", "allow"]:
                    return True, "User approved"
                elif response in ["n", "no", "deny", "reject"]:
                    return False, "User denied"
                elif response.strip():
                    return False, f"User denied: {response}"
                else:
                    # Empty response, treat as deny
                    return False, "User denied"
                    
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]Approval cancelled by user[/yellow]")
                return False, "User cancelled"
    
    def _get_tool_risk_level(self, tool_name: str) -> str:
        """Get risk level color for tool."""
        risk_tools = {
            "execute": "[bold red]HIGH[/bold red]",
            "bash": "[bold red]HIGH[/bold red]",
            "shell": "[bold red]HIGH[/bold red]",
            "run_shell_command": "[bold red]HIGH[/bold red]",
            "edit_file": "[bold yellow]MEDIUM[/bold yellow]",
            "apply_patch": "[bold yellow]MEDIUM[/bold yellow]",
            "write_file": "[bold yellow]MEDIUM[/bold yellow]",
            "delete_file": "[bold red]HIGH[/bold red]",
        }
        
        return risk_tools.get(tool_name, "[bold green]LOW[/bold green]")
    
    def _render_context_analysis(self, context: Dict[str, Any], width: int) -> Panel:
        """Render context analysis panel."""
        context_table = Table(title="Context Analysis", box=None)
        context_table.add_column("Aspect", style="cyan", width=15)
        context_table.add_column("Analysis", style="white")
        
        # Add context information
        if "security_analysis" in context:
            sec = context["security_analysis"]
            context_table.add_row(
                "Security",
                f"[green]{sec.get('classification', 'Unknown')}[/green]"
            )
            context_table.add_row(
                "Risk Score", 
                f"[yellow]{sec.get('risk_score', 'N/A')}[/yellow]"
            )
            
        if "tool_purpose" in context:
            purpose = context["tool_purpose"]
            context_table.add_row("Purpose", purpose)
            
        if "file_analysis" in context:
            files = context["file_analysis"]
            if isinstance(files, list):
                file_text = ", ".join(files[:3])
                if len(files) > 3:
                    file_text += f" and {len(files) - 3} others"
                context_table.add_row("Files Affected", file_text)
            else:
                context_table.add_row("Files Affected", str(files))
        
        return Panel(context_table, title="Context", border_style="blue")
    
    def _render_security_info(self, tool_name: str, args: Dict[str, Any], width: int) -> Panel:
        """Render security information panel."""
        security_table = Table(title="Security Information", box=None)
        security_table.add_column("Check", style="cyan", width=20)
        security_table.add_column("Status", style="white")
        
        # Command injection check
        cmd_injection_risk = "command injection"
        if tool_name in ["execute", "bash", "shell", "run_shell_command"]:
            command = args.get("command", "")
            if any(danger in command.lower() for danger in ["rm -rf", "sudo", "su", "chmod 777"]):
                security_table.add_row(cmd_injection_risk, "[red]⚠️ Risky[/red]")
                reason = f"Command contains potentially dangerous operations: {command[:50]}..."
            else:
                security_table.add_row(cmd_injection_risk, "[green]✓ Safe[/green]")
                reason = "Command appears safe"
        else:
            security_table.add_row(cmd_injection_risk, "[green]N/A[/green]")
            reason = "Not a command execution tool"
        
        # File access check
        file_ops = ["read_file", "write_file", "edit_file", "apply_patch"]
        if tool_name in file_ops:
            file_path = args.get("file_path", "")
            if any(danger in file_path for danger in ["/etc/", "/boot/", "/usr/bin/"]):
                security_table.add_row("File Access", "[red]⚠️ Sensitive[/red]")
            else:
                security_table.add_row("File Access", "[green]✓ Safe[/green]")
        else:
            security_table.add_row("File Access", "[green]N/A[/green]")
        
        # Add reason row
        security_table.add_row("Assessment", reason)
        
        return Panel(security_table, title="Security Assessment", border_style="yellow")
    
    def show_batch_approval_dialog(
        self,
        tool_calls: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        width: int = 80
    ) -> Tuple[List[bool], List[str]]:
        """Show batch approval dialog for multiple tool calls."""
        
        print()
        self.console.print(Panel(
            f"[bold yellow]⚠️[/bold yellow] [bold red]{len(tool_calls)} APPROVALS REQUIRED[/bold red]",
            border_style="red",
            padding=(0, 2)
        ))
        
        # Create summary table
        summary_table = Table(title="Batch Tool Calls", box=None)
        summary_table.add_column("Tool", style="cyan")
        summary_table.add_column("Risk", style="yellow")
        summary_table.add_column("Status", style="white")
        
        for i, tool_call in enumerate(tool_calls, 1):
            tool_name = tool_call.get("tool_name", "unknown")
            risk = self._get_tool_risk_level(tool_name)
            summary_table.add_row(f"{i}. {tool_name}", risk, "[dim]Pending[/dim]")
        
        self.console.print(Panel(summary_table, border_style="yellow"))
        
        # Options
        self.console.print()
        self.console.print("[bold]Approval Options:[/bold]")
        self.console.print("  [bold green]a[/bold green]pprove all  [bold red]d[/bold red]eny all  [bold yellow]r[/bold yellow]eview individually")
        
        # Get decision
        while True:
            try:
                choice = Prompt.ask(
                    "[bold]Your decision[/bold]",
                    console=self.console,
                    choices=["a", "d", "r"],
                    default="r"
                ).strip().lower()
                
                if choice == "a":
                    # Approve all
                    reasons = ["Approved in batch"] * len(tool_calls)
                    return [True] * len(tool_calls), reasons
                elif choice == "d":
                    # Deny all
                    reasons = ["Denied in batch"] * len(tool_calls)
                    return [False] * len(tool_calls), reasons
                elif choice == "r":
                    # Review individually
                    approvals = []
                    reasons = []
                    for tool_call in tool_calls:
                        self.console.print(f"\n[yellow]Reviewing: {tool_call.get('tool_name')}[/yellow]")
                        approved, reason = self.show_approval_dialog(
                            tool_call.get("tool_name"),
                            tool_call.get("args", {}),
                            context,
                            width
                        )
                        approvals.append(approved)
                        reasons.append(reason)
                    return approvals, reasons
                else:
                    self.console.print("[red]Invalid choice. Please try again.[/red]")
                    
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]Batch approval cancelled by user[/yellow]")
                return [False] * len(tool_calls), ["User cancelled"] * len(tool_calls)
