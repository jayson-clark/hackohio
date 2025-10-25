from typing import List, Dict, Optional
import asyncio
from app.config import settings

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
    """
    
    def __init__(self):
        self.enabled = settings.enable_llm_extraction
        self.openai_client = None
        self.anthropic_client = None
        
        if self.enabled:
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
        if not self.enabled or not (self.openai_client or self.anthropic_client):
            return []
        
        prompt = self._build_extraction_prompt(sentence, entities)
        
        try:
            if self.openai_client:
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
        """Extract using OpenAI GPT"""
        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a biomedical relationship extraction expert."},
                    {"role": "user", "content": prompt}
                ],
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
        """Extract using Anthropic Claude"""
        try:
            response = await asyncio.to_thread(
                self.anthropic_client.messages.create,
                model="claude-3-sonnet-20240229",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
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
        if not self.enabled or not (self.openai_client or self.anthropic_client):
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
            if self.openai_client:
                response = await asyncio.to_thread(
                    self.openai_client.chat.completions.create,
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=20
                )
                return response.choices[0].message.content.strip()
            elif self.anthropic_client:
                response = await asyncio.to_thread(
                    self.anthropic_client.messages.create,
                    model="claude-3-haiku-20240307",
                    max_tokens=20,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text.strip()
        except Exception as e:
            print(f"LLM classification failed: {e}")
            return None
        
        return None

