from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal

class FocusWindow(QWidget):
    # Окно, которое висит поверх остальных во время работы
    finished_signal = pyqtSignal()
    completed_signal = pyqtSignal(str)  # Передает ID/имя задачи для удаления

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self.setWindowTitle("🔥 Режим фокуса")
        self.resize(300, 150)
        self.current_task = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.lbl_task = QLabel("Текущая задача: ...")
        self.lbl_task.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        self.lbl_task.setWordWrap(True)
        self.lbl_task.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_task)

        btn_layout = QHBoxLayout()

        self.btn_complete = QPushButton("Выполнить (Удалить)")
        self.btn_complete.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
        self.btn_complete.clicked.connect(self.on_complete)

        self.btn_finish = QPushButton("Закончить (Отложить)")
        self.btn_finish.setStyleSheet("background-color: #FF9800; color: white; padding: 10px;")
        self.btn_finish.clicked.connect(self.on_finish)

        btn_layout.addWidget(self.btn_complete)
        btn_layout.addWidget(self.btn_finish)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def set_task(self, task):
        self.current_task = task
        self.lbl_task.setText(f"🔥 В работе:\n{task['title']}")

    def on_complete(self):
        self.completed_signal.emit(self.current_task['title'])
        self.close()

    def on_finish(self):
        self.finished_signal.emit()
        self.close()