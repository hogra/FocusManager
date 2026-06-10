from PyQt6.QtWidgets import QVBoxLayout, QPushButton, QLabel, QListWidget, QDialog, QListWidgetItem
from customcalendar import *

def is_task_active_now(days_left):
    # Проверяет, доступна ли задача прямо сейчас, исходя из текущего времени
    current_hour = datetime.now().time().hour

    if days_left <= 1:
        return True
    elif days_left == 2:
        return current_hour < 23
    elif days_left == 3:
        return current_hour < 22
    elif days_left == 4:
        return current_hour < 21
    elif days_left == 5:
        return current_hour < 20
    return False

class PlansDialog(QDialog):
    def __init__(self, tasks, main_window, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Планы на сегодня")
        self.resize(600, 520)
        self.tasks = tasks
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.calendar = CustomCalendar()
        self.calendar.setGridVisible(True)
        self.calendar.update_task_formats(self.tasks)
        layout.addWidget(QLabel("Календарь дедлайнов:"))
        layout.addWidget(self.calendar)

        self.list_widget = QListWidget()
        layout.addWidget(QLabel("Активные дела на сегодня (шансы выпадения):"))
        layout.addWidget(self.list_widget)

        active_tasks = []
        total_weight = 0

        for task in self.tasks:
            days_left = get_working_days_left(task['deadline'])
            if days_left <= 5 and is_task_active_now(days_left):
                weight = 6 - days_left
                active_tasks.append((task, days_left, weight))
                total_weight += weight

        if not active_tasks:
            self.list_widget.addItem("😎 Нет доступных задач на сегодня. Отдыхайте!")
            has_tasks = False
        else:
            has_tasks = True
            active_tasks.sort(key=lambda x: x[1])

            for task, days_left, weight in active_tasks:
                prob = (weight / total_weight) * 100

                if days_left <= 1:
                    time_limit = "сегодня/завтра (до упора)"
                elif days_left == 2:
                    time_limit = "послезавтра (до 23:00)"
                elif days_left == 3:
                    time_limit = "3 дня (до 22:00)"
                elif days_left == 4:
                    time_limit = "4 дня (до 21:00)"
                elif days_left == 5:
                    time_limit = "5 дней (до 20:00)"

                item_text = f"[{task['deadline']}] {task['title']}\n" \
                            f"   Шанс: {prob:.1f}% | Ограничение: {time_limit}"

                item = QListWidgetItem(item_text)
                self.list_widget.addItem(item)

        self.btn_get_task = QPushButton("🎲 ПОЛУЧИТЬ СЛУЧАЙНУЮ ЗАДАЧУ")
        self.btn_get_task.setStyleSheet(
            "background-color: #2196F3; color: white; font-weight: bold; font-size: 14px; padding: 12px; border-radius: 5px;")
        self.btn_get_task.setEnabled(has_tasks)
        self.btn_get_task.clicked.connect(self.trigger_random_task)
        layout.addWidget(self.btn_get_task)

        self.setLayout(layout)

    def trigger_random_task(self):
        self.accept()
        self.main_window.get_random_task()