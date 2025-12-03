import sys
import random
from PyQt6.QtWidgets import QListWidget, QInputDialog, QTabWidget, QFileDialog, QMessageBox, QStyle, QLabel, \
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtGui import QPainter, QColor, QPen, QIcon, QAction, QPixmap
from PyQt6.QtCore import pyqtSignal, QTimer, QRectF, Qt
import database
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# --- Класс игрового поля ---
# Отвечает за всю логику, отрисовку и обработку пользовательского ввода.
class GridWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 500)

        # Для "бесконечного" поля используется множество (set) для хранения координат
        # только живых клеток в формате (колонка, ряд).
        self.live_cells = set()

        # Шаблон фигуры "Глайдер" в виде смещений (ряд, колонка).
        self.glider_pattern = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]

        # --- Система курсора ---
        self.cursor_pos = (0, 0)  # Текущие мировые координаты курсора (колонка, ряд).
        self.cursor_visible = True  # Флаг для организации мигания.

        # Отдельный таймер, который отвечает только за мигание курсора.
        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self._toggle_cursor_visibility)
        self.cursor_timer.start(500)  # Интервал мигания - 500 мс.

        # --- Система "Камеры" ---
        self.zoom = 10.0  # Масштаб (размер одной клетки в пикселях).
        self.offset_x = 0  # Смещение вида по горизонтали (панорамирование).
        self.offset_y = 0  # Смещение вида по вертикали.

        # --- Система перетаскивания поля ---
        self.panning = False  # Флаг, активен ли режим перетаскивания.
        self.last_mouse_pos = None  # Хранит последнюю позицию мыши при перетаскивании.

    def _toggle_cursor_visibility(self):
        """Инвертирует видимость курсора для создания эффекта мигания."""
        self.cursor_visible = not self.cursor_visible
        self.update()  # Запрашивает перерисовку для обновления вида курсора.

    def showEvent(self, event):
        """
        Этот метод вызывается один раз, когда виджет впервые отображается.
        Используется для коректной инициализации смещения камеры в центр экрана.
        """
        super().showEvent(event)
        if self.offset_x == 0 and self.offset_y == 0:
            self.offset_x = self.width() / 2
            self.offset_y = self.height() / 2

    def clear_grid(self):
        """Полностью очищает поле от живых клеток."""
        self.live_cells.clear()
        self.update()

    def screen_to_world(self, pos):
        """Преобразует экранные координаты (пиксели) в мировые (клетки)."""
        col = int((pos.x() - self.offset_x) / self.zoom)
        row = int((pos.y() - self.offset_y) / self.zoom)
        return col, row

    def count_neighbors(self, col, row):
        """Считает количество живых соседей для указанной клетки."""
        count = 0
        # dr (delta row) и dc (delta col) - смещения для проверки 8 соседей.
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0:
                    continue  # Пропускаем саму клетку.
                if (col + dc, row + dr) in self.live_cells:
                    count += 1
        return count

    def update_grid(self):
        """Вычисляет следующее поколение клеток по правилам игры 'Жизнь'."""
        # Собираем всех "кандидатов" - живые клетки и их непосредственных соседей.
        # Только эти клетки могут изменить свое состояние.
        candidates = set()
        for (col, row) in self.live_cells:
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    candidates.add((col + dc, row + dr))

        next_live_cells = set()
        # Проверяем каждого кандидата и решаем, будет ли он жив в след. поколении.
        for (col, row) in candidates:
            neighbors = self.count_neighbors(col, row)
            is_alive = (col, row) in self.live_cells

            if (is_alive and neighbors in (2, 3)) or (not is_alive and neighbors == 3):
                next_live_cells.add((col, row))

        self.live_cells = next_live_cells
        self.update()

    def keyPressEvent(self, event):
        """Обрабатывает нажатия клавиш для управления курсором и клетками."""
        col, row = self.cursor_pos

        # Движение курсора стрелками.
        if event.key() == Qt.Key.Key_Up:
            row -= 1
        elif event.key() == Qt.Key.Key_Down:
            row += 1
        elif event.key() == Qt.Key.Key_Left:
            col -= 1
        elif event.key() == Qt.Key.Key_Right:
            col += 1
        # Нажатие Enter инвертирует состояние клетки под курсором.
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.cursor_pos in self.live_cells:
                self.live_cells.remove(self.cursor_pos)
            else:
                self.live_cells.add(self.cursor_pos)

        self.cursor_pos = (col, row)
        self.cursor_visible = True  # Делаем курсор видимым после любого действия.
        self.cursor_timer.start(500)  # Перезапускаем таймер мигания.
        self.update()

    def mousePressEvent(self, event):
        """Обрабатывает нажатия кнопок мыши."""
        # Левая кнопка: перемещает курсор в указанную точку.
        if event.button() == Qt.MouseButton.LeftButton:
            self.cursor_pos = self.screen_to_world(event.position())
            self.cursor_visible = True
            self.cursor_timer.start(500)
            self.update()
        # Правая кнопка: активирует режим перетаскивания поля.
        elif event.button() == Qt.MouseButton.RightButton:
            self.panning = True
            self.last_mouse_pos = event.position()

    def mouseMoveEvent(self, event):
        """Обрабатывает движение мыши, если режим перетаскивания активен."""
        if self.panning:
            delta = event.position() - self.last_mouse_pos
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.last_mouse_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        """Отключает режим перетаскивания, когда правая кнопка отпущена."""
        if event.button() == Qt.MouseButton.RightButton:
            self.panning = False
            self.last_mouse_pos = None

    def wheelEvent(self, event):
        """Обрабатывает прокрутку колеса мыши для изменения масштаба."""
        old_zoom = self.zoom
        mouse_pos = event.position()

        # Вычисляем мировые координаты под курсором до изменения масштаба.
        world_before_zoom_x = (mouse_pos.x() - self.offset_x) / old_zoom
        world_before_zoom_y = (mouse_pos.y() - self.offset_y) / old_zoom

        # Изменяем масштаб.
        if event.angleDelta().y() > 0:
            self.zoom *= 1.2
        else:
            self.zoom /= 1.2
        self.zoom = max(1, min(self.zoom, 100))  # Ограничиваем масштаб.

        # Корректируем смещение, чтобы точка под курсором осталась на месте.
        self.offset_x = mouse_pos.x() - world_before_zoom_x * self.zoom
        self.offset_y = mouse_pos.y() - world_before_zoom_y * self.zoom
        self.update()

    def get_live_cells(self):
        """Возвращает множество всех живых клеток."""
        return self.live_cells

    def set_live_cells(self, cells):
        """Устанавливает новое состояние живых клеток и перерисовывает поле."""
        self.live_cells = cells
        self.update()

    def paintEvent(self, event):
        """Главный метод отрисовки. Вызывается каждый раз при self.update()."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("white"))  # Заливаем фон белым.

        # Вычисляем, какие мировые координаты (клетки) сейчас видны на экране.
        start_col = int(-self.offset_x / self.zoom);
        end_col = int((-self.offset_x + self.width()) / self.zoom) + 1
        start_row = int(-self.offset_y / self.zoom);
        end_row = int((-self.offset_y + self.height()) / self.zoom) + 1

        # Рисуем сетку, только если масштаб достаточно большой.
        if self.zoom > 4:
            pen = QPen(QColor("#dcdcdc"));
            pen.setWidth(1);
            painter.setPen(pen)
            for x in range(start_col, end_col): painter.drawLine(int(x * self.zoom + self.offset_x), 0,
                                                                 int(x * self.zoom + self.offset_x), self.height())
            for y in range(start_row, end_row): painter.drawLine(0, int(y * self.zoom + self.offset_y), self.width(),
                                                                 int(y * self.zoom + self.offset_y))

        # Рисуем все живые клетки, которые попадают в видимую область.
        painter.setBrush(QColor("black"));
        painter.setPen(Qt.PenStyle.NoPen)
        for (col, row) in self.live_cells:
            if start_col <= col < end_col and start_row <= row < end_row:
                painter.drawRect(
                    QRectF(col * self.zoom + self.offset_x, row * self.zoom + self.offset_y, self.zoom, self.zoom))

        # Рисуем мигающий курсор поверх всего остального.
        if self.cursor_visible:
            col, row = self.cursor_pos
            if start_col <= col < end_col and start_row <= row < end_row:
                pen = QPen(QColor("red"));
                pen.setWidth(2);
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)  # Прозрачная заливка.
                painter.drawRect(
                    QRectF(col * self.zoom + self.offset_x, row * self.zoom + self.offset_y, self.zoom, self.zoom))


class PatternLibraryWindow(QWidget):
    # Сигнал, который будет отправляться, когда пользователь выберет паттерн
    pattern_selected = pyqtSignal(set)

    def __init__(self, current_cells):
        super().__init__()
        self.setWindowTitle("Библиотека паттернов")
        self.setFixedSize(400, 500)
        self.current_cells = current_cells

        layout = QVBoxLayout(self)

        # Список для отображения паттернов
        self.pattern_list = QListWidget()
        self.pattern_list.itemDoubleClicked.connect(self.load_selected_pattern)

        # Кнопки управления
        load_button = QPushButton("Загрузить выбранный")
        load_button.clicked.connect(self.load_selected_pattern)

        save_button = QPushButton("Сохранить текущий паттерн")
        save_button.clicked.connect(self.save_current_pattern)

        delete_button = QPushButton("Удалить выбранный")
        delete_button.clicked.connect(self.delete_selected_pattern)

        layout.addWidget(QLabel("Доступные паттерны:"))
        layout.addWidget(self.pattern_list)
        layout.addWidget(load_button)
        layout.addWidget(save_button)
        layout.addWidget(delete_button)

        self.refresh_list()

    def refresh_list(self):
        """Обновляет список паттернов из базы данных."""
        self.pattern_list.clear()
        self.patterns_map = {}
        patterns = database.get_patterns()
        for pattern_id, name in patterns:
            self.pattern_list.addItem(name)
            self.patterns_map[name] = pattern_id

    def load_selected_pattern(self):
        """Загружает выбранный паттерн и отправляет его в главное окно."""
        selected_item = self.pattern_list.currentItem()
        if not selected_item:
            return

        pattern_id = self.patterns_map[selected_item.text()]
        cells_str = database.get_pattern_cells(pattern_id)

        new_cells = set()
        if cells_str:
            for part in cells_str.split(';'):
                col, row = map(int, part.split(','))
                new_cells.add((col, row))

        # Отправляем сигнал с загруженными клетками
        self.pattern_selected.emit(new_cells)
        self.close()  # Закрываем окно после загрузки

    def save_current_pattern(self):
        """Запрашивает имя и сохраняет текущий паттерн в БД."""
        name, ok = QInputDialog.getText(self, "Сохранить паттерн", "Введите имя паттерна:")
        if ok and name:
            success, message = database.add_pattern(name, self.current_cells)
            QMessageBox.information(self, "Результат", message)
            if success:
                self.refresh_list()

    def delete_selected_pattern(self):
        """Удаляет выбранный паттерн из БД."""
        selected_item = self.pattern_list.currentItem()
        if not selected_item:
            return

        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Вы уверены, что хотите удалить паттерн '{selected_item.text()}'?")

        if reply == QMessageBox.StandardButton.Yes:
            pattern_id = self.patterns_map[selected_item.text()]
            database.delete_pattern(pattern_id)
            self.refresh_list()


### --- Классс окна справки ---
class HelpWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Справка")
        self.setFixedSize(500, 400)

        # Главный layout для окна
        main_layout = QVBoxLayout(self)

        # Создаем систему вкладок
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Создаем и добавляем каждую вкладку
        self._create_controls_tab()
        self._create_rules_tab()
        self._create_about_tab()

    def _create_tab(self, content_widget):
        """Вспомогательная функция для создания страницы вкладки."""
        # Каждая вкладка - это отдельный виджет со своим layout
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(content_widget)
        return page

    def _create_controls_tab(self):
        """Создает вкладку с описанием управления."""
        label = QLabel()
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)

        text = """
        <h3>Управление</h3>
        <ul>
            <li><b>Левая кнопка мыши:</b> Переместить курсор в указанную точку.</li>
            <li><b>Правая кнопка мыши (зажать и двигать):</b> Перемещение (панорамирование) вида.</li>
            <li><b>Колесо мыши:</b> Масштабирование (зум).</li>
            <li><b>Клавиши-стрелки:</b> Перемещение курсора на одну клетку.</li>
            <li><b>Enter:</b> Создать или удалить живую клетку под курсором.</li>
            <li><b>End:</b> (Отладка) Заполнить видимую область случайными клетками.</li>
        </ul>
        """
        label.setText(text)

        controls_tab = self._create_tab(label)
        self.tabs.addTab(controls_tab, "Управление")

    def _create_rules_tab(self):
        """Создает вкладку с правилами игры."""
        label = QLabel()
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)

        text = """
        <h3>Правила игры «Жизнь»</h3>
        <p>
            Классический клеточный автомат, придуманный Джоном Конвеем.
            Эволюция живых клеток подчиняется трем простым правилам, что порождает
            сложное и непредсказуемое поведение системы.
        </p>
        <ol>
            <li><b>Выживание:</b> Живая клетка, у которой есть 2 или 3 живых соседа, выживает в следующем поколении.</li>
            <li><b>Смерть:</b> Живая клетка, у которой менее 2 (одиночество) или более 3 (перенаселение) живых соседей, умирает.</li>
            <li><b>Рождение:</b> Мёртвая клетка, у которой ровно 3 живых соседа, становится живой в следующем поколении.</li>
        </ol>
        """
        label.setText(text)

        rules_tab = self._create_tab(label)
        self.tabs.addTab(rules_tab, "Правила")

    def _create_about_tab(self):
        """Создает вкладку 'О программе' с иконкой и текстом."""
        # Создаем виджет-контейнер для этой вкладки
        about_page = QWidget()
        layout = QVBoxLayout(about_page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Центрируем все содержимое

        # --- Добавляем иконку (использование картинок) ---
        icon_label = QLabel()
        # Загружаем иконку из файла icon.ico
        icon_path = os.path.join(BASE_DIR, "icon.ico")
        pixmap = QPixmap(icon_path)
        # Масштабируем иконку до адекватного размера
        icon_label.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- Добавляем текст ---
        text_label = QLabel()
        text_label.setTextFormat(Qt.TextFormat.RichText)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setText("<h3>Игра «Жизнь»</h3><p>Версия 1.0<br>Автор: uberd1</p>")

        # Добавляем виджеты в layout
        layout.addWidget(icon_label)
        layout.addWidget(text_label)

        self.tabs.addTab(about_page, "О программе")


# --- Класс главного окна ---
# Отвечает за создание окна, кнопок и компоновку элементов.
class GameOfLifeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.help_win = None
        self.library_win = None
        icon_path = os.path.join(BASE_DIR, "icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle("Game of Life")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.grid_widget = GridWidget()
        # Разрешаем виджету отслеживать нажатия клавиш.
        self.grid_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        main_layout.addWidget(self.grid_widget)

        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)

        # Создание и подключение кнопок управления.
        start_button = QPushButton("Start");
        start_button.clicked.connect(self.start_game)
        stop_button = QPushButton("Stop");
        stop_button.clicked.connect(self.stop_game)
        reset_glider_button = QPushButton("Reset & Center Glider")
        reset_glider_button.clicked.connect(self.reset_glider)
        clear_button = QPushButton("Clear");
        clear_button.clicked.connect(self.clear)

        button_layout.addWidget(start_button)
        button_layout.addWidget(stop_button)
        button_layout.addWidget(reset_glider_button)
        button_layout.addWidget(clear_button)

        # Главный таймер, отвечающий за симуляцию.
        self.timer = QTimer();
        self.timer.timeout.connect(self.grid_widget.update_grid)

        # Главное меню игры
        self._create_menu_bar()

    def _create_menu_bar(self):
        """Создает и настраивает строку меню."""
        menu_bar = self.menuBar()

        # МЕНЮ "ФАЙЛ"
        file_menu = menu_bar.addMenu("&Файл")

        # Действие "Сохранить"
        save_action = QAction("Сохранить паттерн...", self)
        save_action.triggered.connect(self.save_pattern)
        file_menu.addAction(save_action)

        # Действие "Загрузить"
        load_action = QAction("Загрузить паттерн...", self)
        load_action.triggered.connect(self.load_pattern)
        file_menu.addAction(load_action)

        # МЕНЮ "ПОМОЩЬ"
        help_icon = self.style().standardIcon(getattr(QStyle.StandardPixmap, "SP_MessageBoxQuestion"))
        help_action = QAction(help_icon, "Справка", self)
        help_action.triggered.connect(self.show_help_window)
        help_menu = menu_bar.addMenu("&Помощь")
        help_menu.addAction(help_action)

        # Библиотекарь sqlite
        library_action = QAction("Библиотека паттернов...", self)
        library_action.triggered.connect(self.show_pattern_library)
        file_menu.addAction(library_action)

        file_menu.addSeparator()

    def show_help_window(self):
        """Создает и показывает окно справки."""
        # Проверяем, не открыто ли уже окно
        if self.help_win is None:
            self.help_win = HelpWindow()

        self.help_win.show()

    def save_pattern(self):
        """
        Открывает диалог сохранения файла и записывает в него
        координаты живых клеток.
        """
        self.stop_game()  # Останавливаем симуляцию перед сохранением

        # Открываем стандартный диалог сохранения
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить паттерн",
            "",  # Начальная директория (пусто = по умолчанию)
            "Pattern Files (*.txt);;All Files (*)"  # Фильтры файлов
        )

        # Если пользователь выбрал файл (не нажал "Отмена")
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    # Получаем клетки от виджета
                    live_cells = self.grid_widget.get_live_cells()
                    # Записываем каждую координату (col, row) в новую строку
                    for col, row in live_cells:
                        f.write(f"{col},{row}\n")
            except Exception as e:
                # Показываем сообщение об ошибке, если что-то пошло не так
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")

    def load_pattern(self):
        """
        Открывает диалог загрузки файла и считывает из него
        координаты живых клеток.
        """
        self.stop_game()  # Останавливаем симуляцию

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить паттерн",
            "",
            "Pattern Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                new_live_cells = set()
                with open(file_path, 'r') as f:
                    for line in f:
                        # Убираем лишние пробелы и пустые строки
                        line = line.strip()
                        if not line:
                            continue
                        # Разделяем строку "col,row" на две части
                        parts = line.split(',')
                        col = int(parts[0])
                        row = int(parts[1])
                        new_live_cells.add((col, row))

                # Передаем новые клетки в виджет
                self.grid_widget.set_live_cells(new_live_cells)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл:\n{e}")

    def show_pattern_library(self):
        """Открывает окно библиотеки паттернов."""
        self.stop_game()
        # Передаем текущие клетки, чтобы их можно было сохранить
        current_cells = self.grid_widget.get_live_cells()
        self.library_win = PatternLibraryWindow(current_cells)
        # Подключаемся к сигналу, который вернет выбранный паттерн
        self.library_win.pattern_selected.connect(self.load_pattern_from_db)
        self.library_win.show()

    def load_pattern_from_db(self, cells):
        """Слот, который принимает клетки от окна библиотеки и загружает их."""
        self.grid_widget.set_live_cells(cells)

    def reset_and_center_glider(self):
        self.stop_game()
        self.grid_widget.clear_grid()
        self.grid_widget.zoom = 10.0
        self.grid_widget.offset_x = self.grid_widget.width() / 2
        self.grid_widget.offset_y = self.grid_widget.height() / 2

        for dr, dc in self.grid_widget.glider_pattern:
            self.grid_widget.live_cells.add((0 + dc, 0 + dr))
        self.grid_widget.update()

    def start_game(self):
        self.timer.start(100)

    def stop_game(self):
        self.timer.stop()

    def reset_glider(self):
        self.stop_game()
        self.reset_and_center_glider()

    def clear(self):
        """
        Останавливает игру и запрашивает у пользователя подтверждение
        перед тем, как дать виджету команду на очистку.
        """
        self.stop_game()

        # Создаем диалоговое окно с вопросом
        reply = QMessageBox.question(
            self,
            'Подтверждение очистки',
            'Вы уверены, что хотите очистить все поле?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        # Проверяем ответ и даем команду виджету
        if reply == QMessageBox.StandardButton.Yes:
            self.grid_widget.clear_grid()


# --- Точка входа в приложение ---
if __name__ == "__main__":
    database.init_db()
    app = QApplication(sys.argv)
    window = GameOfLifeWindow()
    window.show()
    sys.exit(app.exec())
