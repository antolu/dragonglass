from __future__ import annotations

import dotenv

from dragonglass.tui.app import DragonglassApp


def main() -> None:
    dotenv.load_dotenv()
    DragonglassApp().run()
