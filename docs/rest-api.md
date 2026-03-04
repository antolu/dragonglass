# Custom Obsidian API Reference

The obsidian-vector-search-server plugin provides a local HTTP REST API for performing semantic search and atomic file patching in your vault. Dragonglass's internal search tools use this API directly.

All endpoints are **POST** only. The default port is `51362`.

## Semantic Search

### `POST /embed`
Generates a vector embedding for the provided text using the configured Ollama model.
- **Request Body**:
  ```json
  { "text": "my note content" }
  ```
- **Response**:
  ```json
  { "vector": [0.012, -0.456, 0.789, ...] }
  ```

### `POST /search/text`
Performs a semantic search for notes matching the query text.
- **Request Body**:
  ```json
  {
    "text": "machine learning notes",
    "top_n": 10,       // Optional, default: 10
    "min_score": 0.4,   // Optional, default: 0.35
    "allowlist": ["notes/ai.md", "notes/ml.md"] // Optional: restrict search to these paths
  }
  ```
- **Response**:
  ```json
  {
    "results": [
      { "path": "notes/ai.md", "score": 0.85 },
      { "path": "notes/ml.md", "score": 0.78 }
    ]
  }
  ```

### `POST /search/vector`
Performs a semantic search using a pre-computed vector.
- **Request Body**:
  ```json
  {
    "vector": [0.012, ...],
    "top_n": 5,
    "allowlist": []
  }
  ```
- **Response**: Same as `/search/text`.

## File Reading & Patching

### `POST /notes/read`
Reads a note's content and computes a SHA-256 hash for atomic updates.
- **Request Body**:
  ```json
  { "path": "notes/my_note.md" }
  ```
- **Response**:
  ```json
  {
    "path": "notes/my_note.md",
    "content": "# My Note\nContent here...",
    "line_count": 5,
    "content_hash": "a1b2c3d4...",
    "mtime": 1714567890
  }
  ```

### `POST /notes/patch-lines`
Performs atomic line-based edits on a note. Fails if the `expected_hash` doesn't match the current file hash.
- **Request Body**:
  ```json
  {
    "path": "notes/my_note.md",
    "start_line": 2,      // 1-based, inclusive
    "end_line": 3,        // 1-based, inclusive
    "replacement": "Updated line content\nWith multiple lines",
    "expected_hash": "a1b2c3d4..."
  }
  ```
- **Response**:
  ```json
  {
    "path": "notes/my_note.md",
    "applied_start_line": 2,
    "applied_end_line": 3,
    "new_hash": "e5f6g7h8...",
    "new_line_count": 6,
    "mtime": 1714567999
  }
  ```

## Technical Details

- **Locality**: All embeddings are generated locally via Ollama and stored in your vault under `.obsidian/plugins/obsidian-vector-search/index.json`.
- **Indexing**: The plugin automatically detects file changes and updates the index incrementally.
- **Persistence**: The index is saved to disk and loaded on Obsidian startup.
- **Error Handling**: Standard HTTP status codes are used (200 OK, 400 Bad Request if hash mismatch or invalid path).
