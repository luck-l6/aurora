import sys
import os
import traceback
import faulthandler

log = open("crash.log", "w", encoding="utf-8")
faulthandler.enable(file=log)

import PyQt5
_pyqt5_dir = os.path.dirname(PyQt5.__file__)
_plugins_path = os.path.join(_pyqt5_dir, "Qt5", "plugins")
if os.path.isdir(_plugins_path):
    os.environ["QT_PLUGIN_PATH"] = _plugins_path
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(_plugins_path, "platforms")
_bin_path = os.path.join(_pyqt5_dir, "Qt5", "bin")
if os.path.isdir(_bin_path) and _bin_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _bin_path + os.pathsep + os.environ.get("PATH", "")

def main():
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QSharedMemory
    from PyQt5.QtGui import QFont

    _shared_mem = QSharedMemory("DesktopOrganizer_Lock_v300")
    if not _shared_mem.create(1):
        print("ERROR: Another instance running!")
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei", 10))

    from organizer import DesktopOrganizer
    window = DesktopOrganizer()
    window.show()

    ret = app.exec_()
    del window
    del app
    log.close()
    sys.exit(ret)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        traceback.print_exc(file=log)
        log.flush()
        input("Press Enter...")
