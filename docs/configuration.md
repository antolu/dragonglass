# Configuration & Paths

Dragonglass adheres to the XDG Base Directory Specification for consistency across macOS and Linux environments.

## Directories and Paths

All directories are rooted under the dragonglass/ subdirectory within the standard XDG locations.

| Type | Path (macOS default) | Environment Variable | Content |
|------|----------------------|----------------------|---------|
| **Config** | `~/.config/dragonglass/` | `XDG_CONFIG_HOME` | `config.toml`, `extra_models.json` |
| **Data** | `~/.local/share/dragonglass/` | `XDG_DATA_HOME` | `conversations/` ([id].json) |
| **Cache** | `~/.cache/dragonglass/` | `XDG_CACHE_HOME` | Temporary LLM cache, logs, etc. |

### Conversation Storage
Active chats are persisted in `XDG_DATA_HOME/dragonglass/conversations/` as JSON files. They contain the id, title, updated_at timestamp, and the full message history (JSON array of role/content pairs).

## Settings (config.toml)

The backend behavior can be customized via a config.toml file in the configuration directory.

```toml
# Obsidian REST API settings
obsidian_api_url = "http://localhost:27123"
obsidian_api_key = "my-secret-key"

# LLM & Ollama settings
llm_model = "ollama/llama3.2"        # Default provider/model
ollama_url = "http://localhost:11434"
vector_search_url = "http://localhost:51362"

# Agent behavior settings
llm_temperature = 0.4
llm_top_p = 0.9
llm_top_k = 40
llm_min_p = 0.05

# Search & Context settings
agents_note_path = "AGENTS.md"       # Relative to vault root

# Tool permission settings
auto_allow_edit = true               # Patch and Update without asking
auto_allow_create = true
auto_allow_delete = false            # Deletions always require user confirmation
```

### Dynamic Configuration
Configuration is managed using Pydantic Settings.
- The Settings object is initialized on server startup.
- It can be dynamically invalidated (`invalidate_settings()`) when the frontend sends a set_config command.
- The next call to `get_settings()` will re-load the TOML file from disk.

## Environment Variable Overrides

Any setting in the table above can be overridden by setting an environment variable with the same name (case-insensitive) or by using an .env file in the project directory.

Example:
```bash
OBSIDIAN_API_KEY="override-key" DRAGON_LLM_MODEL="gemini/gemini-1.5-flash"
```
