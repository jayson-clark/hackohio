from typing import List, Dict, Optional
import asyncio
from app.config import settings
from app.services.lava_service import LavaService

# Optional LLM imports
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class LLMService:
    """
    Optional LLM-powered relationship extraction and classification
    Enhances basic co-occurrence with semantic understanding
    Routes through Lava Payments for usage-based billing when enabled
    """
    
    def __init__(self):
        self.lava_service = LavaService()
        self.use_lava = self.lava_service.enabled
        
        # Enable LLM if either Lava is enabled OR direct API keys are provided
        self.enabled = settings.enable_llm_extraction or self.use_lava
        
        self.openai_client = None
        self.anthropic_client = None
        
        if self.enabled and not self.use_lava:
            # Only initialize direct clients if NOT using Lava
            if OPENAI_AVAILABLE and settings.openai_api_key:
                self.openai_client = openai.OpenAI(api_key=settings.openai_api_key)
            elif ANTHROPIC_AVAILABLE and settings.anthropic_api_key:
                self.anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    
    async def extract_relationships_from_sentence(
        self,
        sentence: str,
        entities: List[str]
    ) -> List[Dict[str, any]]:
        """
        Use LLM to extract relationships from a sentence
        Returns relationships with semantic labels
        """
        if not self.enabled:
            return []
        
        if not self.use_lava and not (self.openai_client or self.anthropic_client):
            return []
        
        prompt = self._build_extraction_prompt(sentence, entities)
        
        try:
            # Prefer Lava if enabled, otherwise use direct clients
            if self.use_lava:
                return await self._extract_with_openai(prompt)
            elif self.openai_client:
                return await self._extract_with_openai(prompt)
            elif self.anthropic_client:
                return await self._extract_with_anthropic(prompt)
        except Exception as e:
            print(f"LLM extraction failed: {e}")
            return []
        
        return []
    
    def _build_extraction_prompt(self, sentence: str, entities: List[str]) -> str:
        """Build prompt for relationship extraction"""
        entities_str = ", ".join(entities)
        
        prompt = f"""Given the following biomedical sentence and entities, extract relationships between the entities.

Sentence: {sentence}

Entities: {entities_str}

For each relationship found, provide:
1. Source entity
2. Target entity
3. Relationship type (e.g., INHIBITS, ACTIVATES, TREATS, CAUSES, ASSOCIATES_WITH)
4. Confidence (0.0 to 1.0)

Return as JSON array:
[{{"source": "...", "target": "...", "type": "...", "confidence": 0.9}}]

If no clear relationships exist, return an empty array.
"""
        return prompt
    
    async def _extract_with_openai(self, prompt: str) -> List[Dict[str, any]]:
        """Extract using OpenAI GPT (via Lava if enabled)"""
        try:
            messages = [
                {"role": "system", "content": "You are a biomedical relationship extraction expert."},
                {"role": "user", "content": prompt}
            ]
            
            if self.use_lava:
                # Route through Lava for usage tracking
                response_data = await self.lava_service.forward_openai_request(
                    messages=messages,
                    model="gpt-4-turbo-preview",
                    temperature=0.3,
                    response_format={"type": "json_object"},
                    metadata={
                        "service": "synapse_mapper",
                        "task": "relationship_extraction"
                    }
                )
                # Extract content from Lava response
                import json
                result = json.loads(response_data['data']['choices'][0]['message']['content'])
                return result.get("relationships", [])
            else:
                # Direct OpenAI call
                response = await asyncio.to_thread(
                    self.openai_client.chat.completions.create,
                    model="gpt-4-turbo-preview",
                    messages=messages,
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                import json
                result = json.loads(response.choices[0].message.content)
                return result.get("relationships", [])
        except Exception as e:
            print(f"OpenAI extraction error: {e}")
            return []
    
    async def _extract_with_anthropic(self, prompt: str) -> List[Dict[str, any]]:
        """Extract using Anthropic Claude (via Lava if enabled)"""
        try:
            messages = [{"role": "user", "content": prompt}]
            
            if self.use_lava:
                # Route through Lava for usage tracking
                response_data = await self.lava_service.forward_anthropic_request(
                    messages=messages,
                    model="claude-3-sonnet-20240229",
                    max_tokens=1024,
                    temperature=0.3,
                    metadata={
                        "service": "synapse_mapper",
                        "task": "relationship_extraction"
                    }
                )
                # Extract content from Lava response
                import json
                result = json.loads(response_data['data']['content'][0]['text'])
                return result if isinstance(result, list) else result.get("relationships", [])
            else:
                # Direct Anthropic call
                response = await asyncio.to_thread(
                    self.anthropic_client.messages.create,
                    model="claude-3-sonnet-20240229",
                    max_tokens=1024,
                    messages=messages
                )
                
                import json
                result = json.loads(response.content[0].text)
                return result if isinstance(result, list) else result.get("relationships", [])
        except Exception as e:
            print(f"Anthropic extraction error: {e}")
            return []
    
    async def classify_relationship(
        self,
        source: str,
        target: str,
        evidence: str
    ) -> Optional[str]:
        """
        Classify a relationship between two entities
        Returns semantic relationship type
        """
        if not self.enabled:
            return None
        
        if not self.use_lava and not (self.openai_client or self.anthropic_client):
            return None
        
        prompt = f"""Classify the relationship between these two biomedical entities based on the evidence.

Source Entity: {source}
Target Entity: {target}
Evidence: {evidence}

Choose ONE of these relationship types:
- INHIBITS
- ACTIVATES
- TREATS
- CAUSES
- ASSOCIATES_WITH
- BINDS_TO
- REGULATES
- EXPRESSED_IN
- UNKNOWN

Return only the relationship type, nothing else.
"""
        
        try:
            messages = [{"role": "user", "content": prompt}]
            
            # Prefer Lava, then fall back to direct clients
            if self.use_lava:
                # Route through Lava (defaults to OpenAI)
                response_data = await self.lava_service.forward_openai_request(
                    messages=messages,
                    model="gpt-3.5-turbo",
                    temperature=0.1,
                    max_tokens=20,
                    metadata={
                        "service": "synapse_mapper",
                        "task": "relationship_classification"
                    }
                )
                return response_data['data']['choices'][0]['message']['content'].strip()
            elif self.openai_client:
                # Direct OpenAI call
                response = await asyncio.to_thread(
                    self.openai_client.chat.completions.create,
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.1,
                    max_tokens=20
                )
                return response.choices[0].message.content.strip()
            elif self.anthropic_client:
                # Direct Anthropic call
                response = await asyncio.to_thread(
                    self.anthropic_client.messages.create,
                    model="claude-3-haiku-20240307",
                    max_tokens=20,
                    messages=messages
                )
                return response.content[0].text.strip()
        except Exception as e:
            print(f"LLM classification failed: {e}")
            return None
        
        return None

