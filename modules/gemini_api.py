"""
PLEASE READ!!

AI/Gemini module for the Vocabulary Builder app.

Uses Google's Gemini AI to create learning content for a word:
a simple explanation, example sentences and a memory trick.

How to use it from another module:

    from modules.gemini_api import AIContentGenerator

    generator = AIContentGenerator()
    content = generator.get_learning_content("resilient")
    print(content["explanation"])

Setup: each person needs their own Gemini API key, saved as an environment
variable called GEMINI_API_KEY (never put the key in the code). Get a key at
https://aistudio.google.com/apikey, then run in a terminal:

    setx GEMINI_API_KEY "your-key-here"

and restart VS Code / the terminal so it can see the new variable. 

This is for any other collaborator by the way.
"""

import os
from typing import Literal           # Restricts a field to a fixed list of allowed values

from google import genai             # Google's official Gemini library
from google.genai import types       # Ready-made "forms" for Gemini request settings
from pydantic import BaseModel, Field  # Lets us describe the exact shape of Gemini's answer

# The Gemini model we use. Change it here only, and every request will use it.
DEFAULT_MODEL = "gemini-3.1-flash-lite"

# A standing instruction that tells Gemini who to be for every request.
TUTOR_INSTRUCTION = (
    "You are a friendly vocabulary tutor for English learners. "
    "Use simple, everyday English and avoid difficult words in your explanations."
)


class LearningContent(BaseModel):
    """The shape of the learning content we want Gemini to return."""

    # Each line is one field Gemini must fill in: its name, its type, and a
    # description. The descriptions are sent to Gemini as instructions.
    explanation: str = Field(description="A simple 1-2 sentence explanation in plain English.")
    examples: list[str] = Field(description="Exactly 3 example sentences using the word.")
    memory_trick: str = Field(description="A short, memorable trick for remembering the meaning.")


class QuizQuestion(BaseModel):
    """The shape of one multiple choice quiz question."""

    word: str = Field(description="The vocabulary word this question tests.")
    # Literal means Gemini must pick exactly one of these three values.
    question_type: Literal["meaning", "fill_in_the_blank", "synonym"] = Field(
        description="The kind of question."
    )
    question: str = Field(
        description="The question text. For fill_in_the_blank, use ____ for the missing word."
    )
    options: list[str] = Field(description="Exactly 4 answer options.")
    # Stored as text (not a position) so it stays correct if the options are shuffled.
    correct_answer: str = Field(description="The correct option, copied exactly from options.")
    explanation: str = Field(description="One simple sentence explaining why the answer is correct.")


class Quiz(BaseModel):
    """A list of quiz questions (Gemini fills in the whole list in one go)."""

    # A form inside a form: a list of QuizQuestion forms.
    questions: list[QuizQuestion]


class AIContentGenerator:
    """Creates vocabulary learning content using Google's Gemini AI."""

    def __init__(self, model_name=DEFAULT_MODEL):
        # Read the key from the environment, so it never appears in this file.
        api_key = os.environ.get("GEMINI_API_KEY")

        # Create the connection to Gemini once and reuse it for every request.
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def _ask_gemini(self, prompt, schema):
        """Send a prompt to Gemini and return its reply as a Python dictionary.

        `schema` is a Pydantic model class describing the shape of the reply.
        The leading underscore means this is an internal helper: other modules
        should call the public methods below instead.
        """
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                # Give Gemini its "friendly tutor" role.
                system_instruction=TUTOR_INSTRUCTION,
                # We don't let Gemini call Python functions, so turn this
                # feature off (this also hides a warning from the library).
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

    def get_learning_content(self, word, definition=None):
        """Create simple learning content for one word.

        Args:
            word (str): The word to explain.
            definition (str, optional): The definition from the dictionary
                module. If given, Gemini explains this exact meaning.

        Returns:
            dict with these keys:
                "word" (str): the word that was explained
                "explanation" (str): 1-2 simple sentences
                "examples" (list[str]): 3 example sentences
                "memory_trick" (str): a trick for remembering the meaning
                "source" (str): "ai" (may also be "fallback" once error
                    handling is added)
        """
        # Build the request. If the dictionary module found a definition,
        # include it so Gemini explains the same meaning.
        prompt = f"Create learning content for the word '{word}'."
        if definition:
            prompt += f"\nUse this meaning from the dictionary: {definition}"

        content = self._ask_gemini(prompt, LearningContent)

        # Add two keys Gemini doesn't need to fill in, because we already know them.
        content["word"] = word
        content["source"] = "ai"  # tells the UI this came from the AI
        return content

    def generate_quiz(self, words, definitions=None, num_questions=5):
        """Create multiple choice quiz questions for a list of words.

        Args:
            words (list[str]): The words to test, e.g. ["resilient", "bank"].
            definitions (dict, optional): Word -> definition from the dictionary
                module, e.g. {"bank": "the land along the side of a river"}.
            num_questions (int): How many questions to create (default 5).

        Returns:
            list of dicts, one per question, each with these keys:
                "word" (str): the word being tested
                "question_type" (str): "meaning", "fill_in_the_blank" or "synonym"
                "question" (str): the question text
                "options" (list[str]): 4 answer options
                "correct_answer" (str): the right option, exactly as written in "options"
                "explanation" (str): one sentence explaining the answer
        """
        # Build the request: which words, how many questions, and the rules.
        prompt = (
            f"Create {num_questions} multiple-choice quiz questions to test these words: "
            f"{', '.join(words)}.\n"
            "Mix the question types: meaning, fill_in_the_blank and synonym.\n"
            "Each question must have exactly 4 options, and correct_answer must be "
            "copied exactly from the options."
        )
        # If the dictionary module gave us definitions, add one line per word
        # so the questions test the same meanings the user saw.
        if definitions:
            prompt += "\nUse these meanings from the dictionary:"
            for word, meaning in definitions.items():
                prompt += f"\n- {word}: {meaning}"

        quiz = self._ask_gemini(prompt, Quiz)

        # Unwrap the list from the Quiz form, so callers get a plain list.
        return quiz["questions"]


# This block only runs when the file is run directly
# (python modules/gemini_api.py), not when another module imports it.
# Use it to quickly test the module on its own.
if __name__ == "__main__":
    generator = AIContentGenerator()
    content = generator.get_learning_content(
        "bank", definition="the land along the side of a river"
    )
    print(content)

    # Test the quiz: print each question with its options and answer.
    questions = generator.generate_quiz(["resilient", "bank", "creation"])
    for q in questions:
        print()
        print(f"[{q['question_type']}] {q['question']}")
        for option in q["options"]:
            print("   -", option)
        print("   Answer:", q["correct_answer"])
