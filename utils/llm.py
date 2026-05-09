import os
import time
import logging
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"

_client = None


def get_client() -> InferenceClient:
    global _client
    if _client is None:
        token = os.getenv("HUGGING_FACE_TOKEN")
        if not token:
            raise EnvironmentError("HUGGING_FACE_TOKEN not set in .env")
        _client = InferenceClient(token=token)
    return _client


def call_llm(prompt: str, model: str = DEFAULT_MODEL, max_retries: int = 3) -> str:
    client = get_client()

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower():
                wait = 10 * (2 ** attempt)
                logger.warning(f"Rate limit, retrying in {wait}s...")
                time.sleep(wait)
                continue
            if "503" in error_str or "loading" in error_str.lower():
                logger.warning("Model loading, waiting 20s...")
                time.sleep(20)
                continue
            logger.error(f"LLM call failed: {e}")
            raise

    raise RuntimeError(f"LLM call failed after {max_retries} retries.")