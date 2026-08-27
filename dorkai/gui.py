"""
gui.py — графическая оболочка dorkAI (tkinter из стандартной поставки Python).

Дизайн: «престижный минимализм» — тёмная палитра, много воздуха,
одна акцентная кнопка, ничего лишнего.

Особенность: кнопка «API-ключ» открывает диалог, где ключ вставляется
и сохраняется ОДНИМ кликом (пишется в .env, без правок кода).

Потокобезопасность: сетевой вызов идёт в фоновом потоке, а обновление
виджетов планируем через self.after(...) — tkinter нельзя трогать из потоков.
"""

# os.path — для извлечения имени файла в диалоге (не критично, но пригождается)
import threading  # фоновый поток, чтобы GUI не «замерзал» во время запроса к ИИ

# tkinter — стандартная GUI-библиотека Python
import tkinter as tk
# ttk — тематические виджеты (кнопки/скроллбар выглядят нативно)
from tkinter import ttk
# scrolledtext — текстовый виджет со встроенным скроллом
from tkinter.scrolledtext import ScrolledText
# messagebox — всплывающие информационные окна
from tkinter import messagebox

# Ядро приложения
from .config import Settings
from .dork_generator import DorkGenerator
from .dork_generator import GenerationResult
from .exceptions import DorkAIError

# --- Палитра (минимализм: тёмный фон, один акцент) ---------------------------
C_BG = "#101216"        # основной фон окна
C_PANEL = "#161A20"     # фон «карточек»/полей
C_BORDER = "#23272F"    # тонкие рамки
C_FG = "#E8EAED"        # основной текст
C_MUTED = "#8A9199"     # второстепенный текст
C_ACCENT = "#4F8CFF"    # акцентный цвет (кнопка «Сгенерировать»)
C_ACCENT_HOVER = "#6FA0FF"
C_OK = "#3FB96F"        # зелёный индикатор «ключ есть»
C_ERR = "#E5534B"       # красный — ошибки

# Шрифтовая пара (есть на любой Windows; fallback tkinter сделает сам)
F_TITLE = ("Segoe UI", 15, "bold")
F_TEXT = ("Segoe UI", 10)
F_MONO = ("Consolas", 10)   # моноширинный — для самих дорков


class ApiKeyDialog(tk.Toplevel):
    """
    Модальное окно «ввод API-ключа одним кликом».

    Логика: вставил -> «Сохранить» -> ключ уезжает в .env,
    статус в главном окне мгновенно становится зелёным.
    """

    def __init__(self, master, settings: Settings, on_saved) -> None:
        # Инициализация Toplevel (отдельного окна поверх главного)
        super().__init__(master)
        # Сохраняем ссылки для колбэков
        self._settings = settings
        self._on_saved = on_saved  # функция, которую позовём после успешного сохранения

        # Оформление окна
        self.title("API-ключ")
        self.configure(bg=C_BG)
        self.resizable(False, False)
        # Модальность: блокируем главное окно, пока открыт диалог
        self.transient(master)
        self.grab_set()

        # --- Виджеты диалога -------------------------------------------------
        # Заголовок
        tk.Label(
            self, text="Вставьте API-ключ", bg=C_BG, fg=C_FG, font=F_TITLE
        ).pack(anchor="w", padx=20, pady=(18, 4))
        # Пояснение мелким серым
        tk.Label(
            self,
            text="Ключ сохраняется локально в файл .env и не зашивается в код.",
            bg=C_BG, fg=C_MUTED, font=F_TEXT, wraplength=380, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 12))

        # Рамка-«карточка» вокруг поля ввода (для аккуратной тонкой границы)
        entry_frame = tk.Frame(self, bg=C_BORDER, padx=1, pady=1)
        entry_frame.pack(fill="x", padx=20)
        # Само поле ввода: show="*" скрывает символы ключа
        self._entry = tk.Entry(
            entry_frame,
            bg=C_PANEL, fg=C_FG, insertbackground=C_FG,
            font=F_MONO, show="*", relief="flat",
        )
        # Растягиваем поле на всю ширину карточки
        self._entry.pack(fill="both", ipady=7, padx=8, pady=8)
        # Автофокус: пользователь сразу может нажать Ctrl+V
        self._entry.focus_set()

        # Ряд кнопок внизу
        buttons = tk.Frame(self, bg=C_BG)
        buttons.pack(fill="x", padx=20, pady=(14, 18))

        # Кнопка «Вставить из буфера» — тот самый ввод «одним кликом»
        tk.Button(
            buttons, text="Вставить из буфера", command=self._paste_from_clipboard,
            bg=C_PANEL, fg=C_FG, activebackground=C_BORDER, activeforeground=C_FG,
            relief="flat", font=F_TEXT, padx=12, pady=6, cursor="hand2",
        ).pack(side="left")

        # Акцентная кнопка сохранения
        tk.Button(
            buttons, text="Сохранить", command=self._save,
            bg=C_ACCENT, fg="#FFFFFF", activebackground=C_ACCENT_HOVER,
            activeforeground="#FFFFFF", relief="flat", font=F_TEXT,
            padx=16, pady=6, cursor="hand2",
        ).pack(side="right")

        # Enter в поле = сохранить (ускоряет ввод)
        self._entry.bind("<Return>", lambda _e: self._save())
        # Escape = закрыть диалог без сохранения
        self.bind("<Escape>", lambda _e: self.destroy())

        # Центрируем окно относительно родителя
        self._center_over(master)

    # --- Поведение ------------------------------------------------------------

    def _center_over(self, master) -> None:
        # Даём окну рассчитать свои размеры
        self.update_idletasks()
        # Геометрия родителя: x, y, width, height
        x, y = master.winfo_rootx(), master.winfo_rooty()
        w, h = master.winfo_width(), master.winfo_height()
        # Свои размеры диалога
        dw, dh = self.winfo_reqwidth(), self.winfo_reqheight()
        # Формула центрирования
        self.geometry(f"+{x + (w - dw) // 2}+{y + (h - dh) // 3}")

    def _paste_from_clipboard(self) -> None:
        # Пытаемся прочитать буфер обмена Windows
        try:
            text = self.clipboard_get()
        except tk.TclError:
            # Буфер пуст — тихо выходим
            return
        # Очищаем поле и вставляем содержимое буфера
        self._entry.delete(0, "end")
        self._entry.insert(0, text.strip())
        # Переносим фокус на кнопку сохранения
        self.focus_set()

    def _save(self) -> None:
        # Читаем то, что ввёл пользователь
        key = self._entry.get().strip()
        # Пустой ключ — предупреждение
        if not key:
            messagebox.showwarning("API-ключ", "Поле пустое — вставьте ключ.", parent=self)
            return
        # Сохраняем через ядро (пишется .env + обновляются живые настройки)
        if self._settings.save_api_key(key):
            # Успех: уведомляем главный окно (обновит индикатор статуса)
            self._on_saved()
            # Закрываем диалог
            self.destroy()
        else:
            # Не удалось записать файл — сообщаем
            messagebox.showerror("API-ключ", "Не удалось записать .env (проверьте права доступа).", parent=self)


class DorkAIApp(tk.Tk):
    """Главное окно приложения dorkAI."""

    def __init__(self, settings: Settings) -> None:
        # Инициализация корневого окна tkinter
        super().__init__()
        # Сохраняем настройки ядра
        self._settings = settings
        # Сервис генерации (общий для GUI и CLI)
        self._generator = DorkGenerator(settings)
        # Последний успешный результат — нужен кнопке «Копировать все»
        self._last_result: GenerationResult | None = None
        # Служебные поля для анимации статуса и фонового потока
        self._spinner_job: str | None = None
        self._spinner_dots = 0
        self._worker: threading.Thread | None = None

        # Базовое оформление окна
        self.title("dorkAI — генератор Google Dorks")
        self.configure(bg=C_BG)
        self.geometry("760x640")
        self.minsize(640, 520)

        # Собираем интерфейс тремя блоками
        self._build_header()
        self._build_input_area()
        self._build_results()

        # Рисуем стартовый статус (ключ есть/нет)
        self._refresh_key_status()

        # Корректно закрываем HTTP-клиент при закрытии окна
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # --- Построение интерфейса --------------------------------------------------

    def _build_header(self) -> None:
        # Верхняя панель: статус ключа слева, кнопка «API-ключ» справа
        header = tk.Frame(self, bg=C_BG)
        header.pack(fill="x", padx=20, pady=(16, 8))

        # Заголовок приложения
        tk.Label(header, text="dorkAI", bg=C_BG, fg=C_FG, font=F_TITLE).pack(side="left")
        # Подзаголовок приглушённым цветом
        tk.Label(
            header, text="  Google Dorks через ИИ", bg=C_BG, fg=C_MUTED, font=F_TEXT
        ).pack(side="left", pady=(6, 0))

        # Кнопка открытия диалога ключа — та самая «вставка ключа одним кликом»
        tk.Button(
            header, text="API-ключ", command=self._open_key_dialog,
            bg=C_PANEL, fg=C_FG, activebackground=C_BORDER, activeforeground=C_FG,
            relief="flat", font=F_TEXT, padx=14, pady=6, cursor="hand2",
        ).pack(side="right")

        # Строка статуса: индикатор-точка + текст (заполняется _refresh_key_status)
        status_line = tk.Frame(self, bg=C_BG)
        status_line.pack(fill="x", padx=20)
        # Цветная точка-индикатор (юникодный кружок, цвет меняется динамически)
        self._dot = tk.Label(status_line, text="●", bg=C_BG, fg=C_ERR, font=("Segoe UI", 10))
        self._dot.pack(side="left")
        # Текстовое пояснение рядом с точкой
        self._key_status = tk.Label(status_line, text="", bg=C_BG, fg=C_MUTED, font=F_TEXT)
        self._key_status.pack(side="left", padx=(6, 0))

        # Тонкая линия-разделитель под шапкой
        tk.Frame(self, bg=C_BORDER, height=1).pack(fill="x", padx=20, pady=(10, 0))

    def _build_input_area(self) -> None:
        # Блок ввода темы исследования
        area = tk.Frame(self, bg=C_BG)
        area.pack(fill="x", padx=20, pady=(14, 4))

        # Подпись над полем
        tk.Label(area, text="Тема исследования", bg=C_BG, fg=C_MUTED, font=F_TEXT).pack(anchor="w")

        # Ряд: поле ввода + акцентная кнопка
        row = tk.Frame(area, bg=C_BG)
        row.pack(fill="x", pady=(6, 0))

        # Карточка-рамка для поля (тонкая граница как у инпутов в дорогих UI-китах)
        entry_card = tk.Frame(row, bg=C_BORDER)
        entry_card.pack(side="left", fill="x", expand=True, ipadx=1, ipady=1, padx=(0, 10))
        # Поле ввода темы
        self._entry = tk.Entry(
            entry_card, bg=C_PANEL, fg=C_FG, insertbackground=C_FG,
            font=("Segoe UI", 11), relief="flat",
        )
        self._entry.pack(fill="both", ipady=8, padx=8)
        # Placeholder и горячие клавиши
        self._placeholder = "Например: публичные документы и профили компании X"
        self._entry.insert(0, self._placeholder)
        self._entry.config(fg=C_MUTED)
        self._entry.bind("<FocusIn>", self._clear_placeholder)
        self._entry.bind("<FocusOut>", self._restore_placeholder)
        # Enter в поле запускает генерацию — быстрее, чем тянуться к мыши
        self._entry.bind("<Return>", lambda _e: self._on_generate())

        # Главная акцентная кнопка
        self._generate_btn = tk.Button(
            row, text="Сгенерировать", command=self._on_generate,
            bg=C_ACCENT, fg="#FFFFFF", activebackground=C_ACCENT_HOVER,
            activeforeground="#FFFFFF", relief="flat",
            font=("Segoe UI", 10, "bold"), padx=18, cursor="hand2",
        )
        self._generate_btn.pack(side="right", fill="y")

        # Строка динамического статуса (анимация «...», ошибки, успешные сообщения)
        self._status = tk.Label(self, text="", bg=C_BG, fg=C_MUTED, font=F_TEXT, anchor="w")
        self._status.pack(fill="x", padx=20, pady=(6, 0))

    def _build_results(self) -> None:
        # Блок вывода результатов
        area = tk.Frame(self, bg=C_BG)
        area.pack(fill="both", expand=True, padx=20, pady=(10, 16))

        # Панель инструментов блока результатов
        tools = tk.Frame(area, bg=C_BG)
        tools.pack(fill="x", pady=(0, 6))
        tk.Label(tools, text="Результаты", bg=C_BG, fg=C_MUTED, font=F_TEXT).pack(side="left")
        # Кнопка копирования всех дорков сразу
        tk.Button(
            tools, text="Копировать все", command=self._copy_all,
            bg=C_PANEL, fg=C_FG, activebackground=C_BORDER, activeforeground=C_FG,
            relief="flat", font=F_TEXT, padx=10, pady=4, cursor="hand2",
        ).pack(side="right")

        # Текстовое поле со скроллом — только для чтения
        self._output = ScrolledText(
            area, bg=C_PANEL, fg=C_FG, relief="flat", wrap="word",
            font=F_TEXT, insertbackground=C_FG, state="disabled",
            borderwidth=0, highlightthickness=1, highlightbackground=C_BORDER,
        )
        self._output.pack(fill="both", expand=True)
        # Внутренние отступы «воздуха» — часть минималистичной эстетики
        self._output.configure(padx=16, pady=14)

        # Настраиваем текстовые теги (стили фрагментов внутри поля)
        self._output.tag_configure("h1", font=("Segoe UI", 11, "bold"), foreground=C_FG, spacing3=8)
        self._output.tag_configure("num", foreground=C_ACCENT, font=("Segoe UI", 10, "bold"))
        self._output.tag_configure("title", foreground=C_FG, font=("Segoe UI", 10, "bold"), spacing1=10)
        self._output.tag_configure("query", foreground="#9ECBFF", font=F_MONO, lmargin1=18, lmargin2=18)
        self._output.tag_configure("desc", foreground=C_MUTED, font=F_TEXT, lmargin1=18, lmargin2=18, spacing3=4)

    # --- Поведение статуса ключа ------------------------------------------------

    def _refresh_key_status(self) -> None:
        # Обновляем индикатор по факту наличия ключа в настройках
        if self._settings.has_api_key:
            # Зелёная точка + маскированный ключ (первые 6 символов)
            masked = self._settings.api_key[:6] + "…"
            self._dot.config(fg=C_OK)
            self._key_status.config(text=f"Ключ подключён ({masked})")
        else:
            # Красная точка + приглашение нажать кнопку
            self._dot.config(fg=C_ERR)
            self._key_status.config(text="Ключ не задан — нажмите «API-ключ»")

    def _open_key_dialog(self) -> None:
        # Открываем модальный диалог ввода ключа
        ApiKeyDialog(self, self._settings, on_saved=self._refresh_key_status)

    # --- Placeholder логика --------------------------------------------------------

    def _clear_placeholder(self, _event=None) -> None:
        # При фокусе убираем подсказку, если она ещё на месте
        if self._entry.get() == self._placeholder:
            self._entry.delete(0, "end")
            self._entry.config(fg=C_FG)

    def _restore_placeholder(self, _event=None) -> None:
        # Если поле пустое при потере фокуса — возвращаем подсказку
        if not self._entry.get():
            self._entry.insert(0, self._placeholder)
            self._entry.config(fg=C_MUTED)

    # --- Генерация (взаимодействие с ядром) --------------------------------------

    def _on_generate(self) -> None:
        # Обработчик кнопки/Enter: валидируем ввод и запускаем фоновый поток
        query = self._entry.get().strip()
        # Подсказка-плейсхолдер не считается реальным запросом
        if not query or query == self._placeholder:
            messagebox.showinfo("dorkAI", "Введите тему исследования.")
            return
        # Без ключа сразу открываем диалог его ввода
        if not self._settings.has_api_key:
            self._open_key_dialog()
            return
        # Блокируем интерфейс на время запроса (кнопка + поле)
        self._set_busy(True)
        # Создаём демона-поток: он не помешает закрытию приложения
        self._worker = threading.Thread(target=self._worker_run, args=(query,), daemon=True)
        self._worker.start()

    def _worker_run(self, query: str) -> None:
        # Выполняется В ФОНОВОМ ПОТОКЕ: здесь нельзя трогать tkinter-виджеты
        try:
            # Тяжёлая работа вынесена в ядро
            result = self._generator.generate(query)
            # Возврат в главный поток через after (безопасный мост в tkinter)
            self.after(0, self._on_success, result)
        except DorkAIError as exc:
            # Доменные ошибки показываем как есть
            self.after(0, self._on_error, str(exc))
        except Exception as exc:  # noqa: BLE001 — последний рубеж защиты GUI
            # Непредвиденные ошибки тоже не должны «ронять» окно
            self.after(0, self._on_error, f"Неожиданная ошибка: {exc}")

    def _on_success(self, result: GenerationResult) -> None:
        # Выполняется в главном потоке: разблокируем UI и рисуем результат
        self._set_busy(False)
        # Запоминаем результат для «копировать все»
        self._last_result = result
        # Рендерим список дорков
        self._render_result(result)
        # Короткое подтверждение в статусе
        self._status.config(text=f"Готово: {len(result.dorks)} дорков за {result.elapsed_seconds} с", fg=C_OK)

    def _on_error(self, message: str) -> None:
        # Выполняется в главном потоке: разблокируем UI и показываем ошибку
        self._set_busy(False)
        # Красный статус с текстом ошибки
        self._status.config(text=message, fg=C_ERR)

    def _render_result(self, result: GenerationResult) -> None:
        # Полностью перерисовываем поле результатов
        self._output.config(state="normal")
        self._output.delete("1.0", "end")
        # Шапка: тема исследования
        self._output.insert("end", f"Тема: {result.source_query}\n", "h1")
        # Каждый дорк отдельным блоком
        for i, dork in enumerate(result.dorks, start=1):
            # Номер + название техники
            self._output.insert("end", f"{i:>2}  ", "num")
            self._output.insert("end", f"{dork.title}\n", "title")
            # Сам запрос моноширинным — его копируют
            self._output.insert("end", f"{dork.query}\n", "query")
            # Пояснение (если модель его дала)
            if dork.description:
                self._output.insert("end", f"{dork.description}\n", "desc")
            # Встраиваем кнопку «копировать» прямо напротив дорка
            copy_btn = tk.Button(
                self._output, text="копировать",
                command=lambda q=dork.query: self._copy_text(q, f"Скопировано: {dork.title}"),
                bg=C_BORDER, fg=C_MUTED, activebackground=C_ACCENT, activeforeground="#FFFFFF",
                relief="flat", font=("Segoe UI", 8), cursor="hand2", padx=8, pady=1,
            )
            # Вставляем кнопку как «окошко» в текстовый поток
            self._output.window_create("end", window=copy_btn)
            self._output.insert("end", "\n")
        # Возвращаем полю режим «только чтение»
        self._output.config(state="disabled")

    # --- Буфер обмена -------------------------------------------------------------

    def _copy_text(self, text: str, ok_message: str) -> None:
        # Универсальное копирование строки в буфер обмена Windows
        self.clipboard_clear()
        self.clipboard_append(text)
        # Визуальное подтверждение в статусной строке
        self._status.config(text=ok_message, fg=C_OK)

    def _copy_all(self) -> None:
        # Копируем все дорки разом (нумерованный список)
        if not self._last_result:
            # Копировать пока нечего
            self._status.config(text="Пока нечего копировать — сначала сгенерируйте дорки.", fg=C_MUTED)
            return
        # Собираем текст: 1. запрос (перевод строки) 2. запрос ...
        lines = [f"{i}. {dork.query}" for i, dork in enumerate(self._last_result.dorks, start=1)]
        # Отдаём в общий копировщик
        self._copy_text("\n".join(lines), "Все дорки скопированы")

    # --- Служебное -------------------------------------------------------------------

    def _set_busy(self, busy: bool) -> None:
        # Включаем/выключаем «занятой» режим интерфейса
        if busy:
            # Блокируем ввод и кнопку
            self._generate_btn.config(state="disabled", text="Думаю…")
            self._entry.config(state="disabled")
            # Запускаем анимацию точек в статусе
            self._spinner_dots = 0
            self._animate_spinner()
        else:
            # Останавливаем анимацию
            if self._spinner_job is not None:
                self.after_cancel(self._spinner_job)
                self._spinner_job = None
            # Разблокируем элементы
            self._generate_btn.config(state="normal", text="Сгенерировать")
            self._entry.config(state="normal")

    def _animate_spinner(self) -> None:
        # Анимация «Генерация…» — живой отклик вместо мёртвого зависания
        self._spinner_dots = (self._spinner_dots + 1) % 4
        self._status.config(text="Генерация" + "." * self._spinner_dots, fg=C_MUTED)
        # Планируем следующий кадр анимации через 350 мс
        self._spinner_job = self.after(350, self._animate_spinner)

    def _on_close(self) -> None:
        # Аккуратное завершение: закрываем HTTP-клиент и окно
        self._generator.close()
        self.destroy()


def run_gui(settings: Settings) -> None:
    """Точка входа графического режима: создаёт настройки и запускает цикл tkinter."""
    # Создаём и запускаем приложение (mainloop блокирует до закрытия окна)
    DorkAIApp(settings).mainloop()
