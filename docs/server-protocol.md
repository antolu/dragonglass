# WebSocket Protocol Reference

Dragonglass's frontend and backend communicate via a JSON-over-WebSocket protocol on port 51363.

## Frontend to Backend (Commands)

### chat
Starts a message reasoning session. Cancels any existing chat task.
```json
{
  "command": "chat",
  "text": "What are my AI notes about?",
  "model": "ollama_chat/llama3.2" // Optional model override
}
```

### stop
Immediately cancels the current LLM turn/task.
```json
{ "command": "stop" }
```

### get_config / set_config
Retrieves or updates backend settings (Ollama URL, default model, etc).
```json
{ "command": "get_config" }
{ "command": "set_config", "config": { "llm_model": "..." } }
```

### list_models / save_model
Lists available models from the local Ollama instance and saves custom model selection.

### list_conversations / load_conversation / delete_conversation
Management of chat history files stored in XDG_DATA_HOME/dragonglass/conversations/.

---

## Backend to Frontend (Events)

### TextChunk
A chunk of the LLM's streaming response content.
```json
{ "type": "TextChunk", "text": "The latest..." }
```

### StatusEvent
High-level tool execution status for the UI pill notification.
```json
{ "type": "StatusEvent", "message": "searching: AI notes" }
```

### FileAccessEvent
Detailed log of which file is being accessed and with what operation.
```json
{ "type": "FileAccessEvent", "path": "notes/ai.md", "operation": "read" }
```

### UsageEvent
Token metrics for the current exchange.
```json
{
  "type": "UsageEvent",
  "prompt_tokens": 120,
  "completion_tokens": 45,
  "total_tokens": 165,
  "session_total": 450
}
```

### DoneEvent
Sent when a chat task has completed or was cancelled.
```json
{ "type": "DoneEvent" }
```

### ConversationsListEvent / ConversationLoadedEvent
Metadata or full history content of an existing chat.

### ToolErrorEvent
Informative error if a specific tool (e.g., patch_note_lines) fails.
```json
{ "type": "ToolErrorEvent", "tool": "patch_note_lines", "error": "hash_mismatch" }
```
