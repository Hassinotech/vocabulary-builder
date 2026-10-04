import os

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

DEFAULT_MODEL = "gemini-3.8-flash"


class LearningContent(BaseModel):
    """The shape of the learning content we want Gemini to return."""

    explanation: str = Field(description="A simple 1-2 sentence explanation in plain English.")
    examples: list[str] = Field(description="Exactly 3 example sentences using the word.")
    memory_trick: str = Field(description="A short, memorable trick for remembering the meaning.")


class AIContentGenerator:
    """Creates vocabulary learning content using Google's Gemini AI."""

    def __init__(self, model_name=DEFAULT_MODEL):
        
        api_key = os.environ.get("GEMINI_API_KEY")

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def _ask_gemini(self, prompt, schema):
        """Send a prompt to Gemini and return its reply as a Python dictionary.

        `schema` is a Pydantic model class describing the shape of the reply.
        """
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
                # Ask for JSON that follows the shape described by `schema`.
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        # The library turns the JSON into a `schema` object for us;
        # model_dump() then turns that object into a plain dictionary.
        return response.parsed.model_dump()


if __name__ == "__main__":
    generator = AIContentGenerator()
    result = generator._ask_gemini(
        "Create learning content for the word 'resilient' for an English learner.",
        LearningContent,
    )
    print(type(result))
    print(result)
