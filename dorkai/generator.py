"""
generator.py — фасад проекта: класс DorkGenerator.

Именно его импортирует CLI (и любой другой потребитель):
    gen = DorkGenerator()
    batch = await gen.generate("поиск директорий example.com", count=5)
"""

from typing import Optional             # для необязательных типов аннотаций

from .config import Settings, get_settings       # настройки приложения
from .errors import EmptyTopicError, MissingAPIKeyError  # наши исключения
from .llm_client import LLMClient                # сетевой клиент к LLM
from .models import DorkBatch                    # результирующая структура данных
from .prompts import SYSTEM_PROMPT, build_user_prompt  # тексты промптов


class DorkGenerator:
    """Высококоординированный сервис генерации дорков.

    Жизненный цикл: использовать как асинхронный менеджер контекста,
    чтобы HTTP-соединения гарантированно закрывались:

        async with DorkGenerator() as generator:
            batch = await generator.generate("...", count=5)
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Принимает готовые Settings ИЛИ поднимает их сам из окружения."""
        self.settings = settings or get_settings()   # DI: можно подсунуть тестовые
        if not self.settings.is_ready:               # ключ не заполнен?
            raise MissingAPIKeyError(                # сразу понятная человеку ошибка
                "API-ключ не задан. Вставьте ключ в файл .env "
                "(строка DORKAI_API_KEY=...) либо экспортируйте переменную окружения."
            )
        self.client = LLMClient(self.settings)       # создаём клиента сети

    async def generate(self, topic: str, count: int = 5) -> DorkBatch:
        """Главная функция: тема -> список дорков.

        Шаги: валидация входа -> сборка промпта -> запрос к модели ->
        разбор ответа в DorkBatch.
        """
        clean_topic = topic.strip()                  # убираем пробелы по краям
        if not clean_topic:                          # пользователь прислал "" или "   "
            raise EmptyTopicError("Тема запроса пустая — нечего отправлять модели.")
        bounded_count = max(1, min(count, 30))       # ограничиваем счётчик 1..30

        user_prompt = build_user_prompt(clean_topic, bounded_count)  # задание
        raw_answer = await self.client.complete(     # сетевой вызов (await!)
            system_prompt=SYSTEM_PROMPT,             # роль и правила формата
            user_prompt=user_prompt,                 # конкретика задачи
        )
        return DorkBatch.from_llm_text(              # превращаем текст в структуру
            raw_text=raw_answer,                     # сырой ответ модели
            topic=clean_topic,                       # сохраняем тему в пакете
            model=self.settings.model_name,          # сохраняем имя модели
        )

    async def __aenter__(self) -> "DorkGenerator":
        """Вход в `async with` — возвращаем сами себя."""  # noqa: DAR101
        return self                                  # объект доступен после as

    async def __aexit__(self, *exc_info) -> None:
        """Выход из `async with` — закрываем HTTP-сессию клиента."""
        await self.client.aclose()                   # освобождаем ресурсы
