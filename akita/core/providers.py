from abc import ABC, abstractmethod
from typing import List, Optional
import requests
from pydantic import BaseModel

class ModelInfo(BaseModel):
    id: str
    name: Optional[str] = None

class BaseProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def validate_key(self, api_key: str) -> bool:
        pass

    @abstractmethod
    def list_models(self, api_key: str) -> List[ModelInfo]:
        pass

class OpenAIProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "openai"

    def validate_key(self, api_key: str) -> bool:
        if not api_key.startswith("sk-"):
            return False
        # Simple validation request
        try:
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self, api_key: str) -> List[ModelInfo]:
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        exclude_keywords = ["vision", "instruct", "audio", "realtime", "tts", "dall-e", "embedding", "moderation", "davinci", "babbage", "curie", "ada"]
        
        models = []
        for m in data["data"]:
            model_id = m["id"]
            if not any(kw in model_id.lower() for kw in exclude_keywords):
                if model_id.startswith("gpt-") or model_id.startswith("o1") or model_id.startswith("o3"):
                    models.append(ModelInfo(id=model_id))
        return sorted(models, key=lambda x: x.id)

class AnthropicProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "anthropic"

    def validate_key(self, api_key: str) -> bool:
        if not api_key.startswith("sk-ant-"):
            return False
        # Anthropic validation usually requires a full request, but we'll check prefix for now
        # or do a no-op call if possible.
        return True

    def list_models(self, api_key: str) -> List[ModelInfo]:
        # Anthropic doesn't have a public models list API like OpenAI
        return [
            ModelInfo(id="claude-3-5-sonnet-latest", name="Claude 3.5 Sonnet (Latest)"),
            ModelInfo(id="claude-3-5-haiku-latest", name="Claude 3.5 Haiku (Latest)"),
            ModelInfo(id="claude-3-opus-20240229", name="Claude 3 Opus"),
            ModelInfo(id="claude-3-sonnet-20240229", name="Claude 3 Sonnet"),
            ModelInfo(id="claude-3-haiku-20240307", name="Claude 3 Haiku"),
        ]

class OllamaProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "ollama"

    def validate_key(self, api_key: str) -> bool:
        # Ollama doesn't use keys by default, we just check if it's reachable
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self, api_key: str) -> List[ModelInfo]:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
        return [ModelInfo(id=m["name"]) for m in data["models"]]

class GeminiProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "gemini"

    def validate_key(self, api_key: str) -> bool:
        if not api_key.startswith("AIza"):
            return False
        return True

    def list_models(self, api_key: str) -> List[ModelInfo]:
        # Gemini API URL for listing models
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        exclude_keywords = ["nano", "banana", "vision", "embedding", "aqa", "learnlm"]
        
        models = []
        for m in data["models"]:
            model_id = m["name"].split("/")[-1]
            display_name = m["displayName"]
            
            # Check if it supports generation and doesn't have excluded keywords
            if "generateContent" in m["supportedGenerationMethods"]:
                if not any(kw in model_id.lower() or kw in display_name.lower() for kw in exclude_keywords):
                    models.append(ModelInfo(id=model_id, name=display_name))
        
        return models

class GroqProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "groq"

    def validate_key(self, api_key: str) -> bool:
        if not api_key.startswith("gsk_"):
            return False
        return True

    def list_models(self, api_key: str) -> List[ModelInfo]:
        # Groq uses OpenAI-compatible models endpoint
        response = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        # Filter for text models
        exclude_keywords = ["vision", "audio"]
        models = []
        for m in data["data"]:
            model_id = m["id"]
            if not any(kw in model_id.lower() for kw in exclude_keywords):
                models.append(ModelInfo(id=model_id))
        return sorted(models, key=lambda x: x.id)

def detect_provider(api_key: str) -> Optional[BaseProvider]:
    """
    Attempts to detect the provider based on the API key or environment.
    """
    if api_key.lower() == "ollama":
        return OllamaProvider()
    
    if api_key.startswith("sk-ant-"):
        return AnthropicProvider()
    
    if api_key.startswith("gsk_"):
        return GroqProvider()
    
    if api_key.startswith("sk-"):
        return OpenAIProvider()
    
    if api_key.startswith("AIza"):
        return GeminiProvider()
        
    return None
