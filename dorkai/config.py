"""
config.py — единая точка настроек приложения.

Логика загрузки ключа (в порядке приоритета):
    1) переменная окружения DORKAI_API_KEY (задана ДО запуска программы);
    2) файл .env рядом с main.py (его создаёт кнопка «API-ключ» в GUI).

Безопасность: ключ никогда не «зашивается» в код — только окружение/.env.
"""

# Модуль для чтения переменных окружения процесса из стандартной библиотеки
import os

# sys нужен для определения режима запуска: обычный Python или «замороженный» exe (PyInstaller)
import sys

# Path — кроссплатформенная работа с путями (Windows/Linux/macOS без правок)
from pathlib import Path

# load_dotenv умеет взять пары «КЛЮЧ=значение» из файла .env и положить их в os.environ
from dotenv import load_dotenv

# Определяем корень проекта в зависимости от способа запуска.
# Если приложение собрано PyInstaller'ом (sys.frozen == True), файл __file__
# указывает во ВРЕМЕННУЮ папку распаковки (_MEI...), которая удаляется при выходе.
# Поэтому «свои» файлы (.env) ищем и создаём рядом с самим exe-файлом.
if getattr(sys, "frozen", False):
    # Режим exe: корень = папка, где лежит dorkAI.exe
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    # Обычный запуск из исходников: config.py лежит в dorkai/, поднимаемся на уровень выше
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Файл .env, где хранится API-ключ (рядом с main.py, удобно и не попадает в git)
ENV_FILE = PROJECT_ROOT / ".env"

# Подгружаем .env в переменные окружения.
# override=True значит: значения из файла имеют приоритет над уже существующими env,
# чтобы ключ, сохранённый через GUI, сразу «перекрыл» старый.
load_dotenv(ENV_FILE, override=True)


def _env_bool(name: str, default: bool) -> bool:
    # Вспомогательная функция: читает логическую переменную окружения («1/true/yes» = True)
    raw = os.getenv(name)  # берём строковое значение или None
    if raw is None:        # переменная не задана — возвращаем значение по умолчанию
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}  # «правдивые» строки


class Settings:
    """
    Объект настроек (паттерн Settings object):
    один экземпляр создаётся в main.py и передаётся во все слои приложения.
    """

    def __init__(self) -> None:
        # Выполняем первичное чтение всех настроек из окружения
        self._reload()

    def _reload(self) -> None:
        # Ключ API; по умолчанию пустая строка = «ключа нет»
        self.api_key: str = os.getenv("DORKAI_API_KEY", "").strip()
        # Базовый URL провайдера: любой OpenAI-совместимый сервис (Groq/OpenRouter/OpenAI...)
        self.base_url: str = os.getenv("DORKAI_BASE_URL", "https://api.groq.com/openai/v1").strip().rstrip("/")
        # Название модели генерации
        self.model: str = os.getenv("DORKAI_MODEL", "llama-3.3-70b-versatile").strip()
        # Таймаут одного HTTP-запроса в секундах (float — можно указать дробное значение)
        self.request_timeout: float = float(os.getenv("DORKAI_TIMEOUT", "30"))
        # Сколько дорков максимум просим у модели
        self.max_dorks: int = int(os.getenv("DORKAI_MAX_DORKS", "10"))
        # Просить ли провайдер о режиме строгого JSON (экономит токены и упрощает парсинг)
        self.json_mode: bool = _env_bool("DORKAI_JSON_MODE", True)

    @property
    def has_api_key(self) -> bool:
        # Свойство-«флаг»: есть ли непустой ключ
        return bool(self.api_key)

    def save_api_key(self, new_key: str) -> bool:
        """
        Сохраняет ключ в файл .env и мгновенно обновляет текущие настройки.

        Возвращает True при успехе, False при неудаче (например, нет прав на запись).
        Примечание: .env — простой локальный файл; для максимальной защиты в
        корпоративной среде рассмотрите пакет keyring (хранилище Windows).
        """
        # Убираем случайные пробелы вокруг ключа (частая ошибка при копировании)
        cleaned = new_key.strip()
        # Пустой ключ сохранять бессмысленно
        if not cleaned:
            return False
        try:
            # Будущие строки файла: начнём с содержимого существующего .env
            lines: list[str] = []
            if ENV_FILE.exists():
                # Читаем файл построчно (utf-8 — безопасно для любых комментариев)
                for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                    # Пропускаем старую строку с ключом — её заменит новая
                    if line.strip().startswith("DORKAI_API_KEY="):
                        continue
                    lines.append(line)
            # Добавляем актуальную строку с ключом
            lines.append(f"DORKAI_API_KEY={cleaned}")
            # Записываем файл целиком с завершающим переводом строки
            ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
            # Обновляем «живые» настройки, чтобы НЕ перезапускать приложение
            self.api_key = cleaned
            # Синхронизируем окружение процесса (если какой-то код читает os.getenv напрямую)
            os.environ["DORKAI_API_KEY"] = cleaned
            # Успех
            return True
        except OSError:
            # Проблемы диска/прав доступа — сообщаем наверх «мягким» False
            return False
