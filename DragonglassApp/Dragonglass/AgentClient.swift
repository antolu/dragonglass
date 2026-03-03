import Foundation
import Combine

enum AgentEvent: Codable {
    case status(String)
    case assistantMessage(String)
    case error(String, String)
    case done
    case fileAccess(String, String)
    case config(DragonglassConfig)
    case configAck
    case modelsList([String])
    case usage(Int, Int, Int, Int)
    case userMessage(String)
    case conversationsList([ConversationMetadata])
    case conversationLoaded(String, [AgentEvent])
    case unknown(String)

    enum CodingKeys: String, CodingKey {
        case type
        case message
        case text
        case tool
        case error
        case path
        case operation
        case models
        case promptTokens = "prompt_tokens"
        case completionTokens = "completion_tokens"
        case totalTokens = "total_tokens"
        case sessionTotal = "session_total"
        case conversations
        case id
        case history
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .type)

        switch type {
        case "StatusEvent", "statusevent":
            self = .status(try container.decode(String.self, forKey: .message))
        case "TextChunk", "textchunk":
            self = .assistantMessage(try container.decode(String.self, forKey: .text))
        case "ToolErrorEvent", "toolerrorevent":
            self = .error(try container.decode(String.self, forKey: .tool), try container.decode(String.self, forKey: .error))
        case "DoneEvent", "doneevent":
            self = .done
        case "FileAccessEvent", "fileaccessevent":
            self = .fileAccess(try container.decode(String.self, forKey: .path), try container.decode(String.self, forKey: .operation))
        case "config":
            self = .config(try DragonglassConfig(from: decoder))
        case "config_ack":
            self = .configAck
        case "models_list", "ModelsListEvent":
            self = .modelsList(try container.decode([String].self, forKey: .models))
        case "UsageEvent", "usageevent":
            self = .usage(
                try container.decode(Int.self, forKey: .promptTokens),
                try container.decode(Int.self, forKey: .completionTokens),
                try container.decode(Int.self, forKey: .totalTokens),
                try container.decode(Int.self, forKey: .sessionTotal)
            )
        case "ConversationsListEvent", "conversations_list":
            self = .conversationsList(try container.decode([ConversationMetadata].self, forKey: .conversations))
        case "ConversationLoadedEvent", "conversation_loaded":
            self = .conversationLoaded(try container.decode(String.self, forKey: .id), try container.decode([AgentEvent].self, forKey: .history))
        default:
            self = .unknown(type)
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = try encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case .status(let msg):
            try container.encode("StatusEvent", forKey: .type)
            try container.encode(msg, forKey: .message)
        case .assistantMessage(let msg):
            try container.encode("TextChunk", forKey: .type)
            try container.encode(msg, forKey: .text)
        case .error(let tool, let err):
            try container.encode("ToolErrorEvent", forKey: .type)
            try container.encode(tool, forKey: .tool)
            try container.encode(err, forKey: .error)
        case .done:
            try container.encode("DoneEvent", forKey: .type)
        case .fileAccess(let path, let op):
            try container.encode("FileAccessEvent", forKey: .type)
            try container.encode(path, forKey: .path)
            try container.encode(op, forKey: .operation)
        case .config(let config):
            try container.encode("config", forKey: .type)
            try config.encode(to: encoder)
        case .configAck:
            try container.encode("config_ack", forKey: .type)
        case .modelsList(let models):
            try container.encode("models_list", forKey: .type)
            try container.encode(models, forKey: .models)
        case .usage(let pt, let ct, let tt, let st):
            try container.encode("UsageEvent", forKey: .type)
            try container.encode(pt, forKey: .promptTokens)
            try container.encode(ct, forKey: .completionTokens)
            try container.encode(tt, forKey: .totalTokens)
            try container.encode(st, forKey: .sessionTotal)
        case .userMessage(let msg):
            try container.encode("user_message", forKey: .type)
            try container.encode(msg, forKey: .message)
        case .conversationsList(let list):
            try container.encode("conversations_list", forKey: .type)
            try container.encode(list, forKey: .conversations)
        case .conversationLoaded(let id, let history):
            try container.encode("conversation_loaded", forKey: .type)
            try container.encode(id, forKey: .id)
            try container.encode(history, forKey: .history)
        case .unknown(let type):
            try container.encode(type, forKey: .type)
        }
    }
}

struct ConversationMetadata: Codable, Identifiable {
    let id: String
    let title: String
    let updatedAt: Double

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case updatedAt = "updated_at"
    }
}

@MainActor
class AgentClient: ObservableObject {
    @Published var events: [AgentEvent] = []
    @Published var isConnected = false
    @Published var isThinking = false
    @Published var availableModels: [String] = []
    @Published var extraModels: [String] = []
    @Published var selectedModel: String = ""
    @Published var conversations: [ConversationMetadata] = []
    @Published var activeConversationId: String?

    private var webSocketTask: URLSessionWebSocketTask?
    private let url = URL(string: "ws://localhost:51363")!

    func connect() {
        webSocketTask = URLSession.shared.webSocketTask(with: url)
        webSocketTask?.resume()
        isConnected = true
        receiveMessage()
        refreshState()
    }

    func disconnect() {
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        isConnected = false
    }

    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            guard let self else { return }
            Task { @MainActor in
                switch result {
                case .success(let message):
                    switch message {
                    case .string(let text):
                        if let data = text.data(using: .utf8) {
                            do {
                                let event = try JSONDecoder().decode(AgentEvent.self, from: data)

                                switch event {
                                case .assistantMessage(let chunk):
                                    if case .assistantMessage(let existing) = self.events.last {
                                        self.events[self.events.count - 1] = .assistantMessage(existing + chunk)
                                    } else {
                                        self.events.append(event)
                                    }
                                case .status, .error, .done, .fileAccess:
                                    self.events.append(event)
                                case .conversationsList(let list):
                                    self.conversations = list
                                case .conversationLoaded(let id, let history):
                                    self.activeConversationId = id
                                    self.events = history
                                    self.isThinking = false
                                case .modelsList(let models):
                                    self.availableModels = models
                                case .config(let config):
                                    self.extraModels = config.extraModels ?? []
                                    self.selectedModel = config.selectedModel ?? ""
                                case .userMessage:
                                    self.events.append(event)
                                case .unknown, .usage, .configAck:
                                    // These are system events or unknown, don't show in chat
                                    break
                                }
                            } catch {
                                print("[AgentClient] Failed to decode event: \(error) from message: \(text)")
                            }
                        }
                    default: break
                    }
                    self.receiveMessage()
                case .failure:
                    self.isConnected = false
                }
            }
        }
    }

    func sendChat(text: String, model: String? = nil) {
        isThinking = true
        events.append(.userMessage(text))
        var command: [String: Any] = [
            "command": "chat",
            "text": text
        ]
        if let model = model {
            command["model"] = model
        }
        send(command)
    }

    func fetchConfig() async throws -> DragonglassConfig {
        if !isConnected {
            connect()
            // Wait briefly for connection to establish
            for _ in 0..<10 {
                if isConnected { break }
                try? await Task.sleep(nanoseconds: 50_000_000) // 50ms chunks
            }
        }

        let command: [String: Any] = ["command": "get_config"]
        let currentCount = events.count
        send(command)

        for await updatedEvents in $events.values {
            if updatedEvents.count > currentCount {
                for event in updatedEvents.suffix(updatedEvents.count - currentCount) {
                    if case .config(let config) = event {
                        return config
                    }
                }
            }
        }
        throw NSError(domain: "AgentClient", code: 1, userInfo: [NSLocalizedDescriptionKey: "Failed to fetch config"])
    }

    func setConfig(_ config: DragonglassConfig) async throws {
        guard let data = try? JSONEncoder().encode(config),
              let dict = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }

        let command: [String: Any] = [
            "command": "set_config",
            "config": dict
        ]
        send(command)
    }

    func stopChat() {
        send(["command": "stop"])
    }

    func fetchModels() {
        send(["command": "list_models"])
    }

    func refreshState() {
        send(["command": "get_config"])
        fetchModels()
    }

    func saveModel(_ name: String) {
        send(["command": "save_model", "name": name])
    }

    func setSelectedModel(_ model: String) {
        let trimmedModel = model.trimmingCharacters(in: .whitespacesAndNewlines)
        let command: [String: Any] = [
            "command": "set_config",
            "config": ["selected_model": trimmedModel]
        ]
        send(command)
        self.selectedModel = trimmedModel
    }

    func startNewChat() {
        send(["command": "new_chat"])
        events = []
        activeConversationId = nil
    }

    func fetchConversations() {
        send(["command": "list_conversations"])
    }

    func loadConversation(id: String) {
        send(["command": "load_conversation", "id": id])
    }

    func deleteConversation(id: String) {
        send(["command": "delete_conversation", "id": id])
    }

    private func send(_ dict: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: dict),
              let string = String(data: data, encoding: .utf8) else { return }
        webSocketTask?.send(.string(string)) { error in
            if let error = error {
                print("WebSocket send error: \(error)")
            }
        }
    }
}
