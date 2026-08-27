"""
dork_generator.py — сервисный слой: превращает текст пользователя в список Dork.

Поток данных:
    user_query (str)
        -> DorkAIClient.chat()            (HTTP, промпт из prompts.py)
        -> сырой текст ответа модели
        -> _parse()                        (извлечение и валидация JSON)
        -> GenerationResult(dorks=...)

Классы-данные (dataclass) дают бесплатный __init__/__repr__ и читаемость.
"""

# json — разбор ответа модели в словари/списки Python
import json

# re — регулярок для срезания markdown-забора ```json ... ```
import re

# perf_counter — точный таймер для замера времени генерации
from time import perf_counter

# dataclass — декларативные структуры данных без ручных конструкторов
from dataclasses import dataclass

# Доменные импорты проекта
from .ai_client import DorkAIClient
from .config import Settings
from .exceptions import EmptyQueryError, ResponseParsingError
from .prompts import build_system_prompt

# Регулярка: захватывает содержимое между ```json ... ``` или ``` ... ``` (флаг DOTALL
# позволяет точке совпадать с переносами строк; IGNORECASE — с ```JSON).
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


# --- Структуры данных -------------------------------------------------------

@dataclass(frozen=True)
class Dork:
    """Один Google Dork, сгенерированный ИИ (неизменяемый «снимок» данных)."""

    # Короткое человекочитаемое название техники
    title: str
    # Сам запрос-дорк, готовый для вставки в google.com
    query: str
    # Пояснение, что найдёт дорк (может быть пустым)
    description: str = ""

    def is_valid(self) -> bool:
        # Минимальная валидация: и название, и сам запрос обязаны быть непустыми
        return bool(self.title.strip()) and bool(self.query.strip())


@dataclass(frozen=True)
class GenerationResult:
    """Итог одной генерации: исходный запрос + список дорков + время работы."""

    # Что ввёл пользователь (очищенная строка)
    source_query: str
    # Кортеж (не список) — защита от случайного изменения после создания
    dorks: tuple[Dork, ...]
    # Сколько секунд занял полный цикл (округлено до сотых)
    elapsed_seconds: float


# --- Сервис ------------------------------------------------------------------

class DorkGenerator:
    """
    Фасад всего бэкенда: один метод generate(user_query) -> GenerationResult.

    Интерфейсы (GUI/CLI) знают ТОЛЬКО этот класс — можно менять «внутренности»
    (провайдера, промпт, парсинг), не трогая интерфейсы.
    """

    def __init__(self, settings: Settings) -> None:
        # Храним настройки (нужны для лимита дорков в промпте)
        self._settings = settings
        # Создаём HTTP-клиент один раз и переиспользуем для всех запросов
        self._client = DorkAIClient(settings)

    def generate(self, user_query: str) -> GenerationResult:
        """
        Полный цикл генерации дорков.

        Raises:
            EmptyQueryError:      строка запроса пуста.
            MissingApiKeyError:   нет ключа.
            AiClientError:        сетевые/HTTP проблемы.
            ResponseParsingError: модель вернула не тот формат.
        """
        # Нормализуем ввод: срезаем пробелы и переводы строк по краям
        clean_query = (user_query or "").strip()
        # Пустой запрос — это ошибка валидации, а не повод тратить токены
        if not clean_query:
            raise EmptyQueryError("Введите тему для генерации дорков.")

        # Засекаем время старта (perf_counter точнее time.time)
        started = perf_counter()

        # Строим системный промпт с актуальным лимитом дорков из настроек
        system_prompt = build_system_prompt(self._settings.max_dorks)

        # Отправляем запрос провайдеру (внутри — ретраи и таймауты)
        raw_text = self._client.chat(system_prompt, clean_query)

        # Разбираем сырой текст в список словарей с валидацией
        items = self._parse(raw_text)

        # Преобразуем каждый словарь в объект Dork
        dorks: list[Dork] = []
        for item in items:
            # Извлекаем поля с «безопасным» значением по умолчанию
            dork = Dork(
                title=str(item.get("title", "")).strip(),
                query=str(item.get("query", "")).strip(),
                description=str(item.get("description", "")).strip(),
            )
            # Битые записи (без query/title) молча отбрасываем
            if dork.is_valid():
                dorks.append(dork)

        # Модель могла проигнорировать лимит — принудительно обрезаем список
        dorks = dorks[: self._settings.max_dorks]

        # Если после валидации ничего не осталось — честно сообщаем об ошибке
        if not dorks:
            raise ResponseParsingError("ИИ не вернул ни одного корректного дорка.")

        # Считаем прошедшее время
        elapsed = round(perf_counter() - started, 2)

        # Возвращаем неизменяемый результат
        return GenerationResult(
            source_query=clean_query,
            dorks=tuple(dorks),
            elapsed_seconds=elapsed,
        )

    # --- Разбор ответа модели -----------------------------------------------

    @staticmethod
    def _parse(raw_text: str) -> list[dict]:
        """
        Извлекает JSON со списком дорков из сырого текста модели.

        Стратегия (от простого к надёжному):
            1) срезаем markdown-забор ``` ... ```;
            2) если не помогло — берём подстроку от первой "{" до последней "}";
            3) валидируем, что внутри {"dorks": [ ... ]}.

        Raises:
            ResponseParsingError: если ни одна стратегия не сработала.
        """
        # Защита от None/пустой строки
        text = (raw_text or "").strip()
        # Готовим переменную для строкового JSON
        json_candidate = text

        # Шаг 1: если модель обернула JSON в markdown-забор — вырезаем содержимое
        fence_match = _FENCE_RE.search(text)
        if fence_match:
            json_candidate = fence_match.group(1).strip()

        # Шаг 2: «хирургический» fallback — срез от первой фигурной скобки до последней
        if not json_candidate.startswith("{"):
            first = json_candidate.find("{")
            last = json_candidate.rfind("}")
            if first != -1 and last > first:
                json_candidate = json_candidate[first : last + 1]

        # Пытаемся распарсить JSON; ошибка парсинга конвертируется в доменную
        try:
            data = json.loads(json_candidate)
        except json.JSONDecodeError as exc:
            # Включаем фрагмент сырого ответа — это сильно упрощает отладку промпта
            raise ResponseParsingError(
                f"Ответ ИИ не является JSON ({exc.msg}). Фрагмент: {text[:200]}"
            ) from exc

        # Проверяем корневую структуру: ожидаем объект со списком в поле dorks
        if not isinstance(data, dict) or not isinstance(data.get("dorks"), list):
            raise ResponseParsingError("В ответе ИИ нет массива 'dorks'.")

        # Возвращаем исходный список словарей (валидация полей — в generate)
        return data["dorks"]

    # --- Протокол контекстного менеджера -------------------------------------

    def close(self) -> None:
        # Закрываем HTTP-клиент
        self._client.close()

    def __enter__(self) -> "DorkGenerator":
        # Поддержка with-блока
        return self

    def __exit__(self, *exc_info: object) -> None:
        # Гарантированное освобождение ресурсов
        self.close()
