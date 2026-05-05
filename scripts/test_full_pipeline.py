from __future__ import annotations

import asyncio
import os
import sys
import traceback
from pathlib import Path

from dragonglass.agent import VaultAgent
from dragonglass.agent.types import StatusEvent, TextChunk
from dragonglass.config import get_settings

REPO_ROOT = Path(__file__).parent.parent


async def is_port_in_use(port: int) -> bool:
    try:
        _, writer = await asyncio.open_connection("127.0.0.1", port)
    except (ConnectionRefusedError, OSError):
        return False
    else:
        writer.close()
        await writer.wait_closed()
        return True


async def run_full_pipeline_test() -> None:  # noqa: PLR0912, PLR0915
    dragonglass_port = 51365
    mcp_port = 51366

    print(f"[0] Ports: Dragonglass={dragonglass_port}, MCP={mcp_port}")

    if await is_port_in_use(dragonglass_port):
        print(f"ERROR: Port {dragonglass_port} is already in use.")

    env = os.environ.copy()
    env["MCP_HTTP_PORT"] = str(mcp_port)

    server_proc = None
    agent = None

    try:
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

        async def stream_output(label: str, stream: asyncio.StreamReader) -> None:
            while True:
                line = await stream.readline()
                if not line:
                    break
                print(f"[{label}] {line.decode().strip()}")

        if server_proc.stdout:
            server_task = asyncio.create_task(
                stream_output("SERVER-OUT", server_proc.stdout)
            )
            _ = (server_task,)

        print(f"Wait for MCP server on port {mcp_port}...")
        for _ in range(20):
            if await is_port_in_use(mcp_port):
                print(f"MCP server up on port {mcp_port}")
                break
            await asyncio.sleep(1)
        else:
            print(f"ERROR: MCP server did not start on port {mcp_port}")

        print("[2] Running agent turn...", flush=True)
        settings = get_settings()
        test_model = "gpt-4o-mini"
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
        print("[3] Cleaning up...", flush=True)
        if agent:
            await agent.close()

        if server_proc:
            print("Terminating Dragonglass server...", flush=True)
            try:
                server_proc.terminate()
                await server_proc.wait()
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(run_full_pipeline_test())
