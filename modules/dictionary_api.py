"""
Dictionary API module: looks words up in the Free Dictionary API.

    from modules.dictionary_api import DictionaryClient, WordNotFoundError

    client = DictionaryClient()
    word = client.lookup("bank")        # a Word object
    print(word.first_definition)
"""

from dataclasses import dataclass, field

import requests

from modules.validation import clean_word

API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
TIMEOUT_SECONDS = 30  # the free API sometimes takes 20+ seconds


class WordNotFoundError(Exception):
    """Raised when the dictionary has no entry for the word."""


class DictionaryAPIError(Exception):
    """Raised when the dictionary can't be reached (no internet, timeout, server error)."""


@dataclass
class Word:
    """Everything the dictionary knows about one word."""

    text: str
    phonetic: str = ""
    # One dict per part of speech:
    # {"part_of_speech": "noun", "definitions": [{"definition": ..., "example": ...}]}
    meanings: list = field(default_factory=list)
    synonyms: list = field(default_factory=list)
    antonyms: list = field(default_factory=list)

    @property
    def first_definition(self):
        """The first definition found, or "" if there is none."""
        for meaning in self.meanings:
            for item in meaning["definitions"]:
                return item["definition"]
        return ""

    @property
    def examples(self):
        """All example sentences the dictionary gives."""
        return [
            item["example"]
            for meaning in self.meanings
            for item in meaning["definitions"]
            if item.get("example")
        ]


class DictionaryClient:
    """Fetches word information from the Free Dictionary API."""

    def __init__(self):
        # Words already looked up, so the same word isn't fetched twice.
        self._cache = {}

    def lookup(self, text):
        """Look a word up and return a Word.

        Raises:
            InvalidWordError: the input isn't a valid word.
            WordNotFoundError: the dictionary has no entry for it.
            DictionaryAPIError: the dictionary couldn't be reached.
        """
        word = clean_word(text)
        if word in self._cache:
            return self._cache[word]

        try:
            response = requests.get(API_URL.format(word=word), timeout=TIMEOUT_SECONDS)
        except requests.Timeout as error:
            raise DictionaryAPIError(
                "The dictionary took too long to answer. Please try again."
            ) from error
        except requests.RequestException as error:
            raise DictionaryAPIError(
                "Could not reach the dictionary. Please check your internet connection."
            ) from error

        if response.status_code == 404:
            raise WordNotFoundError(f"No definition found for '{word}'.")
        if response.status_code != 200:
            raise DictionaryAPIError(
                f"The dictionary is having problems (error {response.status_code})."
            )

        try:
            entries = response.json()
        except ValueError as error:
            raise DictionaryAPIError("The dictionary sent back an unreadable answer.") from error

        result = self._parse(word, entries)
        self._cache[word] = result
        return result

    @staticmethod
    def _parse(word, entries):
        """Turn the API's JSON (a list of entries) into one Word."""
        result = Word(text=word)
        for entry in entries:
            # Phonetic text: keep the first one found.
            if not result.phonetic:
                result.phonetic = entry.get("phonetic", "")
            for phonetic in entry.get("phonetics", []):
                if not result.phonetic and phonetic.get("text"):
                    result.phonetic = phonetic["text"]

            for meaning in entry.get("meanings", []):
                definitions = [
                    {"definition": item["definition"], "example": item.get("example", "")}
                    for item in meaning.get("definitions", [])
                    if item.get("definition")
                ]
                result.meanings.append(
                    {"part_of_speech": meaning.get("partOfSpeech", ""), "definitions": definitions}
                )
                # Synonyms and antonyms appear on meanings and on single definitions.
                for source in [meaning, *meaning.get("definitions", [])]:
                    for synonym in source.get("synonyms", []):
                        if synonym not in result.synonyms:
                            result.synonyms.append(synonym)
                    for antonym in source.get("antonyms", []):
                        if antonym not in result.antonyms:
                            result.antonyms.append(antonym)
        return result


if __name__ == "__main__":
    client = DictionaryClient()
    word = client.lookup("happy")
    print(word.text, word.phonetic)
    print("Definition:", word.first_definition)
    print("Synonyms:", word.synonyms[:5])
    print("Antonyms:", word.antonyms[:5])
