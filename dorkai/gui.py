"""
gui.py — графическая оболочка dorkAI (tkinter из стандартной поставки Python).

Дизайн: «cosmic shimmer» — живой переливающийся градиент с мерцающими звёздами,
мягкая пульсация акцентов, английский интерфейс, моноширинный вывод дорков.

Архитектурные приёмы:
    * фон — Canvas, созданный ПЕРВЫМ (нижний слой стека) поверх pack/place контента;
    * «переливание» — покадровая перекраска горизонтальных линий градиента;
    * мерцание звёзд — синусоидальная интерполяция цвета к локальному фону;
    * все кадры идут через self.after(...) в главном потоке tkinter;
    * сетевой запрос — в отдельном потоке, обратно только через self.after(...).
"""

# math — тригонометрия для волн градиента и мигания звёзд
import math
# random — случайное размещение/параметры звёзд
import random
# threading — фоновый поток, чтобы интерфейс не «замерзал»
import threading

# Стандартная GUI-библиотека Python
import tkinter as tk
# Доступ к списку шрифтов системы для аккуратного выбора семейства
from tkinter import font as tk_font
# Текстовый виджет со встроенным скроллбаром
from tkinter.scrolledtext import ScrolledText
# Диалоговые окна сообщений
from tkinter import messagebox

# Ядро приложения: настройки, генератор, структуры результата, исключения
from .config import Settings
from .dork_generator import DorkGenerator
from .dork_generator import GenerationResult
from .exceptions import DorkAIError, MissingApiKeyError, EmptyQueryError

# --- Космическая палитра -------------------------------------------------------
_SP1 = (9, 11, 30)        # глубокий индиго — космическая ночь
_SP2 = (47, 26, 98)       # фиолетовая туманность
_SP3 = (9, 56, 84)        # глубокий циан — звёздная дымка

C_PANEL = "#121A38"       # панели поверх космоса
C_PANEL_DK = "#0B1026"    # фон диалога (чуть темнее)
C_BORDER = "#28325E"      # тонкие рамки
C_FG = "#EAF0FF"          # основной текст
C_MUTED = "#96A3CD"       # приглушённый текст
C_ACCENT = "#7C6CFF"      # базовый акцент (фиолетовый)
C_ACCENT_HI = "#A496FF"   # верхняя точка пульсации акцента
C_OK = "#54E0A8"          # индикатор «ключ подключён»
C_ERR = "#FF6B81"         # индикатор ошибки
C_QUERY = "#7DE3FF"       # цвет самих дорков (голубой неон)

# Базовые RGB звёзд: белые, голубоватые, фиолетовые
_STAR_RGBS = ((255, 255, 255), (178, 200, 255), (167, 139, 250))


# --- Утилиты цвета ---------------------------------------------------------------

def _lerp(a: int, b: int, t: float) -> int:
    # Линейная интерполяция канала с ограничением диапазона 0..255
    return max(0, min(255, round(a + (b - a) * t)))


def _mix(c1, c2, t: float):
    # Смешение двух RGB-кортежей: t=0 даёт c1, t=1 даёт c2
    return (_lerp(c1[0], c2[0], t), _lerp(c1[1], c2[1], t), _lerp(c1[2], c2[2], t))


def _hex(rgb) -> str:
    # RGB-кортеж → строку "#RRGGBB", которую понимает tkinter
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _unhex(hs: str):
    # Строку "#RRGGBB" → кортеж (r, g, b): обратное преобразование
    hs = hs.lstrip("#")
    return tuple(int(hs[i:i + 2], 16) for i in (0, 2, 4))


def _pick_font(candidates) -> str:
    # Возвращает первый установленный шрифт из списка приоритета
    available = set(tk_font.families())
    for name in candidates:
        if name in available:
            return name
    return "TkDefaultFont"                # безопасный фолбэк tkinter


_ACCENT_T = _unhex(C_ACCENT)              # акцент как кортеж для быстрой математики
_ACCENT_HI_T = _unhex(C_ACCENT_HI)
_OK_T = _unhex(C_OK)


class ApiKeyDialog(tk.Toplevel):
    """Модальное окно ввода API-ключа одним кликом (интерфейс — английский)."""

    def __init__(self, master, settings: Settings, on_saved) -> None:
        super().__init__(master)                 # инициализация дочернего окна
        self._settings = settings                # настройки ядра
        self._on_saved = on_saved                # колбэк после успешного сохранения
        self.title("API Key")
        self.configure(bg=C_PANEL_DK)
        self.resizable(False, False)             # фиксированный размер
        self.transient(master)                   # окно принадлежит главному
        self.grab_set()                          # модальность: блокируем родителя

        # Заголовок и пояснение — используем крупные шрифты главного окна
        tk.Label(self, text="Connect your AI provider",
                 bg=C_PANEL_DK, fg=C_FG, font=master._f_title).pack(anchor="w", padx=22, pady=(18, 4))
        tk.Label(self, text="Paste your API key.\nIt is saved locally to .env — never hardcoded into code.",
                 bg=C_PANEL_DK, fg=C_MUTED, font=master._f_body,
                 wraplength=400, justify="left").pack(anchor="w", padx=22, pady=(0, 12))

        # Карточка-рамка вокруг поля ввода ключа
        entry_frame = tk.Frame(self, bg=C_BORDER, padx=1, pady=1)
        entry_frame.pack(fill="x", padx=22)
        self._entry = tk.Entry(entry_frame, bg=C_PANEL, fg=C_FG, insertbackground=C_FG,
                               show="*", relief="flat", font=master._f_mono)
        self._entry.pack(fill="both", ipady=8, padx=10, pady=10)
        self._entry.focus_set()                  # сразу можно нажать Ctrl+V

        buttons = tk.Frame(self, bg=C_PANEL_DK)
        buttons.pack(fill="x", padx=22, pady=(14, 18))

        paste_btn = tk.Button(buttons, text="Paste from clipboard", command=self._paste_from_clipboard,
                              bg=C_PANEL, fg=C_FG, activebackground=C_BORDER, activeforeground=C_FG,
                              relief="flat", bd=0, padx=12, pady=6, cursor="hand2", font=master._f_body)
        paste_btn.pack(side="left")
        self._bind_hover(paste_btn, C_PANEL, C_BORDER)

        save_btn = tk.Button(buttons, text="Save", command=self._save,
                             bg=C_ACCENT, fg="#FFFFFF", activebackground=C_ACCENT_HI,
                             activeforeground="#FFFFFF", relief="flat", bd=0,
                             padx=20, pady=6, cursor="hand2", font=master._f_body)
        save_btn.pack(side="right")
        self._bind_hover(save_btn, C_ACCENT, C_ACCENT_HI)

        self._entry.bind("<Return>", lambda _e: self._save())  # Enter = сохранить
        self.bind("<Escape>", lambda _e: self.destroy())       # Esc = закрыть
        self._center_over(master)

    @staticmethod
    def _bind_hover(widget, normal: str, hover: str) -> None:
        # Мгновенная подсветка кнопки при наведении/уходе курсора
        widget.bind("<Enter>", lambda _e: widget.config(bg=hover))
        widget.bind("<Leave>", lambda _e: widget.config(bg=normal))

    def _center_over(self, master) -> None:
        # Центрирование диалога относительно родительского окна
        self.update_idletasks()
        x, y = master.winfo_rootx(), master.winfo_rooty()
        w, h = master.winfo_width(), master.winfo_height()
        dw, dh = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{x + (w - dw) // 2}+{y + (h - dh) // 3}")

    def _paste_from_clipboard(self) -> None:
        # Вставка содержимого буфера обмена Windows в поле ввода
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return                               # буфер пуст — тихо выходим
        self._entry.delete(0, "end")
        self._entry.insert(0, text.strip())
        self.focus_set()

    def _save(self) -> None:
        # Сохраняем ключ через ядро (пишется .env, настройки обновляются «на лету»)
        key = self._entry.get().strip()
        if not key:
            messagebox.showwarning("API Key", "Field is empty — paste your key first.", parent=self)
            return
        if self._settings.save_api_key(key):
            self._on_saved()                     # главное окно обновит индикатор
            self.destroy()
        else:
            messagebox.showerror("API Key", "Could not write .env (check folder permissions).", parent=self)


class DorkAIApp(tk.Tk):
    """Главное окно dorkAI с анимированным космическим фоном."""

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings                        # настройки ядра
        self._generator = DorkGenerator(settings)        # общий сервис генерации
        self._last_result = None                         # последний результат («Copy all»)

        # Состояния анимаций/потоков
        self._phase = 0.0              # глобальное «время» анимации
        self._anim_job = None          # id кадра фона
        self._reveal_job = None        # id отложенного блока результата
        self._reveal_index = 0         # сколько блоков уже «проявлено»
        self._spinner_dots = 0         # счётчик спиннера статуса
        self._busy = False             # идёт ли генерация
        self._worker = None            # ссылка на фоновый поток
        self._closing = False          # флаг корректного завершения

        # Выбор лучших доступных шрифтов системы
        family = _pick_font(["Segoe UI Variable Display", "Segoe UI", "Helvetica"])
        mono = _pick_font(["Cascadia Mono", "Consolas", "Courier New"])
        self._f_title = (family, 19, "bold")     # крупный заголовок
        self._f_head = (family, 11, "bold")      # заголовки секций
        self._f_body = (family, 10)              # основной текст
        self._f_small = (family, 8)              # мелкие подписи
        self._f_mono = (mono, 10)                # сами дорки

        # Оформление окна
        self.title("dorkAI — AI Google Dorks Generator")
        self.configure(bg=_hex(_SP1))
        self.geometry("840x700")
        self.minsize(720, 580)

        # Слои: сначала ФОН (остаётся внизу), затем контент поверх
        self._build_cosmos()
        self._build_header()
        self._build_input_area()
        self._build_results()

        self._refresh_key_status()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ============================ КОСМИЧЕСКИЙ ФОН ================================

    def _build_cosmos(self) -> None:
        """Canvas-фон: линии градиента + звёзды + запуск цикла кадров."""
        self._cosmos = tk.Canvas(self, bg=_hex(_SP1), highlightthickness=0, bd=0)
        self._cosmos.place(relx=0, rely=0, relwidth=1, relheight=1)
        # Canvas создан ПЕРВЫМ, поэтому уже в самом низу стек-порядка:
        # явный .lower() здесь не нужен и конфликтует с Canvas.lower(tagOrId).
        self._stars = []                        # [(id, rgb, speed, phase), ...]
        self._grad_rows = []                    # [(id, нормированная_высота), ...]
        self._rebuild_geometry()                # первая отрисовка геометрии
        self._tick_cosmos()                     # старт бесконечной анимации

    def _rebuild_geometry(self) -> None:
        """Перестраивает градиентные линии и звёзды под текущий размер окна."""
        if self._closing:
            return                              # при закрытии ничего не рисуем
        w, h = self._cosmos.winfo_width(), self._cosmos.winfo_height()
        if w < 50 or h < 50:                    # размеров ещё нет — выходим
            return
        self._cosmos.delete("all")              # очищаем прошлые примитивы
        self._grad_rows, self._stars = [], []
        # Градиент: горизонтальные линии шагом 4 px; кадры лишь ПЕРЕКРАШИВАЮТ их
        y = 0
        while y <= h + 4:
            row_id = self._cosmos.create_line(0, y, w, y + 0.5, width=4, tags=("grad",))
            self._grad_rows.append((row_id, y / h))    # запоминаем высоту 0..1
            y += 4
        # Звёзды: плотность зависит от ширины, у каждой — своя скорость/фаза
        count = min(130, max(45, w // 9))
        for _i in range(count):
            sx = random.uniform(0, w)
            sy = random.uniform(0, h * 0.97)
            r = random.choice((1, 1, 1, 2))            # большинство — точки
            sid = self._cosmos.create_oval(sx, sy, sx + r, sy + r, outline="", width=0)
            base = random.choice(_STAR_RGBS)
            speed = random.uniform(0.5, 1.7)           # индивидуальная частота
            phase = random.uniform(0, 2 * math.pi)     # несинхронное мерцание
            self._stars.append((sid, base, speed, phase))

    def _space_color(self, fy: float) -> str:
        """Цвет неба на высоте fy (0..1) с учётом времени — само «переливание»."""
        span = (fy * 1.5 + self._phase) % 1.0      # позиция плывёт со временем
        seg = span * 3.0                            # палитра из трёх сегментов
        i = int(seg)                                # текущая пара цветов
        frac = seg - i                              # прогресс внутри пары
        trio = (_SP1, _SP2, _SP3)
        return _hex(_mix(trio[i % 3], trio[(i + 1) % 3], frac))

    def _tick_cosmos(self) -> None:
        """Один кадр: красим небо, мигаем звёздами, пульсируем кнопкой/статусом."""
        if self._closing or not self.winfo_exists():
            return                                  # окно закрывается — стоп
        self._phase += 0.004                        # медленное «дыхание» туманностей
        # Перекраска всех линий градиента
        for row_id, fy in self._grad_rows:
            self._cosmos.itemconfig(row_id, fill=self._space_color(fy))
        # Звёзды: яркость = синус; цвет = смесь локального фона и цвета звезды
        for sid, base, speed, ph in self._stars:
            glow = 0.15 + 0.85 * (0.5 + 0.5 * math.sin(speed * self._phase * 60.0 + ph))
            coords = self._cosmos.coords(sid)       # y звезды — для локального фона
            fy = (coords[1] / max(self._cosmos.winfo_height(), 1)) if len(coords) >= 2 else 0.5
            self._cosmos.itemconfig(sid, fill=_hex(_mix(_unhex(self._space_color(fy)), base, glow)))
        # Мягкая пульсация главной кнопки между двумя оттенками акцента
        if hasattr(self, "_generate_btn"):
            p = 0.5 + 0.5 * math.sin(self._phase * 8.0)
            amp = 0.35 if not self._busy else 0.12  # во время работы пульс тише
            self._generate_btn.config(bg=_hex(_mix(_ACCENT_T, _ACCENT_HI_T, p * amp)))
        # Спиннер статуса: каждые 8 кадров добавляем точку «Генерация…»
        if self._busy:
            self._spinner_dots = (self._spinner_dots + 1) % 4
            self._status.config(text="Consulting the stars" + "." * self._spinner_dots)
        # Планируем следующий кадр (~22 FPS — плавно и дёшево по CPU)
        self._anim_job = self.after(45, self._tick_cosmos)

    # ============================ ПОСТРОЕНИЕ ИНТЕРФЕЙСА ==========================

    def _panel(self, parent=None, **kw) -> tk.Frame:
        # Унифицированная «карточка»: панельный фон + тонкая рамка
        return tk.Frame(parent or self, bg=C_PANEL,
                        highlightbackground=C_BORDER, highlightthickness=1, **kw)

    def _hover(self, widget, normal: str, hover: str) -> None:
        # Привязывает ховер-подсветку к любой плоской кнопке
        widget.bind("<Enter>", lambda _e: widget.config(bg=hover))
        widget.bind("<Leave>", lambda _e: widget.config(bg=normal))

    def _build_header(self) -> None:
        """Шапка: название, статус ключа, кнопка API key."""
        header = tk.Frame(self, bg="", highlightthickness=0)
        header.configure(bg=_hex(_SP1))          # прозрачность невозможна — берём тон фона
        header.pack(fill="x", padx=24, pady=(18, 6))

        tk.Label(header, text="dorkAI", bg=header.cget("bg"),
                 fg=C_FG, font=self._f_title).pack(side="left")
        tk.Label(header, text="  ·  AI-powered Google Dorks",
                 bg=header.cget("bg"), fg=C_MUTED, font=self._f_body).pack(side="left", pady=(8, 0))

        key_btn = tk.Button(header, text="API key", command=self._open_key_dialog,
                            bg=C_PANEL, fg=C_FG, activebackground=C_BORDER, activeforeground=C_FG,
                            relief="flat", bd=0, padx=14, pady=6, cursor="hand2", font=self._f_body)
        key_btn.pack(side="right")
        self._hover(key_btn, C_PANEL, C_BORDER)

        # Строка статуса ключа: пульсирующая точка + текст
        status_line = tk.Frame(self, bg=header.cget("bg"))
        status_line.pack(fill="x", padx=24)
        self._dot = tk.Label(status_line, text="●", bg=header.cget("bg"), fg=C_ERR,
                             font=("Segoe UI", 10))
        self._dot.pack(side="left")
        self._key_status = tk.Label(status_line, text="", bg=header.cget("bg"),
                                    fg=C_MUTED, font=self._f_small)
        self._key_status.pack(side="left", padx=(6, 0))

        tk.Frame(self, bg=C_BORDER, height=1).place(x=24, rely=0, y=92, relwidth=1, bordermode="outside")

    def _build_input_area(self) -> None:
        """Блок ввода темы исследования."""
        area = tk.Frame(self, bg=_hex(_SP1))
        area.pack(fill="x", padx=24, pady=(20, 0))

        tk.Label(area, text="RESEARCH TOPIC", bg=area.cget("bg"),
                 fg=C_MUTED, font=self._f_small).pack(anchor="w")

        row = tk.Frame(area, bg=area.cget("bg"))
        row.pack(fill="x", pady=(6, 0))

        # Поле ввода в карточке с рамкой
        card = self._panel(row)
        card.pack(side="left", fill="both", expand=True, padx=(0, 12))
        self._entry = tk.Entry(card, bg=C_PANEL, fg=C_FG, insertbackground=C_FG,
                               relief="flat", font=self._f_mono, bd=0)
        self._entry.pack(fill="both", ipady=9, padx=12)
        # Подсказка-плейсхолдер
        self._placeholder = "e.g., public documents and employee profiles of Company X"
        self._entry.insert(0, self._placeholder)
        self._entry.config(fg=C_MUTED)
        self._entry.bind("<FocusIn>", self._clear_placeholder)
        self._entry.bind("<FocusOut>", self._restore_placeholder)
        self._entry.bind("<Return>", lambda _e: self._on_generate())

        # Главная акцентная кнопка (цветом управляет анимация)
        self._generate_btn = tk.Button(row, text="Generate", command=self._on_generate,
                                       bg=C_ACCENT, fg="#FFFFFF", activebackground=C_ACCENT_HI,
                                       activeforeground="#FFFFFF", relief="flat", bd=0,
                                       font=self._f_head, padx=22, cursor="hand2")
        self._generate_btn.pack(side="right", fill="y")

        # Динамическая строка статуса (спиннер/ошибки/подтверждения)
        self._status = tk.Label(self, text="", bg=_hex(_SP1),
                                fg=C_MUTED, font=self._f_body, anchor="w")
        self._status.pack(fill="x", padx=24, pady=(8, 0))

    def _build_results(self) -> None:
        """Блок результатов с кнопкой «Copy all»."""
        area = tk.Frame(self, bg=_hex(_SP1))
        area.pack(fill="both", expand=True, padx=24, pady=(14, 20))

        tools = tk.Frame(area, bg=area.cget("bg"))
        tools.pack(fill="x", pady=(0, 6))
        tk.Label(tools, text="RESULTS", bg=area.cget("bg"),
                 fg=C_MUTED, font=self._f_small).pack(side="left")
        copy_all = tk.Button(tools, text="Copy all", command=self._copy_all,
                             bg=C_PANEL, fg=C_FG, activebackground=C_BORDER, activeforeground=C_FG,
                             relief="flat", bd=0, padx=10, pady=4, cursor="hand2", font=self._f_small)
        copy_all.pack(side="right")
        self._hover(copy_all, C_PANEL, C_BORDER)

        # Только для чтения поле с тегами-стилями
        self._output = ScrolledText(area, bg=C_PANEL, fg=C_FG, relief="flat",
                                    wrap="word", font=self._f_body, insertbackground=C_FG,
                                    state="disabled", borderwidth=0,
                                    highlightthickness=1, highlightbackground=C_BORDER)
        self._output.pack(fill="both", expand=True)
        self._output.configure(padx=16, pady=14)

        o = self._output
        o.tag_configure("h1", font=self._f_head, foreground=C_FG, spacing3=10)
        o.tag_configure("num", foreground="#B79CFF", font=self._f_head)
        o.tag_configure("title", foreground=C_FG, font=self._f_body, spacing1=8)
        o.tag_configure("query", foreground=C_QUERY, font=self._f_mono,
                        lmargin1=20, lmargin2=20, spacing1=3)
        o.tag_configure("desc", foreground=C_MUTED, font=self._f_small,
                        lmargin1=20, lmargin2=20, spacing3=6)

    # ============================ СТАТУС КЛЮЧА ====================================

    def _refresh_key_status(self) -> None:
        # Обновляет индикатор наличия API-ключа
        if self._settings.has_api_key:
            masked = self._settings.api_key[:6] + "…"
            self._dot.config(fg=C_OK)
            self._key_status.config(text=f"Provider connected ({masked})")
        else:
            self._dot.config(fg=C_ERR)
            self._key_status.config(text="No API key yet — click 'API key'")

    def _open_key_dialog(self) -> None:
        # Открывает модальный диалог ввода ключа
        ApiKeyDialog(self, self._settings, on_saved=self._refresh_key_status)

    # ============================ PLACEHOLDER =====================================

    def _clear_placeholder(self, _event=None) -> None:
        # При фокусе убираем подсказку
        if self._entry.get() == self._placeholder:
            self._entry.delete(0, "end")
            self._entry.config(fg=C_FG)

    def _restore_placeholder(self, _event=None) -> None:
        # Пустое поле при потере фокуса снова показывает подсказку
        if not self._entry.get():
            self._entry.insert(0, self._placeholder)
            self._entry.config(fg=C_MUTED)

    # ============================ ГЕНЕРАЦИЯ =======================================

    def _on_generate(self) -> None:
        # Обработчик кнопки: валидация + запуск фонового потока
        query = self._entry.get().strip()
        if not query or query == self._placeholder:
            messagebox.showinfo("dorkAI", "Type a research topic first.")
            return
        if not self._settings.has_api_key:
            self._open_key_dialog()
            return
        # Отменяем незавершённую «проявку» предыдущего результата
        self._cancel_reveal()
        self._set_busy(True)
        self._worker = threading.Thread(target=self._worker_run, args=(query,), daemon=True)
        self._worker.start()

    def _worker_run(self, query: str) -> None:
        # Выполняется В ФОНОВОМ ПОТОКЕ: tkinter здесь трогать нельзя
        try:
            result = self._generator.generate(query)
            self.after(0, self._on_success, result)
        except DorkAIError as exc:
            self.after(0, self._on_error, self._localize_error(exc))
        except Exception as exc:  # noqa: BLE001 — последний рубеж защиты GUI
            self.after(0, self._on_error, f"Unexpected error: {exc}")

    @staticmethod
    def _localize_error(exc: DorkAIError) -> str:
        # Перевод доменных ошибок ядра на язык интерфейса
        if isinstance(exc, MissingApiKeyError):
            return "No API key configured — click 'API key'."
        if isinstance(exc, EmptyQueryError):
            return "Type a research topic first."
        if type(exc).__name__ == "ResponseParsingError":
            return "AI replied in an unexpected format — try again."
        return f"Generation failed: {exc}"

    def _alive(self) -> bool:
        # Окно может быть закрыто раньше ответа потока — проверяем существование
        try:
            return bool(self.winfo_exists())
        except tk.TclError:
            return False

    def _on_success(self, result: GenerationResult) -> None:
        # Главный поток: разблокируем UI и показываем результат
        if not self._alive():
            return
        self._set_busy(False)
        self._last_result = result
        self._render_result(result)
        self._status.config(text=f"Done — {len(result.dorks)} dorks in {result.elapsed_seconds}s",
                            fg=C_OK)

    def _on_error(self, message: str) -> None:
        # Главный поток: разблокируем UI и показываем ошибку
        if not self._alive():
            return
        self._set_busy(False)
        self._status.config(text=message, fg=C_ERR)

    # --- Проявка результатов ------------------------------------------------------

    def _render_result(self, result: GenerationResult) -> None:
        """Ставит блоки дорков в очередь плавной «проявки» (fade-in эффект)."""
        self._cancel_reveal()
        self._output.config(state="normal")
        self._output.delete("1.0", "end")
        self._output.insert("end", f"Topic: {result.source_query}\n\n", "h1")
        self._output.config(state="disabled")
        # Готовим список блоков; вставлять будем по одному через after(...)
        self._reveal_blocks = []
        for i, dork in enumerate(result.dorks, start=1):
            self._reveal_blocks.append((i, dork))
        self._reveal_index = 0
        self._reveal_next()

    def _reveal_next(self) -> None:
        # Вставляет следующий блок дорка с задержкой — виден эффект появления
        if self._closing or self._reveal_index >= len(getattr(self, "_reveal_blocks", [])):
            self._reveal_job = None
            return
        i, dork = self._reveal_blocks[self._reveal_index]
        self._output.config(state="normal")
        self._output.insert("end", f"{i:>2}  ", "num")
        self._output.insert("end", f"{dork.title}\n", "title")
        self._output.insert("end", f"{dork.query}\n", "query")
        if dork.description:
            self._output.insert("end", f"{dork.description}\n", "desc")
        # Встроенная кнопка копирования напротив каждого дорка
        btn = tk.Button(self._output, text="copy",
                        command=lambda q=dork.query: self._copy_text(q, f"Copied: {dork.title}"),
                        bg=C_BORDER, fg=C_MUTED, activebackground=C_ACCENT, activeforeground="#FFFFFF",
                        relief="flat", bd=0, font=("Segoe UI", 8), padx=8, pady=1, cursor="hand2")
        self._output.window_create("end", window=btn)
        self._output.insert("end", "\n\n")
        self._output.see(f"insert")               # автопрокрутка за проявкой
        self._output.config(state="disabled")
        self._reveal_index += 1
        self._reveal_job = self.after(90, self._reveal_next)

    def _cancel_reveal(self) -> None:
        # Останавливает «проявку», если она идёт
        if self._reveal_job is not None:
            self.after_cancel(self._reveal_job)
            self._reveal_job = None

    # ============================ БУФЕР ОБМЕНА ====================================

    def _copy_text(self, text: str, ok_message: str) -> None:
        # Универсальное копирование строки в буфер обмена Windows
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status.config(text=ok_message, fg=C_OK)

    def _copy_all(self) -> None:
        # Копирует все дорки нумерованным списком разом
        if not self._last_result:
            self._status.config(text="Nothing to copy yet — generate dorks first.", fg=C_MUTED)
            return
        lines = [f"{i}. {d.query}" for i, d in enumerate(self._last_result.dorks, start=1)]
        self._copy_text("\n".join(lines), "All dorks copied to clipboard")

    # ============================ СЛУЖЕБНОЕ ========================================

    def _set_busy(self, busy: bool) -> None:
        # Включает/выключает «занятой» режим интерфейса
        self._busy = busy
        if busy:
            self._generate_btn.config(state="disabled", text="Working…")
            self._entry.config(state="disabled")
            self._spinner_dots = 0
        else:
            self._generate_btn.config(state="normal", text="Generate")
            self._entry.config(state="normal")

    def _on_close(self) -> None:
        # Аккуратное завершение: глушим анимации, закрываем HTTP, разрушаем окно
        self._closing = True
        if self._anim_job is not None:
            self.after_cancel(self._anim_job)
            self._anim_job = None
        self._cancel_reveal()
        try:
            self._generator.close()
        except Exception:                        # даже если сеть «залипла» — закрываемся
            pass
        self.destroy()


def run_gui(settings: Settings) -> None:
    """Точка входа графического режима."""
    DorkAIApp(settings).mainloop()
