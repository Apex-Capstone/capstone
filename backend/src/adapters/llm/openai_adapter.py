"""OpenAI LLM adapter implementation."""

from typing import Any

from openai import AsyncOpenAI

from config.logging import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


class OpenAIAdapter:
    """Adapter for OpenAI API."""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.openai_api_key
        self.model_id = settings.openai_model_id
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> str:
        """Generate a response using OpenAI."""
        try:
            messages = []
            if context:
                messages.append({"role": "system", "content": context})
            messages.append({"role": "user", "content": prompt})
            
            response = await self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def generate_patient_response(
        self,
        case_script: str,
        conversation_history: list[dict[str, str]],
        current_spikes_stage: str,
    ) -> str:
        """Generate patient response for simulation."""
        system_prompt = f"""You are roleplaying as a PATIENT in a medical simulation. You are NOT an assistant or doctor.

IMPORTANT: You are the PATIENT, not the healthcare provider. Respond as a patient would.

Patient Situation:
{case_script}

Current Stage: {current_spikes_stage}

INSTRUCTIONS:
- You are anxious and concerned about your health
- Respond naturally as this patient character would
- Show realistic emotions: worry, fear, sadness, confusion, hope
- Ask questions a patient would ask
- React emotionally to bad news or concerning information
- Do NOT say things like "How can I help you?" - YOU are the patient seeking help
- Be concise (1-3 sentences typical for a patient response)
- If the doctor hasn't introduced themselves yet, you might be nervous/uncertain
- If receiving bad news, show appropriate emotional reactions

Remember: You are receiving care, not providing it. Respond as the patient character described above."""
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                max_tokens=300,
                temperature=0.8,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI patient response error: {e}")
            raise
    
    async def analyze_turn(
        self,
        user_text: str,
        conversation_history: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Analyze user's communication for metrics."""
        analysis_prompt = f"""Analyze this medical communication for:
1. Empathy level (0-10)
2. Question type (open/closed/mixed)
3. Use of medical jargon (low/medium/high)
4. Clarity (0-10)

User's message: "{user_text}"

Respond in JSON format with keys: empathy_score, question_type, jargon_level, clarity_score"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=200,
                temperature=0.3,
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            logger.error(f"OpenAI analysis error: {e}")
            return {
                "empathy_score": 5,
                "question_type": "unknown",
                "jargon_level": "medium",
                "clarity_score": 5,
            }

