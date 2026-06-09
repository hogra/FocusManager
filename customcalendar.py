from PyQt6.QtWidgets import QCalendarWidget
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QTextCharFormat, QColor, QPen
from datetime import datetime, timedelta

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

class CustomCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.formatted_dates = []

    def update_task_formats(self, tasks):
        # Очищаем старые форматы
        default_format = QTextCharFormat()
        for d in self.formatted_dates:
            self.setDateTextFormat(d, default_format)
        self.formatted_dates.clear()

        # для каждой даты ищем минимальный остаток дней
        tasks_dict = {}
        for task in tasks:
            date_str = task['deadline']
            days_left = get_working_days_left(date_str)
            if date_str not in tasks_dict or days_left < tasks_dict[date_str]:
                tasks_dict[date_str] = days_left

        for date_str, days_left in tasks_dict.items():
            qdate = QDate.fromString(date_str, "yyyy-MM-dd")
            fmt = QTextCharFormat()
            if days_left <= 2:
                fmt.setBackground(QColor(255, 100, 100, 150))
            elif days_left <= 5:
                fmt.setBackground(QColor(255, 200, 0, 150))
            else:
                fmt.setBackground(QColor(100, 255, 100, 150))

            self.setDateTextFormat(qdate, fmt)
            self.formatted_dates.append(qdate)

    def paintCell(self, painter, rect, date):
        painter.save()
        qdate_current = QDate.currentDate()
        is_past = date < qdate_current
        is_today = date == qdate_current

        if is_past:
            painter.setOpacity(0.4)

        super().paintCell(painter, rect, date)

        if is_today:
            pen = QPen(QColor(0, 150, 255))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(rect.adjusted(1, 1, -2, -2))

        painter.restore()
