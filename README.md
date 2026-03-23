# Dragonglass

Dragonglass is a hybrid local/AI knowledge management system for your Obsidian vault. It combines a native macOS interface with a Python-based agent loop and now ships a bundled Obsidian plugin for local semantic search.

## Prerequisites

Minimal runtime requirements:

1.  **Ollama**: Ensure [Ollama](https://ollama.com/) is installed and running (used for embeddings and local LLM models).
2.  **Embedding Model**: Have an embedding model available in Ollama (e.g., `nomic-embed-text`).

Optional / replaced items

- Older releases required the **Obsidian Local REST API** plugin; that legacy dependency has been removed from the Python backend. Dragonglass now includes tooling to bundle and deploy our maintained `obsidian-plugin` instead.
- You can still use a separate `obsidian-vector-search-server` if you prefer, but an official `obsidian-plugin` is included as a submodule and can be bundled into the macOS app.

## Components

### macOS Application
The primary user experience is the native macOS app in `DragonglassApp/`. New additions in this branch include:
- An Obsidian setup wizard to configure and persist your vault path.
- Redesigned Settings UI with advanced env settings and save-state UX.
- Built-in support to bundle and deploy the included Obsidian plugin to the user's vault.

### Python Backend
Runs the agent loop and MCP server infrastructure. The backend has been refactored to remove the legacy Obsidian REST API dependency where applicable.

Install and run:
```bash
pip install -e ".[dev]"
dragonglass
```

## Bundled plugin and tooling

We now ship an `obsidian-plugin` submodule and scripts to create distributable plugin artifacts used by the macOS app:

- `obsidian-plugin/` — plugin source (submodule)
- `scripts/bundle_plugin.sh` — convenience script to build and package plugin artifacts
- `DragonglassApp/scripts/bundle_resources.sh` — app-side resource bundling

When cloning the repository, initialize submodules:

```bash
git submodule update --init --recursive
```

## Configuration and Logs

Dragonglass uses standard XDG directories to store state. Most settings can be configured via the macOS App's settings view.

- **Configuration**: `~/.config/dragonglass/config.toml`
- **Conversation History**: `~/.local/share/dragonglass/conversations/`
- **Logs and Cache**: `~/.cache/dragonglass/`

## Usage

Type naturally to interact with your vault via the macOS app or the Python CLI:

- `remember that I like cookies`
- `what do I know about Melanie?`

### Installer / Setup

Open `DragonglassApp/Dragonglass.xcodeproj` in Xcode and run the app to use the new Obsidian setup wizard. The wizard can bundle and deploy the included plugin to your configured vault.

### Developer Documentation

For detailed information on architecture, API, and tools, see the [Developer Guide](docs/index.md).

## Commands (Internal)

Internal agent slash commands are in development.
