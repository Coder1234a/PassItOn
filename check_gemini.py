"""Quick check that Gemini mode works. Run:  python check_gemini.py

Reads the key from .streamlit/secrets.toml (or the GEMINI_API_KEY environment variable),
makes one real call through the Ask agent, and prints whether the AI path was used.
"""
import os
import tomllib
from pathlib import Path

from agents.orchestrator import Orchestrator


def load_key():
    # Put the key from secrets.toml into the environment so llm.py can find it outside Streamlit.
    path = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"
    if path.exists():
        secrets = tomllib.loads(path.read_text(encoding="utf-8"))
        for name in ("GEMINI_API_KEY", "GEMINI_MODEL"):
            if secrets.get(name):
                os.environ.setdefault(name, secrets[name])


load_key()
orc = Orchestrator()
print("AI online:", orc.llm.online, "| model:", orc.llm.model)
if not orc.llm.online:
    print("Problem:", orc.llm.last_error)
else:
    for q in ["DSA CAT is tomorrow and recursion confuses me", "how do I get a hostel room change"]:
        r = orc.handle_question(q)
        a = r["answer"]
        print("\nQ:", q)
        print("  answered by:", a["source"], "| confident:", a["confident"])
        print("  answer:", a["text"])
    print("\nGemini calls made:", orc.llm.calls, "| last error:", orc.llm.last_error)
