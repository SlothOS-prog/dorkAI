"""
cli.py — console shell (proof that the backend works without the GUI).

Run:  python main.py --cli
All comments stay in Russian (project convention); all user-facing text is English.
"""

# sys.exit for graceful exits
import sys

# Core imports of the dorkAI package
from .config import Settings
from .dork_generator import DorkGenerator
from .exceptions import DorkAIError

# ANSI colors for a minimal, tasteful terminal look
_C_RESET = "\033[0m"   # reset to default color
_C_DIM = "\033[2m"     # dim gray — secondary text
_C_CYAN = "\033[36m"   # cyan — accents and headers
_C_GREEN = "\033[32m"  # green — the dorks themselves


def _print_result(result) -> None:
    # Pretty-print a GenerationResult into the terminal
    print()
    print(f"{_C_CYAN}Topic:{_C_RESET} {result.source_query}")
    print(f"{_C_DIM}Dorks: {len(result.dorks)} | elapsed: {result.elapsed_seconds}s{_C_RESET}")
    print("-" * 60)
    for i, dork in enumerate(result.dorks, start=1):
        # Number and technique title
        print(f"{_C_CYAN}{i:>2}. {dork.title}{_C_RESET}")
        # The dork itself in green — this is what users copy into Google
        print(f"    {_C_GREEN}{dork.query}{_C_RESET}")
        # Explanation in dim gray (when provided by the model)
        if dork.description:
            print(f"    {_C_DIM}{dork.description}{_C_RESET}")
        # Blank separator line between dorks
        print()


def run_console() -> int:
    """
    Main loop of the console mode.

    Returns:
        Process exit code for main() (0 = success).
    """
    # Application banner
    print(f"dorkAI {_C_DIM}(console mode){_C_RESET} — Google Dorks via AI")

    # Build settings once (reads environment variables and the .env file)
    settings = Settings()

    # If no key is present, offer a one-shot paste right here
    if not settings.has_api_key:
        print(f"{_C_DIM}No API key found (env DORKAI_API_KEY or the .env file).{_C_RESET}")
        key = input("Paste your API key and press Enter: ").strip()
        if not settings.save_api_key(key):
            # Could not persist the key (disk permissions) — exit with error
            print("Could not save the key to .env")
            return 1
        print("Key saved to .env\n")

    # Build the generation service on top of the settings
    generator = DorkGenerator(settings)

    try:
        # Main REPL: read a topic -> print generated dorks
        while True:
            try:
                query = input("\nResearch topic (q to quit): ").strip()
            except EOFError:
                # stdin closed — finish gracefully
                break
            # Exit commands
            if query.lower() in {"q", "quit", "exit"}:
                break
            # Empty input — just ask again
            if not query:
                continue
            try:
                # Full path through the core: query -> AI -> JSON -> Dork objects
                result = generator.generate(query)
                _print_result(result)
            except DorkAIError as exc:
                # Domain errors are printed plainly, without tracebacks
                print(f"Error: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        # Ctrl+C — soft exit
        pass
    finally:
        # Release HTTP resources no matter what
        generator.close()

    return 0
