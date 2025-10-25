import base64
import json
from typing import Dict, Any, Optional, List
import httpx
from app.config import settings


class LavaService:
    """
    Lava Payments integration for usage-based billing of AI API calls
    Routes LLM requests through Lava's forward endpoint for automatic metering
    """
    
    BASE_URL = "https://api.lavapayments.com/v1"
    
    def __init__(self):
        self.enabled = settings.enable_lava and settings.lava_secret_key
        self.secret_key = settings.lava_secret_key
        self.connection_secret = settings.lava_connection_secret
        self.product_secret = settings.lava_product_secret
        
    def _get_auth_token(self) -> str:
        """
        Create base64-encoded authentication token for Lava forward endpoint
        Format: base64({"secret_key": "...", "connection_secret": "...", "product_secret": "..."})
        """
        auth_payload = {
            "secret_key": self.secret_key,
            "connection_secret": self.connection_secret,
        }
        
        if self.product_secret:
            auth_payload["product_secret"] = self.product_secret
            
        json_str = json.dumps(auth_payload)
        encoded = base64.b64encode(json_str.encode()).decode()
        return encoded
    
    async def forward_openai_request(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Forward OpenAI API request through Lava
        """
        if not self.enabled:
            raise ValueError("Lava service is not enabled")
            
        # Build OpenAI-compatible request body
        request_body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            request_body["max_tokens"] = max_tokens
        if response_format:
            request_body["response_format"] = response_format
            
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {self._get_auth_token()}",
            "Content-Type": "application/json"
        }
        
        # Add metadata if provided
        if metadata:
            headers["x-lava-metadata"] = json.dumps(metadata)
        
        # Forward to Lava
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/forward",
                json=request_body,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    async def forward_anthropic_request(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-3-sonnet-20240229",
        max_tokens: int = 1024,
        temperature: float = 0.3,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Forward Anthropic API request through Lava
        """
        if not self.enabled:
            raise ValueError("Lava service is not enabled")
            
        # Build Anthropic-compatible request body
        request_body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
            
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {self._get_auth_token()}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # Add metadata if provided
        if metadata:
            headers["x-lava-metadata"] = json.dumps(metadata)
        
        # Forward to Lava
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/forward",
                json=request_body,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics from Lava
        """
        if not self.enabled:
            raise ValueError("Lava service is not enabled")
            
        headers = {
            "Authorization": f"Bearer {self.secret_key}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/usage",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    async def list_requests(
        self,
        limit: int = 50,
        cursor: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        List API requests tracked by Lava
        """
        if not self.enabled:
            raise ValueError("Lava service is not enabled")
            
        headers = {
            "Authorization": f"Bearer {self.secret_key}"
        }
        
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        if metadata:
            params["metadata"] = json.dumps(metadata)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/requests",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()

