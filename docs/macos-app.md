# macOS Application

The Dragonglass macOS app is a native Swift application that acts as the primary interface for the AI agent. It manages its own Python backend lifecycle, ensuring that the appropriate agent version and dependencies are available.

## Build Requirements

To build the macOS application from source, you need:
- **macOS**: 14.0 or newer.
- **Xcode**: 15.0 or newer.
- **Python**: 3.11 or newer (used during the build process to package the backend).
- **Package Manager**: Swift Package Manager (managed by Xcode).

## Backend Bundling Process

Dragonglass does not rely on a global Python environment at runtime. Instead, it bundles the entire Python backend and its dependencies directly into the application bundle.

### 1. Build Phase: Wheels Generation
During the Xcode build process, a "Run Script" build phase executes to prepare the backend:
- **Dependency Resolution**: It uses `pip wheel` to download and package all Python dependencies into the `DragonglassApp/Resources/wheels/` directory.
- **Package Bundling**: The `dragonglass` Python package itself is built into a wheel.
- **Metadata**: It generates two key metadata files in `DragonglassApp/Resources/`:
  - `version.txt`: The current version of the Dragonglass package.
  - `python_version.txt`: The major.minor version of Python used during the build phase.

### 2. Runtime: Virtual Environment Management
When the app starts, the `BackendManager` class orchestrates the following:
- **Version Check**: It compares the `version.txt` in the app bundle with the `installed_version.txt` in the user's Application Support directory.
- **Initialization**: If it's a new installation or an update:
  1. It creates a private virtual environment (venv) in `~/Library/Application Support/dragonglass/venv/`.
  2. It installs the bundled wheels into this venv using `pip install --no-index --find-links`. This ensures the app is fully functional even without an internet connection.
- **Execution**: The app launches the bundled Python backend by executing the `dragonglass serve` command from within the private venv.

## Core Swift Components

- **DragonglassApp.swift**: The main entry point for the SwiftUI application.
- **BackendManager.swift**: Handles the lifecycle, installation, and health monitoring of the Python subprocess.
- **AgentClient.swift**: Manages the WebSocket communication with the backend.
- **ConversationManagerView.swift**: The primary UI for browsing and interacting with chat history.
- **SettingsView.swift**: GUI for managing backend configuration (Ollama URL, model selection, etc).
