"""
cli.py — консольная оболочка (демонстрация того, что бэкенд не зависит от GUI).

Запуск:  python main.py --cli
"""

# Выход по Ctrl+C/Q — нужен sys.exit
import sys

# Доменные импорты ядра
from .config import Settings
from .dork_generator import DorkGenerator
from .exceptions import DorkAIError

# Цвета ANSI для минимального «престижного» оформления терминала
_C_RESET = "\033[0m"   # сброс цвета
_C_DIM = "\033[2m"     # приглушённый серый — второстепенный текст
_C_CYAN = "\033[36m"   # циан — акценты и заголовки
_C_GREEN = "\033[32m"  # зелёный — сами дорки


def _print_result(result) -> None:
    # Красиво печатаем GenerationResult в консоль
    print()
    print(f"{_C_CYAN}Тема:{_C_RESET} {result.source_query}")
    print(f"{_C_DIM}Найдено дорков: {len(result.dorks)} | время: {result.elapsed_seconds}s{_C_RESET}")
    print("-" * 60)
    for i, dork in enumerate(result.dorks, start=1):
        # Номер и название техники
        print(f"{_C_CYAN}{i:>2}. {dork.title}{_C_RESET}")
        # Сам дорк зелёным — его копируют в Google
        print(f"    {_C_GREEN}{dork.query}{_C_RESET}")
        # Пояснение серым (если есть)
        if dork.description:
            print(f"    {_C_DIM}{dork.description}{_C_RESET}")
        # Пустая строка-разделитель между дорками
        print()


def run_console() -> int:
    """
    Главный цикл консольного режима.

    Returns:
        Код выхода для main() (0 = норма).
    """
    # Баннер приложения
    print(f"dorkAI {_C_DIM}(консольный режим){_C_RESET} — Google Dorks через ИИ")

    # Создаём настройки (читает окружение/.env один раз)
    settings = Settings()

    # Если ключа нет — предлагаем вставить его прямо сейчас (одним вводом)
    if not settings.has_api_key:
        print(f"{_C_DIM}API-ключ не найден (env DORKAI_API_KEY или файл .env).{_C_RESET}")
        # Единственный input в цикле до генерации — вставили и забыли
        key = input("Вставьте API-ключ и нажмите Enter: ").strip()
        if not settings.save_api_key(key):
            # Сохранить не удалось (права диска) — выходим с ошибкой
            print("Не удалось сохранить ключ в .env")
            return 1
        # Подтверждаем успех
        print("Ключ сохранён в .env\n")

    # Создаём сервис генерации поверх настроек
    generator = DorkGenerator(settings)

    try:
        # Основной REPL: читаем тему -> печатаем дорки
        while True:
            try:
                # Приглашение ввода
                query = input("\nТема исследования (q — выход): ").strip()
            except EOFError:
                # stdin закрылся — аккуратно завершаемся
                break
            # Команда выхода
            if query.lower() in {"q", "quit", "exit"}:
                break
            # Пустой ввод — просто переспрашиваем
            if not query:
                continue
            try:
                # Полный путь через ядро: запрос -> AI -> JSON -> объекты Dork
                result = generator.generate(query)
                # Печатаем результат
                _print_result(result)
            except DorkAIError as exc:
                # Любая доменная ошибка показывается без стектрейса — понятно пользователю
                print(f"Ошибка: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        # Ctrl+C — мягкий выход
        pass
    finally:
        # В любом случае освобождаем HTTP-ресурсы
        generator.close()

    # Успешное завершение
    return 0
