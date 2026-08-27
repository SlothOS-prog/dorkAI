"""
main.py — точка входа приложения dorkAI.

Запуск:
    python main.py          — графический интерфейс (по умолчанию);
    python main.py --cli    — консольный режим.

Порядок работы:
    1) создать Settings (читает переменные окружения и .env);
    2) выбрать оболочку (GUI или CLI);
    3) передать ей ядро генерации.
"""

# argv нужен, чтобы понять, в каком режиме запускать приложение
import sys

# Импортируем из нашего пакета ядро и оболочки
from dorkai.config import Settings
from dorkai.gui import run_gui
from dorkai.cli import run_console


def main() -> int:
    # Читаем настройки один раз — они передаются во все слои приложения
    settings = Settings()

    # Проверяем флаг командной строки --cli
    if "--cli" in sys.argv[1:]:
        # Консольный режим: REPL с вводом тем
        return run_console()

    # По умолчанию — графический режим
    try:
        # Запускаем GUI (mainloop внутри)
        run_gui(settings)
    except ImportError as exc:
        # tkinter отсутствует (некоторые «облегчённые» сборки Python) — поясняем
        print("Не найден tkinter (GUI). Установите полный Python или запустите: python main.py --cli")
        print(f"Подробности: {exc}")
        # Ненулевой код выхода — сигнал об ошибке
        return 1

    # Нормальное завершение
    return 0


# Стандартный guard: код ниже выполнится только при прямом запуске файла,
# но НЕ при импорте (защита от побочных эффектов)
if __name__ == "__main__":
    # Выходим с кодом, который вернула main()
    sys.exit(main())
