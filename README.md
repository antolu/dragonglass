# Dragonglass

Dragonglass is a hybrid local/AI knowledge management system for your Obsidian vault. It combines a native macOS interface with a powerful Python-based agent loop.

## Prerequisites

Dragonglass requires two Obsidian plugins and a local LLM infrastructure:

1.  **Obsidian Local REST API**: Install it from the [Obsidian Community Plugins](https://obsidian.md/plugins?id=obsidian-local-rest-api) gallery.
2.  **Obsidian Vector Search Server**: Must be installed manually from our [custom search server repository](https://github.com/antolu/obsidian-vector-search-server).
3.  **Ollama**: Ensure [Ollama](https://ollama.com/) is installed and running.
4.  **Embedding Model**: You must have an embedding model available in Ollama (e.g., `nomic-embed-text`).

## Components

### macOS Application
The primary way to use Dragonglass is via the native macOS app located in `DragonglassApp/`. It provides:
- Streaming message interface
- Real-time status indicators for agent tools
- In-app configuration management
- Conversation history explorer

### Python Backend
Runs the agent loop and MCP server infrastructure.
```bash
pip install -e ".[dev]"
dragonglass
```

## Configuration and Logs

Dragonglass uses standard XDG directories to store state. You do not need to manage a `.env` file manually as all settings can be configured via the macOS App's settings view.

- **Configuration**: `~/.config/dragonglass/config.toml`
- **Conversation History**: `~/.local/share/dragonglass/conversations/`
- **Logs and Cache**: `~/.cache/dragonglass/`

## Usage

Type naturally to interact with your vault:

- `remember that I like cookies`
- `remember that Michael likes flowers`
- `what do I know about Melanie?`

### Developer Documentation

For detailed information on the architecture, API, and tool catalog, see the [Developer Guide](docs/index.md).

## Commands (Internal)

Slash commands available in the agent loop:
- `/autolink` — coming soon
- `/manage` — coming soon
