import json
import re
import urllib.request
import urllib.error
from typing import Any, Dict
from app.services.ai.base import BaseAiProvider

class OpenAiProvider(BaseAiProvider):
    """OpenAI API Provider implementation."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def generate_diagnosis(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "gpt-4o-mini",
        timeout: int = 30
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                content = res_json["choices"][0]["message"]["content"]
                clean_text = re.sub(r'^```(?:json)?\s*', '', content.strip(), flags=re.MULTILINE)
                clean_text = re.sub(r'```$', '', clean_text.strip(), flags=re.MULTILINE)
                return json.loads(clean_text)
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode('utf-8', errors='ignore')
            raise RuntimeError(f"OpenAI API Error (HTTP {e.code}): {err_msg}")
        except Exception as e:
            raise RuntimeError(f"Failed to communicate with OpenAI API: {str(e)}")
