import os
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MusicalTrainerWindow


def main() -> None:
    lang = os.environ.get("MEDIAHUB_APP_LANG", "es")
    for arg in sys.argv[1:]:
        if arg.startswith("--lang="):
            lang = arg.split("=", 1)[1].strip() or "es"

    app = QApplication(sys.argv)
    window = MusicalTrainerWindow(lang=lang)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
