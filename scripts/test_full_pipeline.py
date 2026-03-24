from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import traceback
from pathlib import Path

from dragonglass.agent.agent import VaultAgent
from dragonglass.agent.types import StatusEvent, TextChunk
from dragonglass.config import get_settings
from dragonglass.paths import OPENCODE_CONFIG_FILE

REPO_ROOT = Path(__file__).parent.parent
logger = logging.getLogger(__name__)


async def is_port_in_use(port: int) -> bool:
    try:
        _, writer = await asyncio.open_connection("127.0.0.1", port)
    except (ConnectionRefusedError, OSError):
        return False
    else:
        writer.close()
        await writer.wait_closed()
        return True


def force_update_opencode_json(opencode_json_path: Path, mcp_port: int) -> None:
    config = {}
    # Try to load from global config first to get providers etc.
    global_config_path = Path.home() / ".config" / "opencode" / "opencode.json"
    if global_config_path.exists():
        try:
            with open(global_config_path, encoding="utf-8") as f:
                config = json.load(f)
            print(f"Loaded global config from {global_config_path}")
        except Exception as e:
            print(f"Warning: Failed to load global config: {e}")

    # Fallback to local if still empty
    if not config and opencode_json_path.exists():
        try:
            with open(opencode_json_path, encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass

    # Update MCP
    if "mcp" not in config:
        config["mcp"] = {}
    config["mcp"]["dragonglass"] = {
        "type": "remote",
        "url": f"http://127.0.0.1:{mcp_port}/mcp",
        "enabled": True,
    }

    # Update Agent
    if "agent" not in config:
        config["agent"] = {}
    config["agent"]["dragonglass"] = {
        "model": "github-copilot/gpt-5-mini",
        "mode": "primary",
        "tools": {
            "dragonglass_*": True,
        },
    }

    with open(opencode_json_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"Updated {opencode_json_path} (merged with global config if found)")


async def run_full_pipeline_test() -> None:  # noqa: PLR0912, PLR0915
    # Use fixed ports to avoid confusion during debugging
    dragonglass_port = 51365
    mcp_port = 51366
    opencode_port = 4096

    print(
        f"[0] Ports: Dragonglass={dragonglass_port}, MCP={mcp_port}, OpenCode={opencode_port}"
    )

    if await is_port_in_use(dragonglass_port):
        print(
            f"ERROR: Port {dragonglass_port} is already in use. Please kill any existing Dragonglass server."
        )

    # Force cleanup of any stale opencode
    os.system("pkill -f 'opencode serve' 2>/dev/stdout || true")

    env = os.environ.copy()
    env["DRAGONGLASS_MCP_HTTP_PORT"] = str(mcp_port)
    env["DRAGONGLASS_SPAWN_OPENCODE"] = "false"
    env["DRAGONGLASS_LLM_BACKEND"] = "opencode"
    env["DRAGONGLASS_LLM_MODEL"] = "github-copilot/gpt-5-mini"
    env["DRAGONGLASS_OPENCODE_URL"] = f"http://127.0.0.1:{opencode_port}"
    env["OPENCODE_CONFIG"] = str(OPENCODE_CONFIG_FILE)

    force_update_opencode_json(OPENCODE_CONFIG_FILE, mcp_port)

    server_proc = None
    opencode_proc = None
    agent = None

    try:
        # 1. Start Main Dragonglass Server
        print(f"[1] Starting Main Dragonglass Server on port {dragonglass_port}...")
        server_proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "dragonglass.server.server",
            "--port",
            str(dragonglass_port),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        print("Wait for server to boot...")
        await asyncio.sleep(5)

        # 2. Start OpenCode server
        print(
            f"[2] Starting OpenCode server on port {opencode_port} with DEBUG logs..."
        )
        opencode_proc = await asyncio.create_subprocess_exec(
            "opencode",
            "serve",
            "--port",
            str(opencode_port),
            "--print-logs",
            "--log-level",
            "DEBUG",
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        async def stream_output(label: str, stream: asyncio.StreamReader) -> None:
            while True:
                line = await stream.readline()
                if not line:
                    break
                print(f"[{label}] {line.decode().strip()}")

        if server_proc.stdout and opencode_proc.stdout:
            # Store tasks to avoid garbage collection
            server_task = asyncio.create_task(
                stream_output("SERVER-OUT", server_proc.stdout)
            )
            opencode_task = asyncio.create_task(
                stream_output("OPENCODE-OUT", opencode_proc.stdout)
            )
            _ = (server_task, opencode_task)

        print("Wait for OpenCode to boot...")
        await asyncio.sleep(8)

        # 3. Run Agent Turn
        print("[3] Running agent turn...", flush=True)
        settings = get_settings()
        # Override settings for the test run
        settings.llm_backend = "opencode"
        settings.opencode_url = f"http://127.0.0.1:{opencode_port}"
        # Use gpt-5-mini as requested
        test_model = "github-copilot/gpt-5-mini"
        settings.llm_model = test_model
        settings.selected_model = test_model

        agent = VaultAgent(settings)
        await agent.initialise()

        user_query = "When is Michael's birthday."
        print(f"\nUser: '{user_query}'\n", flush=True)

        found_answer = False
        print("Agent: ", end="", flush=True)
        async for event in agent.run(
            user_query,
            model_override=test_model,
        ):
            if isinstance(event, TextChunk):
                text = event.text
                print(text, end="", flush=True)
                if "October 14" in text or "1988" in text:
                    found_answer = True
            elif isinstance(event, StatusEvent):
                # Print status updates on a new line to avoid interfering with stream
                print(f"\n[Status] {event.message}", flush=True)
                print("Agent: ", end="", flush=True)

        print("\n")
        if found_answer:
            print("[SUCCESS] Agent found the birthday!", flush=True)
        else:
            print("[FAILURE] Agent did not find the birthday.", flush=True)

    except Exception as e:
        print(f"Error during pipeline test: {e}", flush=True)
        traceback.print_exc()
    finally:
        print("[5] Cleaning up...", flush=True)
        if agent:
            await agent.close()

        if opencode_proc:
            print("Terminating OpenCode server...", flush=True)
            try:
                opencode_proc.terminate()
                await opencode_proc.wait()
            except Exception:
                pass

        if server_proc:
            print("Terminating Dragonglass server...", flush=True)
            try:
                server_proc.terminate()
                await server_proc.wait()
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(run_full_pipeline_test())
