import Foundation
import Combine

enum AgentEvent: Decodable {
    case status(String)
    case text(String)
    case error(String, String)
    case done
    case fileAccess(String, String)
    case config(DragonglassConfig)
    case configAck
    case modelsList([String])
    case usage(Int, Int, Int, Int)
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
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .type)

        switch type {
        case "StatusEvent":
            self = .status(try container.decode(String.self, forKey: .message))
        case "TextChunk":
            self = .text(try container.decode(String.self, forKey: .text))
        case "ToolErrorEvent":
            self = .error(try container.decode(String.self, forKey: .tool), try container.decode(String.self, forKey: .error))
        case "DoneEvent":
            self = .done
        case "FileAccessEvent":
            self = .fileAccess(try container.decode(String.self, forKey: .path), try container.decode(String.self, forKey: .operation))
        case "config":
            self = .config(try DragonglassConfig(from: decoder))
        case "config_ack":
            self = .configAck
        case "models_list":
            self = .modelsList(try container.decode([String].self, forKey: .models))
        case "UsageEvent":
            self = .usage(
                try container.decode(Int.self, forKey: .promptTokens),
                try container.decode(Int.self, forKey: .completionTokens),
                try container.decode(Int.self, forKey: .totalTokens),
                try container.decode(Int.self, forKey: .sessionTotal)
            )
        default:
            self = .unknown(type)
        }
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
                                self.events.append(event)
                                switch event {
                                case .modelsList(let models):
                                    self.availableModels = models
                                case .config(let config):
                                    self.extraModels = config.extraModels ?? []
                                    self.selectedModel = config.selectedModel ?? ""
                                case .done, .error:
                                    self.isThinking = false
                                default:
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
