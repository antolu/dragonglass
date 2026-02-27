import Foundation

struct DragonglassConfig: Codable {
    var obsidianApiUrl: String
    var obsidianApiKey: String
    var ollamaUrl: String
    var vectorSearchUrl: String
    var llmModel: String
    var agentsNotePath: String
    var autoAllowEdit: Bool
    var autoAllowCreate: Bool
    var autoAllowDelete: Bool

    enum CodingKeys: String, CodingKey {
        case obsidianApiUrl = "obsidian_api_url"
        case obsidianApiKey = "obsidian_api_key"
        case ollamaUrl = "ollama_url"
        case vectorSearchUrl = "vector_search_url"
        case llmModel = "llm_model"
        case agentsNotePath = "agents_note_path"
        case autoAllowEdit = "auto_allow_edit"
        case autoAllowCreate = "auto_allow_create"
        case autoAllowDelete = "auto_allow_delete"
    }
}
