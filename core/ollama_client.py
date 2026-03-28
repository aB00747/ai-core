import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout

    async def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        """Generate a response from Ollama."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "system": system,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": 2048,
                        },
                    },
                )
                response.raise_for_status()
                return response.json().get("response", "")
        except httpx.TimeoutException:
            logger.error("Ollama request timed out")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code}")
            raise
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama")
            raise

    async def chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        """Chat with Ollama using message history."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": 2048,
                        },
                    },
                )
                response.raise_for_status()
                return response.json().get("message", {}).get("content", "")
        except httpx.TimeoutException:
            logger.error("Ollama chat request timed out")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama chat HTTP error: {e.response.status_code}")
            raise
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama")
            raise

    async def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    return any(self.model in name for name in model_names)
            return False
        except Exception:
            return False


ollama_client = OllamaClient()
