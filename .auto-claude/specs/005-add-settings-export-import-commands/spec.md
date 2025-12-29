# Add Settings Export/Import Commands

## Overview

Add slash commands to export current merged settings to a file and import settings from a file. This makes it easier to share configurations between projects or team members.

## Rationale

The settings.py module has well-defined load_settings() and JSON read/write helpers (_read_json, _write_json). KaiSettings dataclass is serializable. The pattern for slash commands exists in ralph_commands.py. This is a straightforward extension of existing patterns.

---
*This spec was created from ideation and is pending detailed specification.*
