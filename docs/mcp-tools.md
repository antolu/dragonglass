# MCP Tool Catalog

Dragonglass utilizes several Model Context Protocol (MCP) toolsets, ranging from standard vault operations to custom search logic.

---

## Internal Search Tools

Defined in `dragonglass/mcp/search.py`. These tools manage the core hybrid search state and communicate with the Obsidian REST APIs.

| Tool Name | Signature | Description | Endpoint(s) Called | Sample Response |
|-----------|-----------|-------------|-------------------|-----------------|
| `dragonglass_new_search_session` | `()` | Resets allowlist and hash cache. | - | `{"session_id": "abc123", "status": "created"}` |
| `dragonglass_keyword_search` | `(queries: list[str])` | Merges keyword results into the allowlist. | `POST /search/simple/` | `{"total_found": 10, "query_count": 2, "preview_paths": ["a.md", "b.md"]}` |
| `dragonglass_vector_search` | `(query, top_n, min_score)` | Restricted semantic search within current context. | `POST /search/text` | `[{"path": "a.md", "score": 0.5}, {"path": "b.md", "score": 0.45}]` |
| `dragonglass_open_note` | `(path: str)` | Opens the specified file in the Obsidian UI. | `POST /open/{path}` | `{"status": "opened", "path": "a.md"}` |
| `dragonglass_run_command` | `(command_id: str)` | Executes an Obsidian command by ID. | `POST /commands/{id}` | `{"status": "executed", "command_id": "app:open-settings"}` |
| `dragonglass_read_note_with_hash` | `(path: str, start_line?: int, end_line?: int)` | Reads content and captures file hash for patching. | `GET /notes/read` | `{"path": "a.md", "content": "text...", "content_hash": "sha256...", "line_count": 10}` |
| `dragonglass_patch_note_lines` | `(path, start_line, end_line, replacement, expected_hash?)` | Atomic, hash-gated line replacement. | `PATCH /notes/patch-lines` | `{"path": "a.md", "new_hash": "sha256...", "new_line_count": 11}` |
| `dragonglass_manage_frontmatter` | `(path, operation, key, value?)` | Gets, sets, or deletes YAML frontmatter keys. | `GET /notes/read` + `PATCH /notes/patch-lines` | `{"path": "a.md", "operation": "set", "key": "status", "value": "done"}` |
| `dragonglass_manage_tags` | `(path, operation, tags?)` | Lists, adds, or removes tags in frontmatter and inline content. | `GET /notes/read` + `PATCH /notes/patch-lines` | `{"path": "a.md", "operation": "add", "added": ["project"], "tags": ["project"]}` |

---

## External MCP Tools

External servers currently provide utility tools only.

| Tool Name | Server | Description |
|-----------|--------|-------------|
| `fetch` | `mcp-server-fetch` | Retrieves raw content from a public URL. |

---

`sequentialthinking` is currently disabled at runtime.

---

## Atomic Patching Pattern

The `dragonglass_patch_note_lines` tool is the preferred way for the agent to modify a file without overwriting external changes.

1. **Read**: `dragonglass_read_note_with_hash(path)` -> Get `content_hash` and `content`.
2. **Compute**: The agent computes exact line numbers to change based on the returned content.
3. **Patch**: `dragonglass_patch_note_lines(path, start_line, end_line, replacement)` -> Sends the hash back to the server.
4. **Validate**: The custom Obsidian plugin confirms the `expected_hash` matches current disk state.
5. **Update**: If valid, the patch is applied and a `new_hash` is returned and stored in the session.
6. **Retry**: If a `hash_mismatch` occurs, the agent is instructed to read again and retry once.
