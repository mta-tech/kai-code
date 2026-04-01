# Pydantic-Deep Migration Status

**Branch:** `feat/pydantic-deep-migration`
**Started:** 2026-04-01 11:00 WIB
**Status:** Phase 2 in progress

---

## ✅ Phase 1: COMPLETE (11:00-11:05 WIB)

### Tasks Completed
- [x] Create migration branch
- [x] Update `pyproject.toml` dependencies
- [x] Install pydantic-deep + pydantic-ai
- [x] Verify imports working
- [x] Push branch to remote

### Dependencies Replaced
```toml
# Removed (4 packages):
- deepagents>=0.2.8
- langchain>=1.0.7
- langchain-google-genai>=2.0.0
- langchain-openai>=0.2.0

# Added (2 packages):
+ pydantic-deep>=0.3.0
+ pydantic-ai[openai,anthropic,google-gla]>=1.71.0
```

### Commits
- `b7fbb46` - feat: update dependencies for pydantic-deep migration
- `c47fe82` - feat: add pydantic-deep agent (simplified 364 lines vs 738)

---

## 🔄 Phase 2: IN PROGRESS (11:05-11:55 WIB)

### Tasks Completed
- [x] Created `agent_pydantic.py` (364 lines vs 738 lines, 50% reduction)
- [x] Imports working
- [x] Instantiation working
- [x] Agent building working
- [x] API key detection working

### Simplifications Achieved
1. **No LangChain imports** — Pure pydantic-ai ecosystem
2. **No backend parameter** — Filesystem built-in
3. **No checkpointer** — Built-in
4. **String-based models** — No model objects
5. **Simplified config** — 10 vs 12 parameters

### Remaining Tasks
- [ ] Migrate tools (12 tools → async with RunContext)
  - [ ] apply_patch_tool
  - [ ] web_search_tool
  - [ ] fetch_url_tool
  - [ ] http_request_tool
  - [ ] execute_async_tool
  - [ ] load_skill, unload_skill, list_skills, reload_skills
  - [ ] background task tools
- [ ] Implement streaming (iter() vs astream_events())
- [ ] Update run() to handle pydantic-ai result format
- [ ] Test with API keys
- [ ] Update CLI to use new agent
- [ ] Replace agent.py with agent_pydantic.py

---

## 📊 Comparison: LangChain vs Pydantic

| Aspect | LangChain DeepAgents | Pydantic-Deep | Improvement |
|--------|---------------------|---------------|-------------|
| **Dependencies** | 4 packages | 2 packages | 50% reduction |
| **Agent lines** | 738 | 364 | 50% reduction |
| **Model handling** | BaseChatModel objects | String IDs | Simpler |
| **Backend** | Explicit parameter | Built-in | Cleaner |
| **Checkpointer** | Explicit parameter | Built-in | Cleaner |
| **Tools** | @tool decorator | async + RunContext | More explicit |
| **Streaming** | astream_events() | iter() | Simpler |

---

## 🎯 Next Steps

### Immediate (Next 1-2 hours)
1. **Migrate Tools** — Convert 12 tools to async pattern
2. **Implement Streaming** — Use iter() for streaming
3. **Test with API** — Verify full functionality

### Short-term (Next 2-4 hours)
4. **Update CLI** — Use new agent
5. **Create Migration Guide** — Document patterns
6. **Replace old agent** — Make pydantic version default

### Medium-term (Next 1-2 days)
7. **Phase 3: Harness Integration** — Wire harness hooks
8. **Phase 4: Testing** — Full test suite
9. **Phase 5: Documentation** — Update all docs

---

## 🔧 Tool Migration Pattern

**Before (LangChain):**
```python
@tool("read_file")
def read_file(path: str) -> str:
    """Read file contents."""
    with open(path) as f:
        return f.read()
```

**After (Pydantic):**
```python
async def read_file(
    ctx: RunContext[DeepAgentDeps],
    path: str
) -> str:
    """Read file contents."""
    return ctx.deps.backend.read(path)
```

**Changes:**
1. Remove `@tool` decorator
2. Add `ctx: RunContext[DeepAgentDeps]` as first param
3. Make function `async`
4. Use `ctx.deps.backend` for filesystem operations

---

## 📝 Notes

### What Works
- ✅ Agent creation
- ✅ Model configuration
- ✅ System prompt assembly
- ✅ API key detection

### What's Pending
- ⏸️ Tool execution
- ⏸️ Streaming
- ⏸️ Result parsing
- ⏸️ Message history

### What's Better
- ✅ Simpler API
- ✅ Fewer dependencies
- ✅ Smaller codebase
- ✅ Built-in capabilities

---

## 🚧 Known Issues

1. **Tools not migrated** — Need to convert to async pattern
2. **Streaming stub** — Returns placeholder for now
3. **Result parsing** — Need to extract messages from pydantic result
4. **Message history** — Need to integrate with pydantic memory

---

## 📈 Metrics

**Code Reduction:**
- Agent: 738 → 364 lines (50% reduction)
- Dependencies: 4 → 2 packages (50% reduction)
- Complexity: Reduced (no backend/checkpointer management)

**Expected Benefits:**
- Faster startup (fewer imports)
- Lower memory (smaller dependency tree)
- Cleaner code (built-in capabilities)
- Better DX (simpler API)

---

_Migration Status by CodeChief — 2026-04-01 11:55 WIB_
