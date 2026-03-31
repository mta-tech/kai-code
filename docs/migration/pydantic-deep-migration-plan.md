# kai-code Migration: LangChain DeepAgents → Pydantic-DeepAgents

**Date:** April 1, 2026  
**Status:** Planning Phase  
**Estimated Effort:** 4-6 hours

---

## 🎯 **Migration Objectives**

### **Why Migrate?**
1. ✅ **Lighter dependencies** — Drop langchain/langgraph/langsmith
2. ✅ **Hooks capability** — Claude Code-style lifecycle hooks (PRE_TOOL_USE, deny/modify)
3. ✅ **Better context management** — Auto-summarization for unlimited context
4. ✅ **Checkpoints** — Save, rewind, fork conversations
5. ✅ **Cost tracking** — Token/USD budget enforcement
6. ✅ **Cleaner API** — Simpler tool definition, better DX
7. ✅ **Teams capability** — Multi-agent with shared TODOs

### **Trade-offs**
- ❌ **Migration effort** — 4-6 hours for full migration
- ❌ **Learning curve** — New API patterns
- ❌ **Less mature** — Pydantic-deep is newer than LangChain
- ✅ **Better aligned** — With Claude Code / Manus AI architecture

---

## 📋 **Migration Phases**

### **Phase 1: Setup & Dependencies (30 min)**

**Tasks:**
1. Create migration branch
2. Update `pyproject.toml` dependencies
3. Install new dependencies
4. Verify pydantic-deep installation

**Changes:**
```toml
# Remove:
- deepagents>=0.2.8
- langchain
- langchain-google-genai
- langchain-openai
- langgraph

# Add:
+ pydantic-deep>=0.3.0
+ pydantic-ai>=1.71.0
```

**Commands:**
```bash
cd kai-code
git checkout -b feat/pydantic-deep-migration
# Update pyproject.toml
pip3 install -e .
```

---

### **Phase 2: Core Agent Migration (2-3 hours)**

#### **2.1: Migrate agent.py**

**Current Pattern (LangChain):**
```python
from deepagents import create_deep_agent
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver

@tool
def read_file(path: str) -> str:
    """Read file contents."""
    with open(path) as f:
        return f.read()

agent = create_deep_agent(
    model="google_genai:gemini-2.0-flash",
    tools=[read_file],
    checkpointer=MemorySaver()
)
```

**Target Pattern (Pydantic):**
```python
from pydantic_ai import RunContext
from pydantic_deep import create_deep_agent, DeepAgentDeps, StateBackend

async def read_file(
    ctx: RunContext[DeepAgentDeps],
    path: str
) -> str:
    """Read file contents."""
    return ctx.deps.backend.read(path)

agent = create_deep_agent(
    model="google-gla:gemini-2.0-flash",
    tools=[read_file],
    include_filesystem=True,
    context_manager=True,
)

deps = DeepAgentDeps(backend=StateBackend())
result = await agent.run("Read the README", deps=deps)
```

**Migration Steps:**
1. Replace imports
2. Convert tools to async functions with RunContext
3. Replace `create_deep_agent()` call
4. Add `deps` parameter to all `agent.run()` calls
5. Replace checkpointer with StateBackend

---

#### **2.2: Migrate Tools (12 tools)**

**Current Tools to Migrate:**
1. `read_file` → Use backend.read()
2. `write_file` → Use backend.write()
3. `edit_file` → Use backend.edit()
4. `execute_shell` → Use backend.execute()
5. `glob_files` → Use backend.glob()
6. `grep_content` → Use backend.grep()
7. `load_skill` → Keep as custom tool
8. `unload_skill` → Keep as custom tool
9. `list_skills` → Keep as custom tool
10. `http_request` → Keep as custom tool
11. `web_search` → Use include_web=True
12. `fetch_url` → Use include_web=True

**Migration Pattern:**
```python
# Before:
@tool
def read_file(path: str) -> str:
    """Read file."""
    with open(path) as f:
        return f.read()

# After:
async def read_file(
    ctx: RunContext[DeepAgentDeps],
    path: str
) -> str:
    """Read file."""
    return ctx.deps.backend.read(path)
```

---

#### **2.3: Migrate Streaming**

**Current Pattern (LangGraph):**
```python
async for event in agent.astream_events(prompt, version="v2"):
    if event["event"] == "on_tool_start":
        print(f"Tool: {event['name']}")
    elif event["event"] == "on_tool_end":
        print(f"Result: {event['data']['output']}")
```

**Target Pattern (Pydantic):**
```python
from pydantic_ai._agent_graph import CallToolsNode, End, ModelRequestNode

async with agent.iter(prompt, deps=deps) as run:
    async for node in run:
        if isinstance(node, CallToolsNode):
            for part in node.model_response.parts:
                if hasattr(part, "tool_name"):
                    print(f"Tool: {part.tool_name}")
```

**Migration Steps:**
1. Replace `astream_events()` with `iter()`
2. Update event handling to node-based
3. Simplify streaming logic

---

#### **2.4: Migrate Providers**

**Current Pattern:**
```python
from langchain.chat_models import init_chat_model

model = init_chat_model("google_genai:gemini-2.0-flash")
```

**Target Pattern:**
```python
# Direct string model IDs:
model = "google-gla:gemini-2.0-flash"  # Google
model = "openai:gpt-4.1"               # OpenAI
model = "anthropic:claude-sonnet-4-20250514"  # Anthropic
```

**Supported Providers:**
- `google-gla:*` — Google Generative AI
- `openai:*` — OpenAI
- `anthropic:*` — Anthropic
- `ollama:*` — Ollama (local)

---

### **Phase 3: Harness Integration (1-2 hours)**

**Current Integration:**
```python
from kai_code.harness import create_harness

harness = create_harness()
should_exec, reason = harness.check_before_tool("read_file", {"path": "test.py"})
```

**Target Integration:**
```python
# Use pydantic-deep hooks instead!
from pydantic_deep import Hook, HookEvent

agent = create_deep_agent(
    hooks=[
        Hook(
            event=HookEvent.PRE_TOOL_USE,
            command="python /path/to/harness_hook.py",
        ),
    ],
)
```

**Migration Strategy:**
1. **Option A:** Keep harness as external hooks
2. **Option B:** Rewrite harness as Capabilities
3. **Option C:** Hybrid (harness middleware + hooks)

**Recommendation:** **Option A** (simplest)
- Convert harness checks to hook scripts
- Use environment variables to pass tool context
- Keep harness library as utility

---

### **Phase 4: CLI & Testing (1-2 hours)**

**Tasks:**
1. Update CLI commands
2. Test all functionality
3. Update documentation
4. Create migration guide

**CLI Changes:**
- No changes needed (CLI uses agent.run())
- Streaming update: Use iter() instead of astream_events()

---

### **Phase 5: Documentation (30 min)**

**Docs to Update:**
1. README.md — Installation and usage
2. ARCHITECTURE.md — New architecture
3. MIGRATION.md — Step-by-step guide
4. CHANGELOG.md — Migration notes

---

## 🔧 **Migration Commands**

```bash
# 1. Create branch
git checkout -b feat/pydantic-deep-migration

# 2. Update dependencies
# Edit pyproject.toml

# 3. Install
pip3 install -e .

# 4. Migrate files (manual)
# - agent.py
# - tools/*.py
# - streaming.py
# - providers.py

# 5. Test
pytest tests/
python3 -m kai_code.cli chat

# 6. Commit
git add .
git commit -m "feat: migrate to pydantic-deepagents"
git push -u origin feat/pydantic-deep-migration
```

---

## 📊 **Success Criteria**

### **Must Have:**
- ✅ All 12 tools working
- ✅ Streaming working
- ✅ Multi-model support (Google, OpenAI, Anthropic, Ollama)
- ✅ Harness integration working
- ✅ All tests passing

### **Nice to Have:**
- ✅ Hooks for harness checks
- ✅ Cost tracking
- ✅ Checkpoints
- ✅ Teams capability

---

## ⚠️ **Risks & Mitigations**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking changes | High | Keep feat/harness-engineering branch as backup |
| Incomplete migration | Medium | Migrate incrementally, test each component |
| Performance regression | Low | Benchmark before/after |
| Missing features | Medium | Check pydantic-deep feature parity first |

---

## 📅 **Timeline**

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 1: Setup | 30 min | 02:30 | 03:00 |
| Phase 2: Core | 3 hours | 03:00 | 06:00 |
| Phase 3: Harness | 1.5 hours | 06:00 | 07:30 |
| Phase 4: CLI & Tests | 1.5 hours | 07:30 | 09:00 |
| Phase 5: Docs | 30 min | 09:00 | 09:30 |
| **Total** | **7 hours** | **02:30** | **09:30** |

---

## 🚀 **Next Steps**

**Fitra: Mulai migrasi sekarang?**

1. **YES** — Saya mulai Phase 1 sekarang
2. **WAIT** — Tunggu approval dari tim
3. **MODIFY** — Ubah rencana dulu

**Recommendation:** Start Phase 1 (low risk, easy to rollback)

---

_Migration Plan by CodeChief — April 1, 2026_
