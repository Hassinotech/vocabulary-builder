"""
Data & Validation: checking and cleaning text with regular expressions.

Every module that accepts a word from the user should pass it through
clean_word() first, so the whole app follows the same rules.

    from modules.validation import clean_word, InvalidWordError

    try:
        word = clean_word("  Resilient! ")   # -> "resilient"
    except InvalidWordError as error:
        print(error)                          # a message you can show the user
"""

import re

# A valid word: letters, optionally joined by one hyphen, apostrophe or space,
# e.g. "bank", "mother-in-law", "don't", "ice cream".
WORD_PATTERN = re.compile(r"[a-z]+(?:[-' ][a-z]+)*")
MAX_WORD_LENGTH = 40

# Punctuation at the start or end of the input, e.g. the "!" in "hello!".
EDGE_PUNCTUATION = re.compile(r"^[^\w]+|[^\w]+$")

# Markdown symbols that sometimes appear in generated text: ** * ` #
MARKDOWN_SYMBOLS = re.compile(r"[*`#]+")


class InvalidWordError(ValueError):
    """Raised when the user's input is not a valid word.

    The message is written so it can be shown directly to the user.
    """


def clean_word(text):
    """Tidy a word and check it's valid ("  Hello! " -> "hello").

    Removes punctuation at the start and end, extra spaces and capitals.

    Raises:
        InvalidWordError: if the input is empty or isn't a word.
    """
    word = " ".join(str(text).split()).lower()   # extra spaces out, lowercase
    word = EDGE_PUNCTUATION.sub("", word)         # "hello!" -> "hello"
    if not word:
        raise InvalidWordError("Please enter a word.")
    if len(word) > MAX_WORD_LENGTH or not WORD_PATTERN.fullmatch(word):
        raise InvalidWordError(
            f"'{word}' doesn't look like a word. Please use letters only."
        )
    return word


def clean_sentence(text):
    """Remove markdown symbols and repeated spaces from a sentence."""
    text = MARKDOWN_SYMBOLS.sub("", str(text))
    return re.sub(r"\s+", " ", text).strip()
