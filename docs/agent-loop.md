# Agent Logic & Prompts

The heart of Dragonglass is the VaultAgent, a custom implementation designed for high reliability and vault-focused reasoning.

## The VaultAgent Loop

The agent follows an asynchronous reasoning loop powered by LiteLLM.

1. **System Prompt**: Built by combining global instructions, current context (time/date), and the optional AGENTS.md instruction note from the vault.
2. **User Input**: Added to the current conversation history.
3. **Reasoning Turn**:
   - The agent decides if it needs tools to answer the request.
   - For complex queries, it uses sequentialthinking as a Chain of Thought scratchpad.
4. **Tool Execution**:
   - The agent calls internal (`search.py`) or external (obsidian-mcp-server) tools.
   - Status events and file access events are yielded back to the frontend to keep the user informed.
5. **Observation**: Result from tool execution is appended to the prompt history.
6. **Final Response**: Once sufficient information is gathered, the agent streams the final text response.

## System Instructions

The global instructions include core rules for vault management:
- **Conciseness**: match the style and tone of existing notes.
- **Immediate Response**: end the message abruptly after performing the action or answering the query.
- **Search First**: always search before answering or making changes.
- **Deduplication**: Never duplicate facts that already exist. Prefer updating notes over creating new ones.
- **Language match**: Use the same language as the notes in the vault.

### Search Reasoning
The agent is instructed to use a multi-step search strategy:
1. `new_search_session` to clear state.
2. `keyword_search` with multiple complementary queries (e.g., synonyms).
3. `vector_search` to rank results or perform a fallback semantic search.
4. Stop and inform the user if two rounds of reformulated search return no hits.

## LLM Provider Integration

Dragonglass uses LiteLLM to decouple the code from specific LLM vendors.
- **Provider-Agnostic**: Supports Ollama (`ollama/llama3.2`), Gemini (`gemini/gemini-1.5-pro`), Claude, OpenAI, and more.
- **Parameter Mapping**: Automatically maps parameters like `top_p`, `top_k`, and `min_p` to the corresponding provider's API.
- **Usage Tracking**: Each turn yields a `UsageEvent` containing prompt/completion tokens and a session-wide total.

## Vault-specific Context (AGENTS.md)

If a note named `AGENTS.md` (or the configured `agents_note_path`) exists at the vault root, its content is automatically appended to the system prompt. This allows users to:
- Define vault-specific terminology.
- Provide custom formatting instructions.
- List "Forbidden folders" or "Preferred tags".
- Explain the structure of specific databases or index notes in the vault.
