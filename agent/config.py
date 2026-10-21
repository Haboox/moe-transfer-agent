"""Settings, read from the .env file (copy .env.example to .env and edit it).

Switching the AI model is a settings change only:
  LLM_PROVIDER=ollama     -> local model on this computer (free, default)
  LLM_PROVIDER=anthropic  -> Claude API (needs ANTHROPIC_API_KEY)
  LLM_PROVIDER=hosted     -> a hosted model behind the OpenAI style API, for example Groq or Google Gemini
                             (HOSTED_URL, HOSTED_MODEL, HOSTED_API_KEY); used by the online copy (plan B)
  LLM_PROVIDER=scripted   -> no AI at all; a fixed rule-following planner used for repeatable tests
"""
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data" / "synthetic"
LOG_DIR = Path(os.getenv("MOE_LOG_DIR") or ROOT / "logs")              # tests point these to a temporary folder
RUNTIME_DIR = Path(os.getenv("MOE_RUNTIME_DIR") or ROOT / "runtime")

# Fixed by the service card (Card: Fees).
SERVICE_FEE_AED = 50
SERVICE_NAME = "Request for Equivalency Certificate for a Class Transfer from Outside the UAE"
SERVICE_CARD_URL = "https://moe.gov.ae/en/eservices/servicecard/Pages/CertEquivalentMove.aspx"
GRADE12_SERVICE_URL = "https://moe.gov.ae/en/eservices/servicecard/Pages/CertEquivalent-Out.aspx"
GRADE12_SERVICE_URL_AR = "https://moe.gov.ae/ar/eservices/servicecard/Pages/CertEquivalent-Out.aspx"
SERVICE_CARD_URL_AR = "https://moe.gov.ae/ar/eservices/servicecard/Pages/CertEquivalentMove.aspx"
MOE_SUPPORT_NUMBER = "80051115"


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    ollama_url: str
    ollama_model: str
    ollama_think: bool
    ollama_num_ctx: int
    anthropic_api_key: str
    anthropic_model: str
    llm_timeout_seconds: int
    max_tool_steps: int
    tool_max_retries: int
    tool_timeout_seconds: float
    mock_latency_seconds: float
    mock_hang_seconds: float
    application_date: date
    chat_max_chars: int = 600               # longest typed message accepted
    hosted_api_key: str = ""
    hosted_url: str = "https://api.groq.com/openai/v1"
    hosted_model: str = "openai/gpt-oss-120b"
    hosted_reasoning: str = ""              # sent as reasoning_effort when set (depends on the model)
    hosted_context: int = 131072
    hosted_fallback: tuple = ()             # other models to use when the main one's allowance is used up


def get_settings() -> Settings:
    app_date = os.getenv("APPLICATION_DATE", "").strip()
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "ollama").strip().lower(),
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434").strip(),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:8b").strip(),
        ollama_think=os.getenv("OLLAMA_THINK", "false").strip().lower() == "true",
        ollama_num_ctx=int(os.getenv("OLLAMA_NUM_CTX", "8192")),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5").strip(),
        llm_timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "180")),
        max_tool_steps=int(os.getenv("MAX_TOOL_STEPS", "10")),
        tool_max_retries=int(os.getenv("TOOL_MAX_RETRIES", "1")),
        tool_timeout_seconds=float(os.getenv("TOOL_TIMEOUT_SECONDS", "3")),
        mock_latency_seconds=float(os.getenv("MOCK_LATENCY_SECONDS", "0.3")),
        mock_hang_seconds=float(os.getenv("MOCK_HANG_SECONDS", "6")),
        application_date=date.fromisoformat(app_date) if app_date else date.today(),
        chat_max_chars=int(os.getenv("CHAT_MAX_CHARS", "600")),
        hosted_api_key=(os.getenv("HOSTED_API_KEY") or os.getenv("GROQ_API_KEY") or "").strip(),
        hosted_url=os.getenv("HOSTED_URL", "https://api.groq.com/openai/v1").strip(),
        hosted_model=os.getenv("HOSTED_MODEL", "openai/gpt-oss-120b").strip(),
        hosted_reasoning=os.getenv("HOSTED_REASONING", "").strip().lower(),
        hosted_context=int(os.getenv("HOSTED_CONTEXT", "131072")),
        hosted_fallback=tuple(m.strip() for m in os.getenv("HOSTED_FALLBACK_MODELS", "openai/gpt-oss-20b").split(",")
                              if m.strip()),
    )
