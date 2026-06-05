import sys
from mainwindow import *
from PyQt6.QtWidgets import QApplication



if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Настройка для работы трея (чтобы при скрытии главного окна приложение не закрывалось)
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())