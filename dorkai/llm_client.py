"""
llm_client.py — тонкая асинхронная обёртка над любым OpenAI-совместимым API.

Почему именно официальный SDK openai:
  * работает с OpenAI, Groq, OpenRouter, DeepSeek, vLLM (меняется только base_url);
  * внутри используется httpx — асинхронный HTTP/2 клиент;
  * встроенные повторные попытки (max_retries) при сетевых сбоях.
"""

from openai import AsyncOpenAI              # асинхронный клиент

from .config import Settings                # наш контейнер настроек
from .errors import ModelOutputError        # ошибка пустого ответа модели


class LLMClient:
    """Отвечает ровно за одно: отправить промпт — получить строку-ответ."""

    def __init__(self, settings: Settings):
        """Сохраняет настройки и создаёт клиента SDK один раз (переиспользуется)."""
        self._settings = settings           # приватное поле: наружу отдавать не нужно
        self._client = AsyncOpenAI(         # создание асинхронного клиента
            api_key=settings.api_key,       # ключ из переменных окружения/.env
            base_url=settings.base_url,     # адрес сервиса (OpenAI-совместимый)
            timeout=settings.request_timeout,   # сколько секунд ждём ответа
            max_retries=2,                  # авто-ретраи при сетевых сбоях/429
        )

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        """Отправляет пару промптов в чат-модель и возвращает ТЕКСТ ответа.

        Именованные аргументы (*) запрещают вызывать позиционно — меньше путаницы.
        """
        response = await self._client.chat.completions.create(
            model=self._settings.model_name,          # имя модели из настроек
            messages=[                                 # история диалога (без истории)
                {"role": "system", "content": system_prompt},  # роль и правила
                {"role": "user", "content": user_prompt},      # конкретное задание
            ],
            temperature=self._settings.temperature,    # степень творчества модели
        )
        content = response.choices[0].message.content  # достаём текст первого варианта
        if not content:                                # модель может вернуть None/пустоту
            raise ModelOutputError("Модель вернула пустой ответ.")  # фиксируем проблему
        return content.strip()                         # чистый текст без лишних пробелов

    async def aclose(self) -> None:
        """Аккуратно закрывает HTTP-сессию (вызывать при завершении работы)."""
        await self._client.close()                     # освобождаем соединения httpx
