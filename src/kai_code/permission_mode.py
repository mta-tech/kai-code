from __future__ import annotations

from dataclasses import dataclass

from .permissions import PermissionConfig


PermissionMode = str

VALID_PERMISSION_MODES: tuple[PermissionMode, ...] = (
    "default",
    "acceptEdits",
    "plan",
    "bypassPermissions",
)


@dataclass(frozen=True)
class PermissionModeResolution:
    mode: PermissionMode
    yolo: bool
    interrupt_on: dict[str, bool] | None
    permissions: PermissionConfig | None


def resolve_permission_mode(
    *,
    mode: PermissionMode,
    base_permissions: PermissionConfig | None,
) -> PermissionModeResolution:
    """Map a permission mode onto (HITL interrupts + PermissionConfig).

    This is an intentionally minimal mapping designed to match letta-code's
    headless semantics:

    - default: approvals for execute + write/edit/apply_patch
    - acceptEdits: approvals only for execute
    - plan: read-only (deny write/edit/apply_patch/execute)
    - bypassPermissions: YOLO (no approvals)
    """
    if mode not in VALID_PERMISSION_MODES:
        raise ValueError(f"Invalid permission mode: {mode}")

    if mode == "bypassPermissions":
        return PermissionModeResolution(mode=mode, yolo=True, interrupt_on=None, permissions=None)

    if mode == "plan":
        # Read-only tools only.
        perms = PermissionConfig(
            allowed_tools=["ls", "read_file", "glob", "grep"],
            disallowed_tools=["write_file", "edit_file", "execute", "apply_patch"],
            allowed_commands=None,
            disallowed_commands=["*"],
        )
        return PermissionModeResolution(mode=mode, yolo=True, interrupt_on=None, permissions=perms)

    if mode == "acceptEdits":
        # Approve execution only, allow edits/patches without interrupts.
        return PermissionModeResolution(
            mode=mode,
            yolo=False,
            interrupt_on={"execute": True},
            permissions=base_permissions,
        )

    # default
    return PermissionModeResolution(
        mode=mode,
        yolo=False,
        interrupt_on={
            "execute": True,
            "write_file": True,
            "edit_file": True,
            "apply_patch": True,
        },
        permissions=base_permissions,
    )

