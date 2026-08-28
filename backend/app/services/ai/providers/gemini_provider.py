import json
import re
import requests
from typing import Any, Dict
from app.services.ai.base import BaseAiProvider

FALLBACK_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
]

class GeminiAiProvider(BaseAiProvider):
    """Google Gemini AI Provider implementation using robust REST API calls."""

    def __init__(self, api_key: str):
        self.api_key = api_key.strip()

    def generate_diagnosis(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "gemini-3.1-flash-lite",
        timeout: int = 30
    ) -> Dict[str, Any]:
        # Models to try in order (requested model first, then fallbacks if 503/404)
        models_to_try = [model]
        for fb in FALLBACK_MODELS:
            if fb not in models_to_try:
                models_to_try.append(fb)

        last_error = None

        for current_model in models_to_try:
            # Clean model name (remove 'models/' prefix if present)
            clean_model_name = current_model.replace("models/", "").strip()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={self.api_key}"

            payload = {
                "system_instruction": {
                    "parts": [{"text": system_prompt}]
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user_prompt}]
                    }
                ],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                }
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "NetSage-AI/1.0",
            }

            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=timeout
                )

                # If model is overloaded (503) or not found (404), try next fallback
                if response.status_code in [503, 404, 429]:
                    last_error = f"Gemini API ({clean_model_name} HTTP {response.status_code}): {response.text[:200]}"
                    continue

                response.raise_for_status()
                res_json = response.json()

                candidates = res_json.get("candidates", [])
                if not candidates:
                    raise ValueError(f"No candidate responses returned by Gemini API for model {clean_model_name}.")

                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                
                # Extract JSON using regex or direct parsing
                clean_text = text.strip()
                # Remove code blocks if present
                clean_text = re.sub(r'^```(?:json)?\s*', '', clean_text, flags=re.MULTILINE)
                clean_text = re.sub(r'```$', '', clean_text, flags=re.MULTILINE).strip()
                
                # Find outermost JSON object
                json_match = re.search(r'(\{[\s\S]*\})', clean_text)
                if json_match:
                    return json.loads(json_match.group(1))

                return json.loads(clean_text)

            except requests.exceptions.Timeout:
                last_error = f"Gemini request timed out for model {clean_model_name} after {timeout} seconds."
                continue
            except requests.exceptions.RequestException as e:
                last_error = f"Gemini request error on {clean_model_name}: {str(e)}"
                continue
            except Exception as e:
                last_error = f"Failed to parse Gemini response on {clean_model_name}: {str(e)}"
                continue

        raise RuntimeError(last_error or "Failed to communicate with any supported Gemini model.")
