# MCP Tool Catalog

Dragonglass utilizes several Model Context Protocol (MCP) toolsets, ranging from standard vault operations to custom search logic.

---

## Internal Search Tools

Defined in `dragonglass/mcp/search.py`. These tools manage the core hybrid search state and communicate with the Obsidian REST APIs.

| Tool Name | Signature | Description | Endpoint(s) Called | Sample Response |
|-----------|-----------|-------------|-------------------|-----------------|
| `new_search_session` | `()` | Resets allowlist and hash cache. | - | `{"session_id": "abc123", "status": "created"}` |
| `keyword_search` | `(queries: list[str])` | Merges keyword results into the allowlist. | `POST /search/simple/` (Local REST API) | `{"total_found": 10, "query_count": 2, "preview_paths": ["a.md", "b.md"]}` |
| `vector_search` | `(query, top_n, min_score)` | Restricted semantic search (Focussed). | `POST /search/text` (Custom Server) | `[{"path": "a.md", "score": 0.5}, {"path": "b.md", "score": 0.45}]` |
| `open_note` | `(path: str)` | Opens the specified file in the Obsidian UI. | `POST /open/{path}` (Local REST API) | `{"status": "opened", "path": "a.md"}` |
| `run_command` | `(command_id: str)` | Executes an Obsidian command by ID. | `POST /commands/{id}` (Local REST API) | `{"status": "executed", "command_id": "app:open-settings"}` |
| `read_note_with_hash` | `(path: str)` | Reads content and captures state for patching. | `POST /notes/read` (Custom Server) | `{"path": "a.md", "content": "text...", "content_hash": "sha256...", "line_count": 10}` |
| `patch_note_lines` | `(path, start, end, repl, hash)` | Atomic, hash-gated replacement of lines. | `POST /notes/patch-lines` (Custom Server) | `{"path": "a.md", "new_hash": "sha256...", "new_line_count": 11}` |

---

## Obsidian MCP Server Tools

Injected via the `obsidian-mcp-server`. These provide comprehensive vault access via the `obsidian-local-rest-api`.

| Tool Name | Arguments | Description |
|-----------|-----------|-------------|
| `obsidian_list_notes` | `dirPath`, `recursionDepth` | Lists files and folders. |
| `obsidian_global_search` | `query`, `searchInPath` | Text-based search across the entire vault. |
| `obsidian_update_note` | `targetIdentifier`, `modificationType`, `content` | Create or update a note (append, prepend, overwrite). |
| `obsidian_search_replace` | `targetIdentifier`, `replacements` | Multi-line string/regex replacement. |
| `obsidian_delete_note` | `filePath` | Deletes a note from the vault. |
| `obsidian_manage_frontmatter` | `filePath`, `operation`, `key`, `value` | Atomically manage YAML metadata. |
| `obsidian_manage_tags` | `filePath`, `operation`, `tags` | Manage note-level tags (add/remove). |

---

## External Utility Tools

Standard MCP servers for additional functionality.

| Tool Name | Server | Description |
|-----------|--------|-------------|
| `fetch` | `mcp-server-fetch` | Retrieves raw content from any public URL. |
| `sequentialthinking` | `server-sequential-thinking` | Allows the agent to use a "Chain of Thought" scratchpad. |

---

## Atomic Patching Pattern

The `patch_note_lines` tool is the preferred way for the agent to modify a file without overwriting external changes.

1. **Read**: `read_note_with_hash(path)` -> Get `content_hash` and `content`.
2. **Compute**: The agent computes exact line numbers to change based on the returned content.
3. **Patch**: `patch_note_lines(path, start, end, replacement)` -> Sends the hash back to the server.
4. **Validate**: The custom Obsidian plugin confirms the `expected_hash` matches current disk state.
5. **Update**: If valid, the patch is applied and a `new_hash` is returned and stored in the session.
6. **Retry**: If a `hash_mismatch` occurs, the agent is instructed to read again and retry once.
