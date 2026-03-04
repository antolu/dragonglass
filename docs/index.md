# Dragonglass: Developer Documentation

Welcome to the internal developer documentation for Dragonglass. This documentation is split into several modules for easier navigation and depth.

## Documentation Modules

- [Architecture & Data Flow](architecture.md): High-level system design and component interactions.
- [Custom Obsidian API](rest-api.md): Reference for the obsidian-vector-search-server plugin.
- [MCP Tool Catalog](mcp-tools.md): Exhaustive list of all tools available to the AI agent.
- [Agent Logic & Prompts](agent-loop.md): Details on the thinking loop, system instructions, and litellm integration.
- [WebSocket Protocol](server-protocol.md): Communication interface between the Swift frontend and Python backend.
- [Configuration & Paths](configuration.md): XDG standards, environment variables, and config.toml settings.

## Getting Started

Dragonglass is a hybrid local/AI knowledge management system. It bridges a native macOS user interface with a powerful Python-based agent loop that has direct, programmatic access to your Obsidian vault.

### Key Technologies
- **Frontend**: Swift, SwiftUI, AppKit (macOS).
- **Backend**: Python 3.13+, Asyncio, WebSockets.
- **AI Integration**: litellm (supports Ollama, Gemini, Claude, etc).
- **MCP Integration**: fastmcp and stdio_client (via obsidian-mcp-server).
- **Search**: Hybrid Keyword (Simple REST) + Semantic (custom vector plugin).
