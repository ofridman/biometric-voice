"""Challenge-response system for liveness detection.

Generates random phrases, transcribes audio via ASR, and checks whether the
user said the requested phrase (fuzzy match).
"""

from __future__ import annotations

import random
import secrets
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

from speechbrain.inference.ASR import EncoderDecoderASR

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Word pools for generating challenge phrases
COLORS = ["red", "blue", "green", "black", "white", "yellow", "orange", "pink", "gray", "brown"]
NOUNS = [
    "cat", "dog", "tree", "house", "book", "chair", "river", "cloud", "stone", "bird",
    "fish", "moon", "star", "lamp", "door", "bell", "ship", "road", "hill", "rain",
]
NUMBERS = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
ACTIONS = [
    "run", "jump", "walk", "read", "sing", "play", "open", "close", "watch", "call",
]

# How similar the transcription must be to the challenge phrase (0.0 - 1.0)
DEFAULT_PHRASE_THRESHOLD = 0.6

# Maximum number of unconsumed tokens before oldest are evicted
MAX_CHALLENGES = 1000


def generate_phrase(word_count: int = 3) -> str:
    """Generate a random short phrase from common words."""
    pools = [COLORS, NOUNS, NUMBERS, ACTIONS]
    words = []
    used_pools = random.sample(pools, min(word_count, len(pools)))
    for pool in used_pools:
        words.append(random.choice(pool))
    return " ".join(words)


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def phrase_matches(expected: str, transcription: str, threshold: float = DEFAULT_PHRASE_THRESHOLD) -> tuple[bool, float]:
    """Check if the transcription fuzzy-matches the expected phrase.

    Returns (match, similarity_ratio).
    """
    expected_n = _normalize(expected)
    transcription_n = _normalize(transcription)

    ratio = SequenceMatcher(None, expected_n, transcription_n).ratio()
    return ratio >= threshold, ratio


class ChallengeStore:
    """In-memory store for active challenge tokens.

    Tokens are single-use (consumed on verification) with no expiry.
    A max size cap evicts the oldest tokens to prevent unbounded growth.
    """

    def __init__(self, max_size: int = MAX_CHALLENGES) -> None:
        self._challenges: dict[str, str] = {}  # token -> phrase
        self._max_size = max_size

    def create(self, word_count: int = 3) -> tuple[str, str]:
        """Create a new challenge. Returns (token, phrase)."""
        self._evict_if_full()
        phrase = generate_phrase(word_count)
        token = secrets.token_urlsafe(32)
        self._challenges[token] = phrase
        return token, phrase

    def consume(self, token: str) -> Optional[str]:
        """Consume a token and return its phrase, or None if invalid."""
        return self._challenges.pop(token, None)

    def _evict_if_full(self) -> None:
        """Drop the oldest entries if the store exceeds max size."""
        if len(self._challenges) >= self._max_size:
            excess = len(self._challenges) - self._max_size + 1
            keys = list(self._challenges.keys())[:excess]
            for k in keys:
                del self._challenges[k]


class Transcriber:
    """Thin wrapper around SpeechBrain ASR for transcription."""

    def __init__(
        self,
        model_source: str = "speechbrain/asr-crdnn-rnnlm-librispeech",
        save_dir: str | Path = DEFAULT_DATA_DIR / "pretrained_asr",
    ) -> None:
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.model = EncoderDecoderASR.from_hparams(
            source=model_source,
            savedir=str(self.save_dir),
        )

    def transcribe(self, audio_path: str | Path) -> str:
        """Transcribe an audio file and return the text."""
        return self.model.transcribe_file(str(audio_path))
