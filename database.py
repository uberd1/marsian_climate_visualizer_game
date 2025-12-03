import sqlite3

DATABASE_NAME = 'patterns.db'


def init_db():
    """Создает базу данных и таблицу, если их не существует."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        # Создаем таблицу для хранения паттернов
        # name - название паттерна
        # cells - координаты живых клеток в виде текста
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                cells TEXT NOT NULL
            )
        """)
        conn.commit()


def get_patterns():
    """Возвращает список всех паттернов (id, name) из базы данных."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM patterns ORDER BY name")
        return cursor.fetchall()


def get_pattern_cells(pattern_id):
    """Возвращает строку с клетками для указанного паттерна."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT cells FROM patterns WHERE id = ?", (pattern_id,))
        result = cursor.fetchone()
        return result[0] if result else None


def add_pattern(name, cells_set):
    """Добавляет новый паттерн в базу данных."""
    # Преобразуем множество клеток в строку вида "x1,y1;x2,y2;..."
    cells_str = ";".join([f"{col},{row}" for col, row in cells_set])

    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO patterns (name, cells) VALUES (?, ?)", (name, cells_str))
            conn.commit()
            return True, "Паттерн успешно сохранен."
        except sqlite3.IntegrityError:
            return False, "Паттерн с таким именем уже существует."


def delete_pattern(pattern_id):
    """Удаляет паттерн из базы данных по его ID."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM patterns WHERE id = ?", (pattern_id,))
        conn.commit()