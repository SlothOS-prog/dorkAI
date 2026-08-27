"""
ai_client.py — тонкий, быстрый HTTP-клиент к OpenAI-совместимому API.

Почему httpx: современная замена requests — HTTP/2, строгие таймауты,
удобные исключения, синхронный и асинхронный API в одном пакете.

Здесь НЕТ бизнес-логики — только транспорт: запрос -> текст ответа.
"""

# time нужен для «экспоненциальной» паузы между повторными попытками
import time

# typing-подсказки делают код самодокументируемым
from typing import Any

# httpx — сторонний сверхбыстрый HTTP-клиент (см. requirements.txt)
import httpx

# Подключаем настройки и доменные исключения проекта
from .config import Settings
from .exceptions import AiClientError, MissingApiKeyError


# Внутренний маркер-исключение для управления циклом ретраев (не «утекает» наружу)
class _RetrySignal(Exception):
    """Служебный сигнал «повторить попытку», используется только внутри DorkAIClient."""


class DorkAIClient:
    """
    Клиент чата к провайдеру (Groq / OpenRouter / OpenAI — любой OpenAI-совместимый).

    Жизненный цикл: создайте один раз и переиспользуйте (клиент держит
    пул соединений), закрывайте по завершении работы (или через with).
    """

    # Сколько раз пробуем повторить запрос при временных сбоях (сеть/таймаут/5xx)
    MAX_RETRIES: int = 3
    # Базовая задержка перед повтором в секундах (растёт с номером попытки)
    RETRY_DELAY: float = 0.75

    def __init__(self, settings: Settings) -> None:
        # Сохраняем настройки (ключ, url, модель, таймаут)
        self._settings = settings
        # Создаём переиспользуемый HTTP-клиент с фиксированным таймаутом
        self._http = httpx.Client(
            # base_url позволяет вызывать post("/chat/completions") без полного URL
            base_url=settings.base_url,
            # Таймаут защищает от «вечного» ожидания ответа провайдера
            timeout=settings.request_timeout,
        )

    # --- Служебные методы -------------------------------------------------

    def _headers(self) -> dict[str, str]:
        # Собираем заголовки на каждый запрос: ключ мог обновиться через GUI
        return {
            # Стандарт авторизации: Bearer <ключ>
            "Authorization": f"Bearer {self._settings.api_key}",
            # Говорим серверу, что тело запроса — JSON
            "Content-Type": "application/json",
        }

    def _build_payload(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        # Формируем тело запроса в формате, который ожидает OpenAI-совместимый API
        payload: dict[str, Any] = {
            # Какую модель вызываем (настройка из окружения)
            "model": self._settings.model,
            # Диалог: сначала системная инструкция, затем запрос пользователя
            "messages": [
                # Системная роль — правила игры (формат, этика, лимит дорков)
                {"role": "system", "content": system_prompt},
                # Пользовательская роль — то, что ввёл человек
                {"role": "user", "content": user_message},
            ],
            # Низкая temperature => детерминированные, аккуратные ответы
            "temperature": 0.2,
            # Потолок токенов ответа: с запасом на 10 дорков
            "max_tokens": 1500,
        }
        # Если провайдер поддерживает строгий JSON — просим его явно
        if self._settings.json_mode:
            payload["response_format"] = {"type": "json_object"}
        # Готовое тело запроса
        return payload

    # --- Публичный API -----------------------------------------------------

    def chat(self, system_prompt: str, user_message: str) -> str:
        """
        Отправляет чат-запрос и возвращает ТЕКСТ ответа модели.

        Raises:
            MissingApiKeyError: ключ не задан.
            AiClientError: сеть/таймаут/HTTP-ошибка после всех ретраев.
        """
        # Ранняя проверка: без ключа нет смысла ходить в сеть
        if not self._settings.has_api_key:
            # Понятное сообщение — интерфейс покажет диалог ввода ключа
            raise MissingApiKeyError("API-ключ не задан. Нажмите кнопку «API-ключ» и вставьте его.")

        # Тело запроса собираем один раз — оно не меняется между ретраями
        payload = self._build_payload(system_prompt, user_message)

        # Переменная для «последней ошибки», чтобы поднять её после исчерпания попыток
        last_error: AiClientError | None = None

        # Цикл попыток: 1..MAX_RETRIES
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                # POST на стандартный эндпоинт чата; json= сам сериализует payload
                response = self._http.post(
                    "/chat/completions",
                    json=payload,
                    headers=self._headers(),
                )

                # Отдельно разбираем 401: почти наверняка невалидный ключ
                if response.status_code == 401:
                    # Ретраи бесполезны — ключ неправильный
                    raise AiClientError(
                        "Провайдер отклонил ключ (HTTP 401). Проверьте API-ключ."
                    )

                # 4xx (кроме 401) — наша ошибка в запросе, повторять бессмысленно
                if 400 <= response.status_code < 500:
                    # Показываем короткий фрагмент тела, чтобы понять причину
                    raise AiClientError(
                        f"Ошибка запроса (HTTP {response.status_code}): {response.text[:200]}"
                    )

                # 5xx — временные проблемы провайдера: логично повторить попытку
                if response.status_code >= 500:
                    # Запоминаем ошибку и уходим на повтор
                    last_error = AiClientError(f"Сервер провайдера недоступен (HTTP {response.status_code}).")
                    # Прыгаем в блок обработки ретрая внизу
                    raise _RetrySignal()

                # Успешный HTTP: разбираем JSON-тело ответа
                data = response.json()
                # Достаём список вариантов ответа (по спецификации там минимум один)
                choices = data.get("choices") or []
                # Если провайдер вернул пустой список — это аномалия протокола
                if not choices:
                    raise AiClientError("Пустой ответ модели (нет choices).")
                # Контент лежит в choices[0].message.content
                content = (choices[0].get("message") or {}).get("content", "")
                # Пустая строка контента тоже аномалия — лучше честная ошибка
                if not content.strip():
                    raise AiClientError("Модель вернула пустой текст.")
                # Всё хорошо — возвращаем текст наружу (там его распарсит dork_generator)
                return content.strip()

            except _RetrySignal:
                # Техническое исключение ниже; здесь просто продолжаем цикл
                pass

            except httpx.TimeoutException as exc:
                # Таймаут — частый временный сбой: запоминаем и пробуем снова
                last_error = AiClientError(f"Таймаут запроса к провайдеру ({exc.__class__.__name__}).")

            except httpx.TransportError as exc:
                # Сетевые проблемы (DNS, обрыв соединения) — тоже кандидаты на ретрай
                last_error = AiClientError(f"Сетевая ошибка: {exc}")

            except AiClientError:
                # Наши «фатальные» ошибки (401, 4xx, пустой ответ) — пробрасываем сразу
                raise

            # Если мы здесь — попытка не удалась; ждём и пробуем снова (если попытки остались)
            if attempt < self.MAX_RETRIES:
                # Пауза растёт с номером попытки: 0.75с, 1.5с, 2.25с...
                time.sleep(self.RETRY_DELAY * attempt)

        # Все попытки исчерпаны — поднимаем последнюю известную ошибку
        raise last_error or AiClientError("Неизвестная ошибка запроса.")

    # --- Протокол контекстного менеджера ------------------------------------

    def close(self) -> None:
        # Освобождаем соединения пула
        self._http.close()

    def __enter__(self) -> "DorkAIClient":
        # Позволяет использовать: with DorkAIClient(settings) as client: ...
        return self

    def __exit__(self, *exc_info: object) -> None:
        # Гарантированно закрываем клиент при выходе из блока with
        self.close()
