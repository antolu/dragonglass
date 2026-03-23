import Foundation

struct DragonglassConfig: Codable, Equatable {
    var obsidianDir: String
    var ollamaUrl: String
    var vectorSearchUrl: String
    var llmModel: String
    var llmTemperature: Double?
    var llmTopP: Double?
    var llmTopK: Int?
    var llmMinP: Double?
    var extraModels: [String]?
    var envVars: [String: String]?
    var selectedModel: String?
    var llmBackend: String
    var opencodeUrl: String
    var spawnOpencode: Bool
    var agentsNotePath: String
    var autoAllowEdit: Bool
    var autoAllowCreate: Bool
    var autoAllowDelete: Bool

    enum CodingKeys: String, CodingKey {
        case obsidianDir = "obsidian_dir"
        case ollamaUrl = "ollama_url"
        case vectorSearchUrl = "vector_search_url"
        case llmModel = "llm_model"
        case llmBackend = "llm_backend"
        case opencodeUrl = "opencode_url"
        case spawnOpencode = "spawn_opencode"
        case llmTemperature = "llm_temperature"
        case llmTopP = "llm_top_p"
        case llmTopK = "llm_top_k"
        case llmMinP = "llm_min_p"
        case selectedModel = "selected_model"
        case agentsNotePath = "agents_note_path"
        case autoAllowEdit = "auto_allow_edit"
        case autoAllowCreate = "auto_allow_create"
        case autoAllowDelete = "auto_allow_delete"
        case extraModels = "extra_models"
        case envVars = "env_vars"
    }
}
