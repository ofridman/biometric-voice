"""Core speaker recognition engine using SpeechBrain ECAPA-TDNN embeddings."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import torch
import torchaudio
from speechbrain.inference.speaker import SpeakerRecognition

from biometric_voice import db

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Cosine-similarity threshold – higher means stricter matching.
DEFAULT_THRESHOLD = 0.25


class SpeakerVerifier:
    """Enroll speakers and verify identities from voice samples."""

    def __init__(
        self,
        model_source: str = "speechbrain/spkrec-ecapa-voxceleb",
        save_dir: str | Path = DEFAULT_DATA_DIR / "pretrained_models",
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        self.threshold = threshold
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.model = SpeakerRecognition.from_hparams(
            source=model_source,
            savedir=str(self.save_dir),
        )

    # ------------------------------------------------------------------
    # Audio helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_audio(path: str | Path) -> torch.Tensor:
        """Load an audio file and resample to 16 kHz mono."""
        signal, sr = torchaudio.load(str(path))
        if signal.shape[0] > 1:
            signal = signal.mean(dim=0, keepdim=True)
        if sr != 16000:
            signal = torchaudio.functional.resample(signal, sr, 16000)
        return signal

    def _extract_embedding(self, audio_path: str | Path) -> list[float]:
        """Return an embedding as a list of floats for the given audio file."""
        signal = self._load_audio(audio_path)
        embedding = self.model.encode_batch(signal)
        return embedding.squeeze().tolist()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enroll(self, speaker_name: str, audio_path: str | Path) -> None:
        """Enroll a speaker by computing and storing their voice embedding."""
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        embedding = self._extract_embedding(audio_path)
        db.upsert_speaker(speaker_name, embedding)

    def verify(
        self,
        speaker_name: str,
        audio_path: str | Path,
        threshold: Optional[float] = None,
    ) -> tuple[bool, float]:
        """Verify whether *audio_path* matches the enrolled *speaker_name*.

        Returns
        -------
        match : bool
            True if the speaker is verified.
        score : float
            Cosine similarity score (higher = more similar).
        """
        enrolled_emb = db.get_embedding(speaker_name)
        if enrolled_emb is None:
            raise KeyError(
                f"Speaker '{speaker_name}' is not enrolled. "
                f"Enrolled speakers: {db.list_speakers()}"
            )

        threshold = threshold if threshold is not None else self.threshold

        enrolled_t = torch.tensor(enrolled_emb).unsqueeze(0)
        test_t = torch.tensor(self._extract_embedding(audio_path)).unsqueeze(0)

        score = torch.nn.functional.cosine_similarity(enrolled_t, test_t)
        score_val = score.item()
        return score_val >= threshold, score_val

    def identify(
        self, audio_path: str | Path, threshold: Optional[float] = None
    ) -> tuple[Optional[str], float]:
        """Identify the speaker from enrolled voices.

        Returns the best-matching speaker name and score, or (None, score) if
        no enrolled speaker exceeds the threshold.
        """
        all_embeddings = db.get_all_embeddings()
        if not all_embeddings:
            raise RuntimeError("No speakers enrolled yet.")

        threshold = threshold if threshold is not None else self.threshold
        test_t = torch.tensor(self._extract_embedding(audio_path)).unsqueeze(0)

        best_name: Optional[str] = None
        best_score = -1.0

        for name, emb_list in all_embeddings.items():
            enrolled_t = torch.tensor(emb_list).unsqueeze(0)
            score = torch.nn.functional.cosine_similarity(enrolled_t, test_t).item()
            if score > best_score:
                best_score = score
                best_name = name

        if best_score >= threshold:
            return best_name, best_score
        return None, best_score

    def list_speakers(self) -> list[str]:
        """Return the names of all enrolled speakers."""
        return db.list_speakers()

    def remove_speaker(self, speaker_name: str) -> None:
        """Remove an enrolled speaker."""
        if not db.remove_speaker(speaker_name):
            raise KeyError(f"Speaker '{speaker_name}' is not enrolled.")
