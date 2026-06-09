import getpass
import psutil
from PyQt6.QtCore import QThread

class ProcessKillerThread(QThread):
    # Фоновый поток, который убивает программы не из белого списка

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.current_user = getpass.getuser()
        self.whitelist = []

    def set_whitelist(self, whitelist):
        self.whitelist = [name.lower() for name in whitelist]

    def run(self):
        self.is_running = True
        while self.is_running:
            for proc in psutil.process_iter(['name', 'username']):
                try:
                    # трогаем только процессы текущего пользователя. Это защитит от падения Windows/macOS
                    # из-за закрытия системных служб
                    proc_user = proc.info['username']
                    if proc_user and self.current_user in proc_user:
                        proc_name = proc.info['name'].lower()
                        if proc_name not in self.whitelist:
                            proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, TypeError):
                    pass
            self.sleep(2)  # Проверяем каждые 2 секунды

    def stop(self):
        self.is_running = False