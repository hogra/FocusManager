import json
import os
import random
from focuswindow import *
from processkillerthread import *
from PyQt6.QtWidgets import QMainWindow, QWidget, QLineEdit, QMessageBox, QSystemTrayIcon, QMenu, QApplication, QStyle
from PyQt6.QtGui import QAction
from whitelistdialog import *

TASKS_FILE = "data/tasks.json"
WHITELIST_FILE = "data/whitelist.json"

# Базовые системные процессы Windows 10/11, чтобы не пропадала панель задач
DEFAULT_WHITELIST = [
    "python.exe", "pythonw.exe", "explorer.exe", "cmd.exe",
    "pycharm64.exe", "code.exe", "idea64.exe",
    "chrome.exe", "msedge.exe", "firefox.exe",
    "shellexperiencehost.exe", "startmenuexperiencehost.exe",
    "searchapp.exe", "searchui.exe", "textinputhost.exe",
    "sihost.exe", "taskmgr.exe", "dwm.exe", "conhost.exe"
]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FocusManager")
        self.resize(700, 500)

        self.is_dark_theme = False

        self.whitelist = self.load_whitelist()
        self.tasks = self.load_tasks()

        self.killer_thread = ProcessKillerThread()
        self.killer_thread.set_whitelist(self.whitelist)

        self.focus_window = FocusWindow()

        self.focus_window.finished_signal.connect(self.end_focus_mode)
        self.focus_window.completed_signal.connect(self.complete_task)

        self.init_tray()
        self.init_menu()
        self.init_ui()
        self.apply_theme()
        self.update_task_list()

    def init_menu(self):
        menu_bar = self.menuBar()

        plans_menu = menu_bar.addMenu("Планы")

        action_show_plans = QAction("📋 Планы на сегодня", self)
        action_show_plans.triggered.connect(self.show_plans)
        plans_menu.addAction(action_show_plans)

        action_get_task = QAction("🎲 Получить случайную задачу", self)
        action_get_task.triggered.connect(self.get_random_task)
        plans_menu.addAction(action_get_task)

        settings_menu = menu_bar.addMenu("Настройки")

        action_whitelist = QAction("Редактор белого списка", self)
        action_whitelist.triggered.connect(self.open_whitelist_editor)
        settings_menu.addAction(action_whitelist)

        self.action_theme = QAction("Сменить тему (сейчас Светлая)", self)
        self.action_theme.triggered.connect(self.toggle_theme)
        settings_menu.addAction(self.action_theme)

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)

        tray_menu = QMenu()
        restore_action = QAction("Развернуть", self)
        restore_action.triggered.connect(self.showNormal)

        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(QApplication.instance().quit)

        tray_menu.addAction(restore_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Менеджер Фокуса",
            "Программа свернута в системный трей и продолжает следить за задачами.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def load_tasks(self):
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def load_whitelist(self):
        if os.path.exists(WHITELIST_FILE):
            with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return DEFAULT_WHITELIST

    def save_whitelist(self):
        os.makedirs(os.path.dirname(WHITELIST_FILE), exist_ok=True)
        with open(WHITELIST_FILE, "w", encoding="utf-8") as f:
            json.dump(self.whitelist, f, ensure_ascii=False, indent=4)
        self.killer_thread.set_whitelist(self.whitelist)

    def save_tasks(self):
        os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=4)

    def init_ui(self):
        central_widget = QWidget()
        main_layout = QHBoxLayout()

        left_panel = QVBoxLayout()
        self.calendar = CustomCalendar()
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
        # Подключаем клик по задаче для выделения дня в календаре
        self.task_list_widget.itemClicked.connect(self.on_task_clicked)

        right_panel.addWidget(QLabel("Все задачи:"))
        right_panel.addWidget(self.task_list_widget)

        btn_delete = QPushButton("Удалить выбранную")
        btn_delete.clicked.connect(self.delete_selected_task)
        right_panel.addWidget(btn_delete)

        self.btn_plans = QPushButton("📋 ПЛАНЫ НА СЕГОДНЯ")
        self.btn_plans.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; font-size: 14px; padding: 15px;")
        self.btn_plans.clicked.connect(self.show_plans)
        right_panel.addWidget(self.btn_plans)

        main_layout.addLayout(left_panel, 2)
        main_layout.addLayout(right_panel, 1)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def on_task_clicked(self, item):
        # Находим дату в квадратных скобках [YYYY-MM-DD] в начале строки
        text = item.text()
        if text.startswith("[") and "]" in text:
            date_str = text[1:text.find("]")]
            qdate = QDate.fromString(date_str, "yyyy-MM-dd")
            if qdate.isValid():
                self.calendar.setSelectedDate(qdate)

    def show_plans(self):
        dialog = PlansDialog(self.tasks, self, self)
        dialog.exec()

    def open_whitelist_editor(self):
        dialog = WhitelistDialog(self.whitelist, self)
        if dialog.exec():
            self.whitelist = dialog.get_whitelist()
            self.save_whitelist()

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        self.apply_theme()

    def apply_theme(self):
        app = QApplication.instance()
        theme_file = "styles/darktheme.сss" if self.is_dark_theme else "styles/lighttheme.сss"

        if os.path.exists(theme_file):
            with open(theme_file, "r", encoding="utf-8") as f:
                style_sheet = f.read()
                app.setStyleSheet(style_sheet)

        if self.is_dark_theme:
            self.action_theme.setText("Сменить тему (сейчас Темная)")
        else:
            self.action_theme.setText("Сменить тему (сейчас Светлая)")

    def update_task_list(self):
        self.task_list_widget.clear()
        self.tasks.sort(key=lambda x: x['deadline'])
        self.calendar.update_task_formats(self.tasks)  # Передаем задачи в календарь для покраски дат
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