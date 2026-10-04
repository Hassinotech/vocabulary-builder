import os

from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-3.8-flash"


class AIContentGenerator:
    """Creates vocabulary learning content using Google's Gemini AI."""

    def __init__(self, model_name=DEFAULT_MODEL):
        
        api_key = os.environ.get("GEMINI_API_KEY")

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def _ask_gemini(self, prompt):
        """Send a prompt to Gemini and return its reply as a string."""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )
        return response.text


if __name__ == "__main__":
    generator = AIContentGenerator()
    print(generator._ask_gemini(
        "Explain the word 'resilient' in one simple sentence for an English learner."
    ))
