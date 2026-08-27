"""
models.py — модели данных (контракты) и разбор ответа нейросети.

Пайплайн такой:
  текст от модели (str)  ->  extract_json_dict()  ->  dict
  dict                   ->  DorkBatch.from_llm_text() -> объекты с валидацией
"""

from typing import Any                       # тип «что угодно» для сырых данных

import orjson                                # сверхбыстрый JSON-парсер на Rust
import json                                  # запасной парсер стандартной библиотеки
from pydantic import BaseModel, Field        # база и поля pydantic-моделей

from .errors import ModelOutputError         # наша ошибка «не смогли разобрать ответ»


class Dork(BaseModel):
    """Один google-дорк со всеми сопутствующими данными."""

    query: str = Field(min_length=1, description="Строка поискового запроса")
    purpose: str = Field(default="", description="Краткое объяснение цели (по-русски)")
    operators: list[str] = Field(
        default_factory=list,               # если операторов нет — будет пустой список
        description="Какие поисковые операторы использованы",
    )


class DorkBatch(BaseModel):
    """Пакет готовых дорков по одной теме (результат одной генерации)."""

    topic: str = Field(description="Тема запроса пользователя")
    model: str = Field(description="Имя модели, которая сгенерировала дорки")
    dorks: list[Dork] = Field(default_factory=list, description="Список дорков")

    @classmethod
    def from_llm_text(cls, raw_text: str, topic: str, model: str) -> "DorkBatch":
        """Разбирает НЕобязательный к чистоте ответ модели в валидный DorkBatch.

        Модели любят оборачивать JSON в ```json ... ``` или добавлять болтовню,
        поэтому extract_json_dict вырезает JSON автоматически.
        """
        payload: dict[str, Any] = extract_json_dict(raw_text)   # текст -> словарь
        dorks_raw = payload.get("dorks")                        # берём ключ "dorks"
        if not isinstance(dorks_raw, list):                     # ключ отсутствует/кривой
            raise ModelOutputError(                             # сигнализируем наверх
                "В ответе модели нет массива 'dorks'."
            )
        dorks = [Dork.model_validate(item) for item in dorks_raw]  # валидация каждого
        return cls(topic=topic, model=model, dorks=dorks)       # собираем пакет


def extract_json_dict(raw_text: str) -> dict[str, Any]:
    """Вытаскивает первый JSON-объект из произвольного текста модели.

    Порядок попыток:
      1. текст обёрнут в код-фенс ```json ... ```   -> берём содержимое фенса;
      2. иначе срезаем всё от первой '{' до последней '}';
      3. парсим orjson (быстро), при неудаче — json (медленно, но терпимо).
    """
    text = raw_text.strip()                  # убираем случайные пробелы по краям

    if "```" in text:                        # признак markdown-код-фенса
        chunk = text.split("```")[1]         # кусок между первым и вторым ```
        if chunk.lower().startswith("json"): # у фенса бывает метка языка "json"
            chunk = chunk[4:]                # отрезаем слово "json" (4 символа)
        text = chunk.strip()                 # дальше работаем с этим куском

    first = text.find("{")                   # индекс первой фигурной скобки
    last = text.rfind("}")                   # индекс последней фигурной скобки
    if first == -1 or last == -1:            # скобок нет вовсе
        raise ModelOutputError("В ответе модели не найден JSON-объект.")
    candidate = text[first : last + 1]       # срез строго внутри {...}

    try:                                     # основная быстрая попытка
        return orjson.loads(candidate)       # orjson вернёт dict/list примитивов
    except orjson.JSONDecodeError:           # orjson строгий — вдруг модель была вольной
        try:                                 # вторая попытка встроенным json
            return json.loads(candidate)     # json мягче (например, с комментами)
        except json.JSONDecodeError as exc:  # совсем не JSON
            raise ModelOutputError(f"Не удалось разобрать JSON: {exc}") from exc
