"""
Data & Validation: saving and loading the app's data in a local JSON file.

Everything the app keeps (flashcards and quiz scores) lives in data.json:

    {
        "flashcards": [ {...}, {...} ],
        "quiz_scores": [ {...}, {...} ]
    }

    from modules.storage import DataManager

    data = DataManager()                 # uses data.json by default
    cards = data.get_flashcards()        # list of dicts
    data.save_flashcards(cards)
"""

import json
import os

DEFAULT_PATH = "data.json"

# What a brand-new data file contains.
EMPTY_DATA = {"flashcards": [], "quiz_scores": []}


class StorageError(Exception):
    """Raised when the data file can't be written (disk full, no permission...)."""


class DataManager:
    """Reads and writes the app's data file."""

    def __init__(self, path=DEFAULT_PATH):
        self.path = path
        # Set when the file existed but couldn't be read, so the UI can warn.
        self.load_error = None

    def load(self):
        """Return all saved data as a dict. Never crashes.

        A missing or empty file gives empty data. A damaged file also gives
        empty data, and load_error explains what went wrong.
        """
        self.load_error = None
        try:
            with open(self.path, encoding="utf-8") as file:
                text = file.read()
        except FileNotFoundError:
            return {key: [] for key in EMPTY_DATA}
        except OSError as error:
            self.load_error = f"Could not read {self.path}: {error}"
            return {key: [] for key in EMPTY_DATA}

        if not text.strip():
            return {key: [] for key in EMPTY_DATA}

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Keep the damaged file under another name, so the next save
            # can't overwrite whatever could still be rescued from it.
            backup_path = self.path + ".damaged"
            try:
                os.replace(self.path, backup_path)
            except OSError:
                backup_path = None
            self.load_error = (
                f"{self.path} was damaged, so saved data could not be loaded."
                + (f" A copy was kept as {backup_path}." if backup_path else "")
            )
            return {key: [] for key in EMPTY_DATA}

        # Make sure both lists exist, even in an older or hand-edited file.
        for key in EMPTY_DATA:
            if not isinstance(data.get(key), list):
                data[key] = []
        return data

    def save(self, data):
        """Write all data to the file.

        It writes to a temporary file first and then swaps it in, so a crash
        halfway through never leaves a half-written data.json.

        Raises:
            StorageError: if the file can't be written.
        """
        temp_path = self.path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.path)
        except OSError as error:
            raise StorageError(f"Could not save your data: {error}") from error

    # ------ Flashcards ------

    def get_flashcards(self):
        return self.load()["flashcards"]

    def save_flashcards(self, flashcards):
        data = self.load()
        data["flashcards"] = flashcards
        self.save(data)

    # ------ Quiz scores ------

    def get_quiz_scores(self):
        return self.load()["quiz_scores"]

    def add_quiz_score(self, score):
        data = self.load()
        data["quiz_scores"].append(score)
        self.save(data)
