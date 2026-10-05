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

import copy                          # Makes independent copies of saved answers
import os
import re                          # Regular expressions: patterns for checking and cleaning text
import time                          # Lets us pause between retries
from typing import Literal           # Restricts a field to a fixed list of allowed values

import httpx                         # The internet library google-genai uses (for "no internet" errors)
from google import genai             # Google's official Gemini library
from google.genai import errors      # Gemini's error types
from google.genai import types       # Ready-made "forms" for Gemini request settings
from pydantic import BaseModel, Field  # Lets us describe the exact shape of Gemini's answer

# The Gemini model we use. Change it here only, and every request will use it.
DEFAULT_MODEL = "gemini-3.1-flash-lite"

# A standing instruction that tells Gemini who to be for every request.
TUTOR_INSTRUCTION = (
    "You are a friendly vocabulary tutor for English learners. "
    "Use simple, everyday English and avoid difficult words in your explanations."
)

# How many times to try a request before giving up, and how long to wait.
MAX_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 2
# Error codes worth retrying: 429 = too many requests, 5xx = server problems.
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)

# What counts as a valid word: letters, optionally joined by one hyphen,
# apostrophe or space, e.g. "bank", "mother-in-law", "don't", "ice cream".
WORD_PATTERN = re.compile(r"[a-z]+(?:[-' ][a-z]+)*")
MAX_WORD_LENGTH = 40


class AIServiceError(Exception):
    """Raised when Gemini can't create content (no key, no internet, server busy...).

    The message is written so it can be shown directly to the user.
    """


def _friendly_message(error):
    """Turn a Gemini APIError into a message a user can understand."""
    if "API key" in str(error):
        return "The Gemini API key is not valid. Please check the GEMINI_API_KEY setting."
    if error.code == 429:
        return "The AI's free usage limit has been reached. Please wait a bit and try again."
    if error.code >= 500:
        return "The AI service is busy right now. Please try again in a few minutes."
    return f"The AI request failed (error {error.code})."


def _clean_word(word):
    """Tidy a word ("  Bank " -> "bank") and check it's valid.

    Raises ValueError with a friendly message if it isn't.
    """
    word = " ".join(str(word).split()).lower()  # remove extra spaces, make lowercase
    if not word:
        raise ValueError("Please enter a word.")
    if len(word) > MAX_WORD_LENGTH or not WORD_PATTERN.fullmatch(word):
        raise ValueError(f"'{word}' doesn't look like a word. Please use letters only.")
    return word


def _clean_text(text):
    """Remove markdown symbols (** * ` #) and extra spaces from Gemini's text.

    Underscores are kept on purpose: fill-in-the-blank questions use ____.
    """
    text = re.sub(r"[*`#]+", "", text)        # remove the symbols
    return re.sub(r"\s+", " ", text).strip()  # squash repeated spaces into one


def _is_good_question(question):
    """A usable question has 4 different options, and the answer is one of them."""
    options = question["options"]
    return (
        len(options) == 4
        and len(set(options)) == 4  # no repeated options
        and question["correct_answer"] in options
    )


def _fallback_content(word, definition, message):
    """Backup learning content, used when the AI can't help."""
    return {
        "word": word,
        "explanation": definition or "AI explanation is not available right now.",
        "examples": [],
        "memory_trick": "",
        "source": "fallback",
        "error": message,
    }


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
    """Creates vocabulary learning content using Google's Gemini AI.

    Learning content is cached (saved) inside this object, so asking for the
    same word twice only uses Gemini once. Streamlit reruns app.py on every
    click, so create the generator ONCE, or the cache will always be empty:

        @st.cache_resource
        def get_generator():
            return AIContentGenerator()
    """

    def __init__(self, model_name=DEFAULT_MODEL):
        # Read the key from the environment, so it never appears in this file.
        api_key = os.environ.get("GEMINI_API_KEY")

        # Create the connection to Gemini once and reuse it for every request.
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            # Without a key, don't crash the app. Each request will fail
            # with a clear message instead.
            self.client = None
        self.model_name = model_name

        # Saved answers: (word, definition) -> learning content.
        self._cache = {}

    def _ask_gemini(self, prompt, schema):
        """Send a prompt to Gemini and return its reply as a Python dictionary.

        `schema` is a Pydantic model class describing the shape of the reply.
        The leading underscore means this is an internal helper: other modules
        should call the public methods below instead.

        Raises:
            AIServiceError: if Gemini can't be reached or gives an unusable answer.
        """
        if self.client is None:
            raise AIServiceError("No Gemini API key found. Please set GEMINI_API_KEY.")

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
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
            except errors.APIError as error:
                # Busy server or rate limit, and we still have tries left: wait, then retry.
                if error.code in RETRY_STATUS_CODES and attempt < MAX_ATTEMPTS:
                    time.sleep(RETRY_WAIT_SECONDS * attempt)  # wait 2s, then 4s
                    continue
                raise AIServiceError(_friendly_message(error)) from error
            except httpx.TransportError as error:
                raise AIServiceError(
                    "Could not reach the AI service. Please check your internet connection."
                ) from error

            # We only reach this point if the request worked.
            # If Gemini's JSON didn't match the form, the library leaves parsed empty.
            if response.parsed is None:
                raise AIServiceError("The AI sent back an answer in the wrong format.")

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
                "source" (str): "ai" if Gemini created it, "fallback" if not
                "error" (str or None): None if it worked, otherwise a
                    message you can show the user

        Never raises an error: if Gemini fails, it returns backup content
        with "source": "fallback". The explanation is then the dictionary
        definition (if one was given), "examples" is an empty list and
        "memory_trick" is an empty string. An invalid word (empty, numbers,
        symbols) also returns fallback content, with the reason in "error".
        The word is returned tidied and lowercase ("  Bank " -> "bank").
        """
        # Check the word first, so we don't waste a Gemini request on it.
        try:
            word = _clean_word(word)
        except ValueError as error:
            return _fallback_content(word, definition, str(error))

        # Already asked about this word (with this definition)? Reuse the saved answer.
        cache_key = (word, definition)
        if cache_key in self._cache:
            return copy.deepcopy(self._cache[cache_key])

        # Build the request. If the dictionary module found a definition,
        # include it so Gemini explains the same meaning.
        prompt = f"Create learning content for the word '{word}'."
        if definition:
            prompt += f"\nUse this meaning from the dictionary: {definition}"

        try:
            content = self._ask_gemini(prompt, LearningContent)
        except AIServiceError as error:
            # The AI failed: return backup content so the app keeps working.
            return _fallback_content(word, definition, str(error))

        # Remove stray markdown (like **bold**) and extra spaces from Gemini's text.
        content["explanation"] = _clean_text(content["explanation"])
        content["examples"] = [_clean_text(example) for example in content["examples"]]
        content["memory_trick"] = _clean_text(content["memory_trick"])

        # Add keys Gemini doesn't need to fill in, because we already know them.
        content["word"] = word
        content["source"] = "ai"  # tells the UI this came from the AI
        content["error"] = None   # same keys as the fallback, so callers can always check it

        # Save a copy for next time. Only real AI answers are saved, never fallbacks.
        self._cache[cache_key] = copy.deepcopy(content)
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

            Questions that fail the quality check (not 4 different options,
            or an answer that isn't one of them) are removed, so the list
            may be shorter than num_questions. Invalid words are skipped.

        Raises:
            AIServiceError: if the quiz can't be created (no key, no internet,
                AI busy, no valid words, no usable questions...). The message
                can be shown to the user, e.g.:

                    try:
                        questions = generator.generate_quiz(words)
                    except AIServiceError as error:
                        st.error(str(error))
        """
        # Keep only the valid words (tidied), and skip the rest.
        valid_words = []
        for word in words:
            try:
                valid_words.append(_clean_word(word))
            except ValueError:
                pass  # not a real word, so leave it out of the quiz
        if not valid_words:
            raise AIServiceError("There are no valid words to make a quiz from.")
        words = valid_words

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

        # Clean each question's text, then keep only the good questions.
        good_questions = []
        for question in quiz["questions"]:  # unwrap the list from the Quiz form
            question["question"] = _clean_text(question["question"])
            question["options"] = [_clean_text(option) for option in question["options"]]
            question["correct_answer"] = _clean_text(question["correct_answer"])
            question["explanation"] = _clean_text(question["explanation"])
            if _is_good_question(question):
                good_questions.append(question)

        if not good_questions:
            raise AIServiceError("The AI couldn't create usable quiz questions. Please try again.")
        return good_questions


# This block only runs when the file is run directly
# (python modules/gemini_api.py), not when another module imports it.
# It demonstrates every feature and uses only 2 Gemini requests.
if __name__ == "__main__":
    generator = AIContentGenerator()

    # 1. Learning content, using a dictionary definition
    print("=== 1. Learning content for 'bank' (river meaning) ===")
    content = generator.get_learning_content(
        "bank", definition="the land along the side of a river"
    )
    print("Source:      ", content["source"])
    if content["error"]:
        print("Error:       ", content["error"])
    print("Explanation: ", content["explanation"])
    for example in content["examples"]:
        print("  -", example)
    print("Memory trick:", content["memory_trick"])

    # 2. Caching: the same word again should be instant
    print("\n=== 2. Same word again (from the cache) ===")
    start = time.perf_counter()  # a stopwatch
    generator.get_learning_content(
        "  BANK ", definition="the land along the side of a river"
    )
    print(f"Took {time.perf_counter() - start:.3f} seconds (no Gemini request)")

    # 3. Validation: an invalid word never reaches Gemini
    print("\n=== 3. Invalid word ===")
    bad = generator.get_learning_content("123")
    print("Source:", bad["source"], "| Error:", bad["error"])

    # 4. Quiz, with error handling (this is how the quiz module should call it)
    print("\n=== 4. Quiz ===")
    try:
        questions = generator.generate_quiz(
            ["resilient", "bank", "creation"],
            definitions={"bank": "the land along the side of a river"},
        )
    except AIServiceError as error:
        print("Could not create the quiz:", error)
    else:  # only runs if no error happened
        for number, q in enumerate(questions, start=1):
            print(f"\nQ{number} [{q['question_type']}] {q['question']}")
            for option in q["options"]:
                print("   -", option)
            print("   Answer:", q["correct_answer"])
            print("   Why:   ", q["explanation"])
