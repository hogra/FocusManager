import json
import os
import random
from focuswindow import *
from processkillerthread import *
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QCalendarWidget, QListWidget, QMessageBox
)

TASKS_FILE = "tasks.json"


# Белый список процессов.
# Системные процессы защищены тем, что мы закрываем только процессы текущего пользователя.
WHITELIST = [
    "python.exe", "pythonw.exe", "explorer.exe", "cmd.exe",
    "pycharm64.exe", "code.exe", "idea64.exe",
    "chrome.exe", "msedge.exe", "firefox.exe"

]


# Логика календаря и времени
def get_working_days_left(deadline_str):
    # Считает оставшиеся дни до дедлайна, пропуская субботу и воскресенье
    today = datetime.now().date()
    try:
        deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    except ValueError:
        return 0

    if deadline_date <= today:
        return 0

    days_left = 0
    current_date = today
    while current_date < deadline_date:
        current_date += timedelta(days=1)
        if current_date.weekday() not in (5, 6):
            days_left += 1

    return days_left


def is_task_active_now(days_left):
    # Проверяет, доступна ли задача прямо сейчас, исходя из текущего времени
    current_hour = datetime.now().time().hour

    if days_left <= 1:
        return True
        return current_hour < 23
    elif days_left == 3:
        return current_hour < 22
    elif days_left == 4:
        return current_hour < 21
    elif days_left == 5:
        return current_hour < 20
    return False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Интерактивный Календарь-Менеджер")
        self.resize(700, 500)

        self.tasks = self.load_tasks()
        self.killer_thread = ProcessKillerThread()
        self.focus_window = FocusWindow()

        self.focus_window.finished_signal.connect(self.end_focus_mode)
        self.focus_window.completed_signal.connect(self.complete_task)

        self.init_ui()
        self.update_task_list()

    def load_tasks(self):
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_tasks(self):
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=4)

    def init_ui(self):
        central_widget = QWidget()
        main_layout = QHBoxLayout()

        left_panel = QVBoxLayout()
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        left_panel.addWidget(self.calendar)

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Введите новую задачу...")
        left_panel.addWidget(self.task_input)

        btn_add = QPushButton("Добавить задачу на выбранную дату")
        btn_add.clicked.connect(self.add_task)
        left_panel.addWidget(btn_add)

        right_panel = QVBoxLayout()
        self.task_list_widget = QListWidget()
        right_panel.addWidget(QLabel("Все задачи:"))
        right_panel.addWidget(self.task_list_widget)

        btn_delete = QPushButton("Удалить выбранную")
        btn_delete.clicked.connect(self.delete_selected_task)
        right_panel.addWidget(btn_delete)

        self.btn_random = QPushButton("🎲 ПОЛУЧИТЬ ЗАДАЧУ")
        self.btn_random.setStyleSheet(
            "background-color: #2196F3; color: white; font-weight: bold; font-size: 14px; padding: 15px;")
        self.btn_random.clicked.connect(self.get_random_task)
        right_panel.addWidget(self.btn_random)

        main_layout.addLayout(left_panel, 2)
        main_layout.addLayout(right_panel, 1)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def update_task_list(self):
        self.task_list_widget.clear()
        self.tasks.sort(key=lambda x: x['deadline'])
        for task in self.tasks:
            days_left = get_working_days_left(task['deadline'])
            status = f"Осталось дней: {days_left}" if days_left > 0 else "Горит (Сегодня/Просрочено)!"
            self.task_list_widget.addItem(f"[{task['deadline']}] {task['title']} ({status})")

    def add_task(self):
        title = self.task_input.text().strip()
        if not title:
            return

        selected_date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        self.tasks.append({"title": title, "deadline": selected_date})
        self.save_tasks()
        self.task_input.clear()
        self.update_task_list()

    def delete_selected_task(self):
        current_row = self.task_list_widget.currentRow()
        if current_row >= 0:
            del self.tasks[current_row]
            self.save_tasks()
            self.update_task_list()

    def get_random_task(self):
        active_tasks = []
        weights = []

        for task in self.tasks:
            days_left = get_working_days_left(task['deadline'])

            if days_left <= 5 and is_task_active_now(days_left):
                weight = 6 - days_left
                active_tasks.append(task)
                weights.append(weight)

        if not active_tasks:
            QMessageBox.information(self, "Отдых",
                                    "На сегодня (или на текущее время) доступных задач нет. Вы свободны!")
            return

        chosen_task = random.choices(active_tasks, weights=weights, k=1)[0]

        reply = QMessageBox.warning(
            self,
            "Внимание!",
            f"Вам выпала задача:\n\n«{chosen_task['title']}»\n\nВы сохранили все открытые документы? "
            f"После нажатия 'Да' закроются все сторонние программы!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.start_focus_mode(chosen_task)

    def start_focus_mode(self, task):
        self.hide()
        self.focus_window.set_task(task)
        self.focus_window.show()

        self.killer_thread.start()

    def end_focus_mode(self):
        # Возвращение из режима фокуса (отложил задачу)
        self.killer_thread.stop()
        self.killer_thread.wait()
        self.show()

    def complete_task(self, task_title):
        # Задача выполнена (удаляем из БД и выходим из фокуса)
        self.tasks = [t for t in self.tasks if t['title'] != task_title]
        self.save_tasks()
        self.update_task_list()
        self.end_focus_mode()
