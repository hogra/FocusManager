import json
import os
import random
from focuswindow import *
from processkillerthread import *
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QMessageBox,
    QSystemTrayIcon, QMenu, QApplication, QStyle, QDialog, QListWidgetItem, QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from customcalendar import *

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

class WhitelistDialog(QDialog):
    def __init__(self, current_whitelist, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактор белого списка")
        self.resize(450, 500)
        self.current_whitelist = set(name.lower() for name in current_whitelist)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        lbl_info = QLabel("Выберите процессы, которые НЕ будут закрываться:\n(Отмеченные галочкой продолжат работать)")
        layout.addWidget(lbl_info)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        import psutil
        import getpass
        current_user = getpass.getuser()
        running_processes = set()
        for proc in psutil.process_iter(['name', 'username']):
            try:
                if proc.info['username'] and current_user in proc.info['username']:
                    running_processes.add(proc.info['name'].lower())
            except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
                pass

        all_processes = sorted(list(running_processes | self.current_whitelist))

        for proc_name in all_processes:
            item = QListWidgetItem(proc_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if proc_name in self.current_whitelist:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)

        btn_layout = QHBoxLayout()

        btn_add_manual = QPushButton("Добавить вручную")
        btn_add_manual.clicked.connect(self.add_manual)
        btn_layout.addWidget(btn_add_manual)

        btn_save = QPushButton("Сохранить")
        btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def add_manual(self):
        name, ok = QInputDialog.getText(self, "Добавить процесс", "Введите имя процесса (например, 'telegram.exe'):")
        if ok and name:
            name = name.strip().lower()
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).text() == name:
                    return
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.list_widget.insertItem(0, item)

    def get_whitelist(self):
        whitelist = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                whitelist.append(item.text())
        return whitelist


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
        self.init_ui()
        self.apply_theme()
        self.update_task_list()

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        # Устанавливаем стандартную иконку (чтобы не искать внешние файлы)
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
        # Двойной клик по иконке трея разворачивает окно
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()

    def closeEvent(self, event):
        # Перехватываем закрытие окна: игнорируем его и прячем окно в трей
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
        with open(WHITELIST_FILE, "w", encoding="utf-8") as f:
            json.dump(self.whitelist, f, ensure_ascii=False, indent=4)
        self.killer_thread.set_whitelist(self.whitelist)

    def save_tasks(self):
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

        self.btn_whitelist = QPushButton("⚙️ Настроить белый список")
        self.btn_whitelist.clicked.connect(self.open_whitelist_editor)
        right_panel.addWidget(self.btn_whitelist)

        self.btn_theme = QPushButton("☀️ Светлая тема")
        self.btn_theme.clicked.connect(self.toggle_theme)
        right_panel.addWidget(self.btn_theme)

        main_layout.addLayout(left_panel, 2)
        main_layout.addLayout(right_panel, 1)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

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
        with open(theme_file, "r", encoding="utf-8") as f:
            style_sheet = f.read()
            app.setStyleSheet(style_sheet)
        if self.is_dark_theme:
            self.btn_theme.setText("🌙 Темная тема")
        else:
            self.btn_theme.setText("☀️ Светлая тема")

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