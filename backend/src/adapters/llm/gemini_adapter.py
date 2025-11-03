"""Google Gemini LLM adapter implementation."""

from typing import Any

import google.generativeai as genai

from config.logging import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


class GeminiAdapter:
    """Adapter for Google Gemini API."""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.gemini_api_key
        self.model_id = settings.gemini_model_id
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_id)
    
    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> str:
        """Generate a response using Gemini."""
        try:
            full_prompt = f"{context}\n\n{prompt}" if context else prompt
            
            generation_config = {
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }
            
            response = await self.model.generate_content_async(
                full_prompt,
                generation_config=generation_config,
            )
            
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    async def generate_patient_response(
        self,
        case_script: str,
        conversation_history: list[dict[str, str]],
        current_spikes_stage: str,
    ) -> str:
        """Generate patient response for simulation."""
        system_prompt = f"""You are playing the role of a patient in a medical simulation.
        
Case Background:
{case_script}

Current SPIKES Stage: {current_spikes_stage}

Respond naturally as this patient would. Be realistic and emotionally appropriate.
Show appropriate emotional responses based on the conversation stage."""
        
        # Format conversation history
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in conversation_history
        ])
        
        full_prompt = f"{system_prompt}\n\nConversation so far:\n{history_text}\n\nPatient's response:"
        
        try:
            response = await self.model.generate_content_async(
                full_prompt,
                generation_config={"max_output_tokens": 300, "temperature": 0.8},
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini patient response error: {e}")
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
            response = await self.model.generate_content_async(
                analysis_prompt,
                generation_config={"max_output_tokens": 200, "temperature": 0.3},
            )
            
            import json
            result = json.loads(response.text)
            return result
        except Exception as e:
            logger.error(f"Gemini analysis error: {e}")
            return {
                "empathy_score": 5,
                "question_type": "unknown",
                "jargon_level": "medium",
                "clarity_score": 5,
            }

