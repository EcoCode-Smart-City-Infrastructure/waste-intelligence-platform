"""
OpenRouter client for AI Copilot Service.

Provides integration with OpenRouter API for LLM inference.
Uses the free API endpoints as specified.
"""

import httpx
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Client for OpenRouter API."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize OpenRouter client."""
        settings = get_settings()
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = base_url or settings.openrouter_base_url
        self.timeout = settings.openrouter_timeout
        
        # Remove any leading/trailing whitespace from API key
        self.api_key = self.api_key.strip() if self.api_key else None
        
        # Initialize HTTP client
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=self._get_headers()
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 0.9,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to OpenRouter.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model identifier (defaults to settings default)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            stream: Whether to stream the response
        
        Returns:
            Response dictionary with 'choices' containing generated content
        """
        settings = get_settings()
        model = model or settings.openrouter_default_model
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if stream:
            payload["stream"] = True
        
        try:
            logger.debug(f"Sending request to OpenRouter: model={model}, messages_count={len(messages)}")
            
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Received response from OpenRouter: choices={len(data.get('choices', []))}")
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter HTTP error: {e.response.status_code} - {e.response.text}")
            raise OpenRouterError(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"OpenRouter request error: {str(e)}")
            raise OpenRouterError(f"Request error: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"OpenRouter response parse error: {str(e)}")
            raise OpenRouterError(f"Response parse error: {str(e)}")
    
    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 0.9
    ):
        """
        Stream a chat completion request to OpenRouter.
        
        Args:
            messages: List of message dictionaries
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
        
        Yields:
            Chunks of the streaming response
        """
        settings = get_settings()
        model = model or settings.openrouter_default_model
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        try:
            async with self._client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line:
                        line = line.strip()
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                yield data
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse streaming chunk: {line}")
                                continue
        
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter streaming HTTP error: {e.response.status_code}")
            raise OpenRouterError(f"Streaming HTTP error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"OpenRouter streaming request error: {str(e)}")
            raise OpenRouterError(f"Streaming request error: {str(e)}")
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models from OpenRouter."""
        try:
            response = await self._client.get(
                f"{self.base_url}/models"
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to list models: {e.response.status_code}")
            return []
    
    async def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model."""
        try:
            response = await self._client.get(
                f"{self.base_url}/models/{model_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get model {model_id}: {e.response.status_code}")
            return None
    
    def select_model_by_task(self, task_type: str) -> str:
        """
        Select a model based on task type.
        
        Args:
            task_type: Type of task (real_time, planning, routine, debug, etc.)
        
        Returns:
            Model identifier string
        """
        settings = get_settings()
        return settings.model_by_task.get(task_type, settings.openrouter_default_model)


class OpenRouterError(Exception):
    """Exception raised for OpenRouter API errors."""
    pass


# Global client instance (lazy initialized)
_client: Optional[OpenRouterClient] = None


def get_openrouter_client() -> OpenRouterClient:
    """Get or create the global OpenRouter client."""
    global _client
    if _client is None:
        _client = OpenRouterClient()
    return _client


async def close_openrouter_client():
    """Close the global OpenRouter client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
