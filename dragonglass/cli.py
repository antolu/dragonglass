from __future__ import annotations

import dotenv

from dragonglass.log import redirect_stderr, setup_logging
from dragonglass.tui.app import DragonglassApp


def main() -> None:
    dotenv.load_dotenv()
    setup_logging()
    redirect_stderr()
    DragonglassApp().run()
