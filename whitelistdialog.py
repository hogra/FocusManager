from PyQt6.QtWidgets import QHBoxLayout, QInputDialog
from PyQt6.QtCore import Qt
from plansdialog import *


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