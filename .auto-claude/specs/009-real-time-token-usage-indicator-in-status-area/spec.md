# Real-Time Token Usage Indicator in Status Area

## Overview

Add an optional token counter to the bottom toolbar or status area that shows context size growing in real-time, with visual warnings when approaching context limits.

## Rationale

Token usage is hidden behind /tokens command. Power users managing long conversations need visibility into context growth to know when to use /clear. The current TokenTracker class tracks tokens but only displays on-demand. Context limits vary by model (4K to 200K+) and users have no warning before hitting limits.

---
*This spec was created from ideation and is pending detailed specification.*
