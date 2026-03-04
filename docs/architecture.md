# Architecture & Data Flow

Dragonglass is architected as a decoupled system. The frontend handles the user experience, while the backend orchestrates the AI agent and its interactions with the knowledge vault.

## System Components

```text
+-----------------------+      +---------------------------+      +--------------------------+
|  Dragonglass Frontend | <--- |  Dragonglass Backend      | <--- |  Obsidian MCP Server     |
|  (Swift/macOS App)    | ---> |  (Python WebSockets)      | ---> |  (npx-managed process)   |
+-----------------------+      +-------------+-------------+      +--------------------------+
                                             |
                                             v
                               +-------------+-------------+      +--------------------------+
                               |  VaultAgent (Core Logic)  | <--- |  Vector Search Server    |
                               |  (litellm + Tool Calling) | ---> |  (Obsidian Plugin API)   |
                               +-------------+-------------+      +--------------------------+
                                             |
                                             v
                               +-------------+-------------+
                               |  Internal Search Tools    |
                               |  (keyword, vector, patch) |
                               +---------------------------+
```

### 1. Swift Frontend (DragonglassApp)
- A native macOS application written in SwiftUI.
- Manages the WebSocket connection to the Python backend.
- Handles user input, markdown rendering for LLM messages, and system notifications.
- Displays high-level status "pills" (e.g., "searching", "reading", "thinking").

### 2. Python Backend (dragonglass.server)
- An asyncio-based server running on a local port (default: 51363).
- Implements the WebSocket protocol to handle chat commands, configuration updates, and conversation management.
- Instantiates the VaultAgent and routes events (Streaming text, tool status, usage metrics) back to the frontend.

### 3. AI Agent (dragonglass.agent.agent)
- Uses LiteLLM to provide a provider-agnostic interface to LLMs (supports Ollama, Gemini, Claude, etc).
- Orchestrates the Reasoning Loop for tool execution and response generation.
- Managed by VaultAgent, which also handles the lifecycle of multiple MCP (Model Context Protocol) servers.

### 4. Obsidian Integration
Dragonglass integrates with Obsidian via two complementary methods:
- **obsidian-local-rest-api**: A standard third-party plugin providing broad CRUD operations.
- **obsidian-vector-search-server** (Our Plugin): Provides fast local embeddings, hybrid semantic search, and hash-gated line patching.

## Interaction Flows

### Global Chat Flow
1. User types "Find my notes on AI".
2. **Frontend** sends command to **Backend** over WebSocket.
3. **Agent** creates reasoning plan, status events are streamed to UI.
4. **Agent** hits Obsidian APIs via MCP tools.
5. **Agent** finalizes answer and streams result.

### Hybrid Search Scenario
Search sessions allow for "focussed search": using keywords to narrow down the space, then semantic search to find the most relevant fragment.

```text
+-----------------------+       +-------------------------+       +------------------------+
|  VaultAgent.run()     |       |  Internal Search Tools  |       |  SearchSession (State) |
+-----------+-----------+       +------------+------------+       +------------+-----------+
            |                                |                                 |
            | 1. new_search_session()        |                                 |
            +------------------------------->|                                 |
            |                                | 2. Reset session state          |
            |                                +-------------------------------->|
            |                                |                                 |
            | 3. keyword_search("query")     |                                 |
            +------------------------------->|                                 |
            |                                | 4. Search via Obsidian API      |
            |                                +-------------------------------->|
            |                                | 5. Update allowlist             |
            |                                |                                 |
            | 6. vector_search("text")       |                                 |
            +------------------------------->|                                 |
            |                                | 7. Restrict results by allowlist|
            |                                +<--------------------------------+
            |                                | 8. Search via custom server     |
            |                                +-------------------------------->|
            |                                |                                 |
+-----------v-----------+       +------------v------------+       +------------v-----------+
```
