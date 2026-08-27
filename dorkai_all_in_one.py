# ============================================================================
#  dorkAI — единый файл проекта: генератор Google dorks с помощью ИИ (OSINT).
#
#  КАК ПОЛЬЗОВАТЬСЯ:
#    1) установите зависимости:
#         pip install openai orjson rich python-dotenv
#    2) создайте рядом файл ".env" и вставьте ключ в строку:
#         DORKAI_API_KEY=sk-...
#       (дополнительно можно задать DORKAI_BASE_URL, DORKAI_MODEL и др.)
#    3) запустите:
#         python dorkai_all_in_one.py "открытые директории example.com" -n 8
#         python dorkai_all_in_one.py            # интерактивный режим ("q" — выход)
#  Этика: только законный OSINT публично индексируемой информации.
# ============================================================================

# ----------------------------------------------------------------------------
#  БЛОК 1. ИМПОРТЫ БИБЛИОТЕК (все внешние ставятся через pip)
# ----------------------------------------------------------------------------

import asyncio                            # асинхронный рантайм: запускаем сетевые вызовы
import argparse                           # разбор аргументов командной строки (стандартная библ.)
import json                               # запасной JSON-парсер стандартной библиотеки
import os                                 # доступ к переменным окружения
import sys                                # доступ к stdout/stderr для фикса кодировки
from dataclasses import dataclass, field  # удобные классы-структуры данных без boilerplate
from pathlib import Path                  # объектная работа с путями файлов
from typing import Any, Optional          # аннотации типов для читаемости кода

import orjson                             # самый быстрый JSON на Python (ядро на Rust)
from dotenv import load_dotenv            # загрузка файла ".env" в переменные окружения
from openai import AsyncOpenAI            # официальный асинхронный SDK (OpenAI/Groq/OpenRouter/…)
from rich.console import Console          # цветной вывод в консоль
from rich.table import Table              # красивые таблицы результатов

console = Console()                       # один общий объект печати rich на всю программу

# ----------------------------------------------------------------------------
#  БЛОК 2. СОБСТВЕННЫЕ ИСКЛЮЧЕНИЯ (понятные ошибки вместо сырых трейсбеков)
# ----------------------------------------------------------------------------


class DorkAIError(Exception):
    """Базовая ошибка проекта: CLI ловит её одну и печатает человеко-понятный текст."""


class MissingAPIKeyError(DorkAIError):
    """API-ключ не найден ни в .env, ни в переменных окружения."""


class EmptyTopicError(DorkAIError):
    """Пользователь передал пустую тему запроса."""


class ModelOutputError(DorkAIError):
    """Ответ модели не удалось разобрать как JSON с дорками."""

# ----------------------------------------------------------------------------
#  БЛОК 3. НАСТРОЙКИ: чтение окружения / файла ".env" (ключи НИКОГДА не в коде)
# ----------------------------------------------------------------------------


@dataclass(slots=True)                    # slots=True: компактнее и быстрее обычного класса
class Settings:
    """Контейнер всех настроек приложения."""

    api_key: str = ""                     # секретный ключ (пусто == ещё не вставлен)
    base_url: str = "https://api.openai.com/v1"      # адрес OpenAI-совместимого API
    model_name: str = "gpt-4o-mini"       # имя модели генерации
    request_timeout: float = 90.0         # секунд ожидания ответа модели
    temperature: float = 0.3              # «творческая свобода» модели (0..1)

    @property                             # вычисляемое поле — вызывается как атрибут
    def is_ready(self) -> bool:
        """True, если после удаления пробелов ключ содержит хотя бы один символ."""
        return bool(self.api_key.strip())


def get_settings() -> Settings:
    """Собирает настройки из окружения: реальные переменные ПРИОРИТЕТНЕЕ .env-файла."""
    env_path = Path(__file__).resolve().parent / ".env"  # ищем .env рядом со скриптом
    if env_path.is_file():                # если файл существует...
        load_dotenv(env_path)             # ...загружаем его значения в os.environ
    return Settings(                      # создаём объект настроек из переменных
        api_key=os.getenv("DORKAI_API_KEY", "").strip()      # имя проекта основное
        or os.getenv("OPENAI_API_KEY", "").strip(),          # запасное универсальное имя
        base_url=os.getenv("DORKAI_BASE_URL", "")            # адрес сервиса
        or "https://api.openai.com/v1",                      # значение по умолчанию
        model_name=os.getenv("DORKAI_MODEL", "")
        or "gpt-4o-mini",                                    # модель по умолчанию
        request_timeout=float(os.getenv("DORKAI_REQUEST_TIMEOUT", "90")),  # таймаут
        temperature=float(os.getenv("DORKAI_TEMPERATURE", "0.3")),         # температура
    )

# ----------------------------------------------------------------------------
#  БЛОК 4. ПРОМПТЫ: «мозг» генератора — роль модели и правила формата ответа
# ----------------------------------------------------------------------------

SYSTEM_PROMPT: str = (
    # 1. Роль: опытный осинт-аналитик.
    "You are an elite OSINT analyst who writes advanced Google search queries "
    "(so called 'Google Dorks') using search operators.\n"
    # 2. Разрешённые операторы — расширяем арсенал модели.
    "Use a wide range of operators and combine them: site:, inurl:, intitle:, "
    "intext:, filetype:, ext:, before:, after:, cache:, related:, numrange/, "
    ".. ranges, * wildcard, \"quoted phrases\", -exclusion, AND/OR.\n"
    # 3. Правила качества каждого дорка.
    "Rules for every dork:\n"
    "- exactly one line, valid Google search syntax, no fabricated operators;\n"
    "- escalate from broad reconnaissance to precise targeted findings;\n"
    "- no duplicates and no trivial queries that any beginner would write;\n"
    "- only legal OSINT of publicly indexed information.\n"
    # 4. ЖЁСТКИЙ формат вывода — только JSON заданной схемы.
    'Answer with STRICT JSON only: {"dorks": ['
    '{"query": "<one-line google query>", '
    '"purpose": "<краткое объяснение по-русски>", '
    '"operators": ["<operator1>", "<operator2>"]}]}'
)


def build_user_prompt(topic: str, count: int) -> str:
    """Собирает конкретное задание для модели из темы и количества дорков."""
    return (
        f"Topic: {topic}\n"              # тема поиска пользователя как есть
        f"Generate exactly {count} dorks in the JSON format described above."  # счётчик
    )

# ----------------------------------------------------------------------------
#  БЛОК 5. МОДЕЛИ ДАННЫХ + ПАРСЕР ОТВЕТА НЕЙРОСЕТИ (текст -> структуры)
# ----------------------------------------------------------------------------


@dataclass(slots=True)                    # лёгкая неизменяемая структура одного дорка
class Dork:
    query: str                            # строка поискового запроса google
    purpose: str = ""                     # краткое пояснение цели (по-русски)
    operators: list[str] = field(default_factory=list)  # список использованных операторов


@dataclass(slots=True)                    # пакет дорков — результат одной генерации
class DorkBatch:
    topic: str                            # исходная тема запроса
    model: str                            # какая модель сгенерировала
    dorks: list[Dork] = field(default_factory=list)     # список готовых дорков

    @classmethod                          # фабричный метод: вызывается от имени класса
    def from_llm_text(cls, raw_text: str, topic: str, model: str) -> "DorkBatch":
        """Превращает сырой ответ модели в валидный пакет DorkBatch."""
        payload = extract_json_dict(raw_text)           # текст -> словарь (см. ниже)
        dorks_raw = payload.get("dorks")                # достаём массив по ключу "dorks"
        if not isinstance(dorks_raw, list):             # ключа нет или это не список
            raise ModelOutputError("В ответе модели нет массива 'dorks'.")
        dorks: list[Dork] = []                          # сюда сложим распарсенные дорки
        for item in dorks_raw:                          # проверяем каждый элемент вручную
            if isinstance(item, dict) and isinstance(item.get("query"), str):
                dorks.append(                           # собираем объект Dork
                    Dork(
                        query=item["query"].strip() or "-",                 # строка запроса
                        purpose=str(item.get("purpose", "")),               # пояснение
                        operators=[str(op) for op in item.get("operators", [])],  # операторы
                    )
                )
        if not dorks:                                   # не осталось ни одного валидного
            raise ModelOutputError("Ответ модели не содержал ни одного корректного дорка.")
        return cls(topic=topic, model=model, dorks=dorks)   # итоговый пакет


def extract_json_dict(raw_text: str) -> dict[str, Any]:
    """Вытаскивает первый JSON-объект из произвольного текста ответа модели.

    Модели любят оборачивать JSON в ```json … ``` или добавлять болтовню,
    поэтому: срезаем фенс, затем всё от первой '{' до последней '}'.
    """
    text = raw_text.strip()               # убираем случайные пробелы по краям
    if "```" in text:                     # признак markdown-код-фенса вокруг JSON
        chunk = text.split("```")[1]      # берём кусок между первым и вторым ```
        if chunk.lower().startswith("json"):   # у фенса бывает метка языка "json"
            chunk = chunk[4:]             # отрезаем слово "json" (ровно 4 символа)
        text = chunk.strip()              # дальше работаем с очищенным куском
    first, last = text.find("{"), text.rfind("}")   # границы фигурных скобок
    if first == -1 or last == -1:         # скобок вообще нет — это не наш формат
        raise ModelOutputError("В ответе модели не найден JSON-объект.")
    candidate = text[first : last + 1]    # срез строго внутри {...}
    try:
        return orjson.loads(candidate)    # быстрая попытка парсинга (orjson/Rust)
    except orjson.JSONDecodeError:        # orjson строгий — пробуем мягче
        try:
            return json.loads(candidate)  # запасной парсер стандартной библиотеки
        except json.JSONDecodeError as exc:     # совсем не JSON
            raise ModelOutputError(f"Не удалось разобрать JSON: {exc}") from exc

# ----------------------------------------------------------------------------
#  БЛОК 6. СЕТЕВОЙ КЛИЕНТ LLM: отправить промпт — получить текст ответа
# ----------------------------------------------------------------------------


class LLMClient:
    """Тонкая асинхронная обёртка над любым OpenAI-совместимым API."""

    def __init__(self, settings: Settings):
        """Сохраняет настройки и один раз создаёт клиента SDK (переиспользуется далее)."""
        self._settings = settings          # приватное поле настроек
        self._client = AsyncOpenAI(        # асинхронный клиент на httpx (HTTP/2)
            api_key=settings.api_key,      # ключ из окружения/.env — никогда не хардкодим
            base_url=settings.base_url,    # адрес сервиса (OpenAI, Groq, OpenRouter…)
            timeout=settings.request_timeout,  # секунд на ожидание ответа
            max_retries=2,                 # авто-повторы при сетевых сбоях/лимитах 429
        )

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        """Отправляет пару промптов в чат-модель и возвращает чистый текст ответа."""
        response = await self._client.chat.completions.create(   # сам сетевой вызов
            model=self._settings.model_name,     # имя модели из настроек
            messages=[                           # «диалог» без истории — один ход
                {"role": "system", "content": system_prompt},   # роль + правила формата
                {"role": "user", "content": user_prompt},       # конкретное задание
            ],
            temperature=self._settings.temperature,  # степень вариативности генерации
        )
        content = response.choices[0].message.content   # текст первого варианта ответа
        if not content:                      # модель может вернуть None/пустую строку
            raise ModelOutputError("Модель вернула пустой ответ.")
        return content.strip()               # убираем лишние пробелы по краям

    async def aclose(self) -> None:
        """Аккуратно закрывает HTTP-сессию при завершении работы программы."""
        await self._client.close()           # освобождаем соединения httpx

# ----------------------------------------------------------------------------
#  БЛОК 7. ГЛАВНЫЙ СЕРВИС: класс DorkGenerator (тема -> пакет дорков)
# ----------------------------------------------------------------------------


class DorkGenerator:
    """Координатор всей логики. Используйте как async-менеджер контекста:

        async with DorkGenerator() as gen:
            batch = await gen.generate("тема", count=5)
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Принимает готовые настройки ИЛИ поднимает их сам из окружения/.env."""
        self.settings = settings or get_settings()   # DI: удобно подставлять тестовые
        if not self.settings.is_ready:               # ключ не заполнен?
            raise MissingAPIKeyError(                # сразу понятная человеку ошибка
                "API-ключ не задан. Создайте файл .env рядом со скриптом и вставьте "
                "ключ в строку DORKAI_API_KEY=… либо экспортируйте переменную окружения."
            )
        self.client = LLMClient(self.settings)       # создаём сетевого клиента

    async def generate(self, topic: str, count: int = 5) -> DorkBatch:
        """Главная функция: тема -> список дорков (валидация, промпт, запрос, парсинг)."""
        clean_topic = topic.strip()                  # нормализуем ввод пользователя
        if not clean_topic:                          # "" или одни пробелы — работать нечем
            raise EmptyTopicError("Тема запроса пустая — нечего отправлять модели.")
        bounded_count = max(1, min(count, 30))       # ограничиваем счётчик диапазоном 1..30
        raw_answer = await self.client.complete(     # сетевой вызов модели (await!)
            system_prompt=SYSTEM_PROMPT,             # роль и правила формата
            user_prompt=build_user_prompt(clean_topic, bounded_count),  # задание
        )
        return DorkBatch.from_llm_text(              # превращаем текст в структуры данных
            raw_text=raw_answer,                     # сырой ответ нейросети
            topic=clean_topic,                       # сохраняем тему в пакете
            model=self.settings.model_name,          # сохраняем имя модели
        )

    async def __aenter__(self) -> "DorkGenerator":
        """Вход в блок `async with` — просто возвращаем сами себя."""
        return self                                  # объект доступен после "as"

    async def __aexit__(self, *exc_info) -> None:
        """Выход из блока `async with` — гарантируем закрытие HTTP-соединений."""
        await self.client.aclose()                   # освобождаем ресурсы

# ----------------------------------------------------------------------------
#  БЛОК 8. CLI-ИНТЕРФЕЙС: аргументы командной строки, таблицы, интерактив
# ----------------------------------------------------------------------------

DEFAULT_COUNT: int = 5                   # количество дорков по умолчанию (интерактив)

# Тексты справки вынесены вверх: cmd.exe с cp1251 иногда портит кириллицу в argparse.
HELP_DESCRIPTION = "dorkAI - генератор Google dorks с помощью ИИ (OSINT backend)."
HELP_TOPIC = 'тема запроса, например: "site example.com login pages"'
HELP_COUNT = "сколько дорков сгенерировать (1..30)"
HELP_MODEL = "имя модели (перекрывает DORKAI_MODEL из .env)"
HELP_SAVE = "путь к файлу .json для сохранения результата"


def build_parser() -> argparse.ArgumentParser:
    """Создаёт и настраивает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(prog="dorkAI", description=HELP_DESCRIPTION)
    parser.add_argument("topic", nargs="?", default="", help=HELP_TOPIC)   # позиционная тема
    parser.add_argument("-n", "--count", type=int, default=DEFAULT_COUNT, help=HELP_COUNT)
    parser.add_argument("--model", type=str, default="", help=HELP_MODEL)
    parser.add_argument("--save", type=str, default="", help=HELP_SAVE)
    return parser                                  # готовый к parse_args()


def print_batch(batch: DorkBatch) -> None:
    """Печатает результат генерации в виде красивой таблицы rich."""
    table = Table(title=f"dorks по теме: {batch.topic}", show_lines=False)
    table.add_column("#", justify="right", style="dim")          # колонка нумерации
    table.add_column("Google dork", style="green")               # сам поисковый запрос
    table.add_column("Зачем", style="cyan")                      # пояснение модели
    for number, dork in enumerate(batch.dorks, start=1):         # нумеруем с единицы
        ops = ", ".join(dork.operators) if dork.operators else "-"  # операторы одной строкой
        cell = f"{dork.query}\n[dim]{ops}[/dim]"                 # дорк + операторы снизу
        table.add_row(str(number), cell, dork.purpose)           # строка таблицы
    console.print(table)                                        # рисуем таблицу
    console.print(f"[dim]модель:[/] {batch.model}   [dim]кол-во:[/] {len(batch.dorks)}")


async def run_once(topic: str, count: int, model_override: str, save_path: str) -> None:
    """Одна полная сессия: настройки -> генерация -> печать -> опциональный экспорт."""
    settings = get_settings()                      # читаем окружение/.env
    if model_override:                             # флаг --model приоритетнее .env
        settings.model_name = model_override       # подменяем имя модели на лету
    with console.status("[bold green]Модель думает...", spinner="dots"):
        async with DorkGenerator(settings) as generator:   # контекст закроет HTTP
            batch = await generator.generate(topic=topic, count=count)  # основная работа
    print_batch(batch)                             # показываем результат
    if save_path:                                  # попросили сохранить результат?
        output_file = Path(save_path)              # путь из аргумента --save
        bytes_json = orjson.dumps(                 # сериализация прямо из dataclass
            batch, default=lambda o: o.__dict__, option=orjson.OPT_INDENT_2,
        )
        output_file.write_bytes(bytes_json)        # пишем файл одним вызовом
        console.print(f"[bold blue]Сохранено в {output_file.resolve()}[/]")


def interactive_loop() -> None:
    """Бесконечный диалог: спрашивает тему у пользователя до команды выхода."""
    console.print("[bold magenta]dorkAI v0.1.0[/] — [dim]введите тему или 'q' для выхода[/]")
    while True:                                    # цикл до выхода
        try:
            topic = console.input("[bold green]> [/]")   # приглашение ввода
        except KeyboardInterrupt:                  # Ctrl+C прямо во время ввода
            break                                  # молча завершаем диалог
        if topic.strip().lower() in {"q", "quit", "exit"}:  # команды выхода
            break
        if not topic.strip():                      # пустая строка — переспрашиваем
            continue
        try:
            asyncio.run(run_once(topic.strip(), DEFAULT_COUNT, "", ""))
        except DorkAIError as error:               # наши ошибки — коротко и понятно
            console.print(f"[bold red]Ошибка:[/] {error}")
        except Exception as error:                 # сетевые/сервисные сбои и прочее
            console.print(f"[bold red]Сбой запроса:[/] {error}")


def force_utf8_console() -> None:
    """Включает UTF-8 в консоли Windows, чтобы кириллица не стала кракозябрами."""
    for stream in (sys.stdout, sys.stderr):        # оба потока вывода
        encoding = getattr(stream, "encoding", "") # текущая кодировка потока
        if encoding.lower() not in {"utf-8", "utf8"}:  # если это НЕ utf-8 (обычно cp866)…
            try:
                stream.reconfigure(encoding="utf-8")   # …перенастраиваем на UTF-8
            except AttributeError:                 # старые версии Python без reconfigure
                pass                               # продолжаем как есть


def main() -> None:
    """Точка входа консольного приложения (запуск скрипта начинается отсюда)."""
    force_utf8_console()                           # фикс кириллицы ДО любого вывода
    args = build_parser().parse_args()             # разбираем аргументы командной строки
    if not args.topic.strip():                     # тема не передана ->
        interactive_loop()                         # ...работаем в интерактивном режиме
        return                                     # после диалога программа завершена
    try:                                           # разовый режим работы
        asyncio.run(run_once(args.topic, args.count, args.model, args.save))
    except DorkAIError as error:                   # понятные ошибки конфигурации
        console.print(f"[bold red]Ошибка:[/] {error}")
        raise SystemExit(1)                        # ненулевой код возврата — для CI/скриптов
    except KeyboardInterrupt:                      # пользователь прервал выполнение
        console.print("\n[dim]Прервано пользователем.[/]")


if __name__ == "__main__":                         # защита: исполнять только при запуске файла
    main()                                         # передаём управление CLI
