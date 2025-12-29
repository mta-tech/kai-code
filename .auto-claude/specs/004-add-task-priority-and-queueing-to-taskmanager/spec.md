# Add Task Priority and Queueing to TaskManager

## Overview

Extend TaskManager to support task priorities (high/normal/low) and a proper queue system. High-priority tasks would be executed before normal/low priority tasks when resources are available.

## Rationale

TaskManager already has MAX_CONCURRENT_TASKS limit and tracks task status. The callback system (_callbacks list with on_task_complete) is already in place. Adding priority would reuse the existing _submit_task pattern but with a priority queue.

---
*This spec was created from ideation and is pending detailed specification.*
