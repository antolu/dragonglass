import Foundation
import Combine
import OSLog

private let logger = Logger(subsystem: subsystem, category: "AgentClient")

struct ApprovalRequest: Identifiable {
    let id: String
    let tool: String
    let permission: String
    let path: String
    let diff: String
    let description: String
}

enum AgentEvent: Codable {
    case status(String)
    case assistantMessage(String)
    case done
    case config(DragonglassConfig)
    case configAck
    case modelsList([String])
    case usage(Int, Int, Int, Int)
    case userMessage(String)
    case conversationsList([ConversationMetadata])
    case conversationLoaded(String, [AgentEvent])
    case mcpTool(String, String, String, String)
    case approvalRequest(ApprovalRequest)
    case unknown(String)

    enum CodingKeys: String, CodingKey {
        case type
        case message
        case text
        case tool
        case error
        case models
        case promptTokens = "prompt_tokens"
        case completionTokens = "completion_tokens"
        case totalTokens = "total_tokens"
        case sessionTotal = "session_total"
        case conversations
        case id
        case history
        case phase
        case detail
        case requestId = "request_id"
        case permission
        case path
        case diff
        case description
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .type)

        switch type {
        case "StatusEvent", "statusevent":
            self = .status(try container.decode(String.self, forKey: .message))
        case "TextChunk", "textchunk":
            self = .assistantMessage(try container.decode(String.self, forKey: .text))
        case "DoneEvent", "doneevent":
            self = .done
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
        case "UserMessageEvent", "user_message":
            self = .userMessage(try container.decode(String.self, forKey: .message))
        case "MCPToolEvent", "mcptoolevent":
            self = .mcpTool(
                try container.decode(String.self, forKey: .tool),
                try container.decode(String.self, forKey: .phase),
                try container.decode(String.self, forKey: .message),
                (try? container.decode(String.self, forKey: .detail)) ?? ""
            )
        case "ApprovalRequestEvent":
            self = .approvalRequest(ApprovalRequest(
                id: try container.decode(String.self, forKey: .requestId),
                tool: try container.decode(String.self, forKey: .tool),
                permission: try container.decode(String.self, forKey: .permission),
                path: try container.decode(String.self, forKey: .path),
                diff: try container.decode(String.self, forKey: .diff),
                description: try container.decode(String.self, forKey: .description)
            ))
        default:
            self = .unknown(type)
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case .status(let msg):
            try container.encode("StatusEvent", forKey: .type)
            try container.encode(msg, forKey: .message)
        case .assistantMessage(let msg):
            try container.encode("TextChunk", forKey: .type)
            try container.encode(msg, forKey: .text)
        case .done:
            try container.encode("DoneEvent", forKey: .type)
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
            try container.encode("UserMessageEvent", forKey: .type)
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
        case .mcpTool(let tool, let phase, let message, let detail):
            try container.encode("MCPToolEvent", forKey: .type)
            try container.encode(tool, forKey: .tool)
            try container.encode(phase, forKey: .phase)
            try container.encode(message, forKey: .message)
            try container.encode(detail, forKey: .detail)
        case .approvalRequest:
            break
        }
    }
}

struct ChatTurn: Identifiable {
    let id: Int
    let userMessageIndex: Int
    var toolCallIndices: [Int] = []
    var assistantMessageIndex: Int?
    var doneIndex: Int?
    var isCompleted: Bool { doneIndex != nil }
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
    @Published var llmBackend: String = "litellm"
    @Published var pendingApproval: ApprovalRequest?
    @Published var detailedToolEvents: Bool = UserDefaults.standard.bool(forKey: "detailedToolEvents") {
        didSet { UserDefaults.standard.set(detailedToolEvents, forKey: "detailedToolEvents") }
    }

    var turns: [ChatTurn] {
        var result: [ChatTurn] = []
        var current: ChatTurn?

        for (index, event) in events.enumerated() {
            switch event {
            case .userMessage:
                if let c = current { result.append(c) }
                current = ChatTurn(id: index, userMessageIndex: index)
            case .mcpTool:
                current?.toolCallIndices.append(index)
            case .assistantMessage:
                if current?.assistantMessageIndex == nil {
                    current?.assistantMessageIndex = index
                }
            case .done:
                current?.doneIndex = index
            default:
                break
            }
        }
        if let c = current { result.append(c) }
        return result
    }

    var prefixEventIndices: [Int] {
        var result: [Int] = []
        for (index, event) in events.enumerated() {
            if case .userMessage = event { break }
            switch event {
            case .status, .configAck:
                result.append(index)
            default:
                break
            }
        }
        return result
    }

    private var webSocketTask: URLSessionWebSocketTask?
    private let url = URL(string: "ws://localhost:51363")!

    func connect() {
        logger.info("connect start url=\(self.url.absoluteString, privacy: .public)")
        webSocketTask = URLSession.shared.webSocketTask(with: url)
        webSocketTask?.resume()
        isConnected = true
        receiveMessage()
        refreshState()
        logger.info("connect ready")
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
                                case .status:
                                    self.events.append(event)
                                case .mcpTool:
                                    self.events.append(event)
                                case .done:
                                    self.events.append(event)
                                    self.isThinking = false
                                case .config(let config):
                                    self.extraModels = config.extraModels ?? []
                                    self.selectedModel = config.selectedModel ?? ""
                                    self.llmBackend = config.llmBackend
                                    if (config.opencodeAvailable ?? true) == false,
                                       self.llmBackend == "opencode" {
                                        self.llmBackend = "litellm"
                                    }
                                    self.events.append(event)
                                case .conversationsList(let list):
                                    self.conversations = list
                                case .conversationLoaded(let id, let history):
                                    self.activeConversationId = id
                                    self.events = history
                                    self.isThinking = false
                                case .modelsList(let models):
                                    self.availableModels = models
                                case .userMessage:
                                    self.events.append(event)
                                case .approvalRequest(let req):
                                    self.events.append(event)
                                    self.pendingApproval = req
                                case .unknown, .usage, .configAck:
                                    break
                                }
                            } catch {
                                logger.warning("decode event failed error=\(error.localizedDescription, privacy: .public)")
                            }
                        }
                    default: break
                    }
                    self.receiveMessage()
                case .failure:
                    self.isConnected = false
                    logger.warning("receiveMessage failed and disconnected")
                }
            }
        }
    }

    func sendChat(text: String, model: String? = nil) {
        logger.info("sendChat text_len=\(text.count) model=\((model ?? "default"), privacy: .public)")
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
        isThinking = false
    }

    func approveRequest(_ req: ApprovalRequest, forSession: Bool) {
        var payload: [String: Any] = [
            "command": forSession ? "approve_session" : "approve",
            "request_id": req.id
        ]
        if forSession { payload["permission"] = req.permission }
        send(payload)
        pendingApproval = nil
    }

    func rejectRequest(_ req: ApprovalRequest) {
        send(["command": "reject", "request_id": req.id])
        pendingApproval = nil
        isThinking = false
    }

    func fetchModels() {
        send(["command": "list_models"])
    }

    func refreshState() {
        logger.debug("refreshState")
        send(["command": "get_config"])
        fetchModels()
    }

    func saveModel(_ name: String) {
        send(["command": "save_model", "name": name])
    }

    func setBackend(_ backend: String) {
        logger.info("setBackend backend=\(backend, privacy: .public)")
        availableModels = []
        selectedModel = ""
        llmBackend = backend
        send(["command": "set_config", "config": ["llm_backend": backend]])
    }

    func setSelectedModel(_ model: String) {
        let trimmedModel = model.trimmingCharacters(in: .whitespacesAndNewlines)
        logger.info("setSelectedModel model=\(trimmedModel, privacy: .public)")
        let command: [String: Any] = [
            "command": "set_config",
            "config": ["selected_model": trimmedModel]
        ]
        send(command)
        self.selectedModel = trimmedModel
    }

    func startNewChat() {
        logger.info("startNewChat")
        send(["command": "new_chat"])
        events = []
        activeConversationId = nil
    }

    func fetchConversations() {
        logger.debug("fetchConversations")
        send(["command": "list_conversations"])
    }

    func loadConversation(id: String) {
        logger.info("loadConversation id=\(id, privacy: .public)")
        send(["command": "load_conversation", "id": id])
    }

    func deleteConversation(id: String) {
        logger.info("deleteConversation id=\(id, privacy: .public)")
        send(["command": "delete_conversation", "id": id])
    }

    func openNote(path: String) {
        logger.info("openNote path=\(path, privacy: .public)")
        send(["command": "open_note", "path": path])
    }

    private func send(_ dict: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: dict),
              let string = String(data: data, encoding: .utf8) else { return }
        logger.debug("send payload_chars=\(string.count)")
        webSocketTask?.send(.string(string)) { error in
            if let error = error {
                logger.error("websocket send error=\(error.localizedDescription, privacy: .public)")
            }
        }
    }
}
