# dorkAI

**AI-powered Google Dorks generator for legitimate OSINT research.**

Describe *what* you want to research — dorkAI asks an LLM to craft ready-to-use
Google Dork queries (`site:`, `filetype:`, `intitle:`, `before:` …) and returns
them as a clean, copyable list. Dark cosmic UI, English interface, works on
Windows out of the box.

```
┌──────────────────────────────────────────────┐
│  dorkAI · AI-powered Google Dorks            │
│  Topic: [ public PDFs of University X     ]  │
│                                    [Generate]│
│  RESULTS                                     │
│   1  Open site PDFs                          │
│      site:university-x.edu filetype:pdf  copy│
└──────────────────────────────────────────────┘
```

## Quick start (no Python needed)

1. Download `dorkAI.exe` from the [latest release](../../releases/latest);
2. Run it (SmartScreen note: unsigned binary → *More info → Run anyway*);
3. Click **API key** → paste your key → **Save**;
4. Type a research topic → **Generate**.

> The key is stored locally in a `.env` file next to the exe — it is never
> hardcoded or sent anywhere except your chosen AI provider.

## Run from source

Requires Python 3.10+.

```bash
git clone https://github.com/SlothOS-prog/dorkAI.git
cd dorkAI
python -m pip install -r requirements.txt
python main.py        # GUI
python main.py --cli  # terminal mode
```

## Configuration (all optional)

Everything is configured through environment variables or the `.env` file
(see [.env.example](.env.example)). Any OpenAI-compatible provider works.

| Variable          | Default                              | Description                     |
|-------------------|--------------------------------------|---------------------------------|
| `DORKAI_API_KEY`  | *(empty)*                            | Provider API key                |
| `DORKAI_BASE_URL` | `https://api.groq.com/openai/v1`     | OpenAI-compatible base URL      |
| `DORKAI_MODEL`    | `llama-3.3-70b-versatile`            | Model name                      |
| `DORKAI_TIMEOUT`  | `30`                                 | Request timeout, seconds        |
| `DORKAI_MAX_DORKS`| `10`                                 | Max dorks per generation        |
| `DORKAI_JSON_MODE`| `1`                                  | Ask provider for strict JSON    |

## Architecture

```
user query ──► prompts.py (system prompt + few-shot)
                    │
                    ▼
             ai_client.py  (httpx, retries, timeouts)
                    │ raw text
                    ▼
           dork_generator.py  (JSON extraction + validation)
                    │ tuple[Dork]
                    ▼
             gui.py / cli.py  (thin shells over one core)
```

The backend never touches the API surface of the shells — swap tkinter for a
web frontend without touching the core.

## Legal & ethics

dorkAI only composes **passive, public-source search queries** (classic OSINT).
It does not access private systems, bypass authentication or perform any
intrusive actions. You are responsible for using it in compliance with local
laws and Google's ToS.

## License

[MIT](LICENSE)
