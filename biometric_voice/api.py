"""FastAPI server for biometric voice recognition."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from biometric_voice.speaker import SpeakerVerifier
from biometric_voice.challenge import ChallengeStore, Transcriber, phrase_matches

app = FastAPI(title="Biometric Voice Recognition API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

verifier: Optional[SpeakerVerifier] = None
transcriber: Optional[Transcriber] = None
challenge_store = ChallengeStore()


def _get_verifier() -> SpeakerVerifier:
    global verifier
    if verifier is None:
        verifier = SpeakerVerifier()
    return verifier


def _get_transcriber() -> Transcriber:
    global transcriber
    if transcriber is None:
        transcriber = Transcriber()
    return transcriber


async def _save_upload(upload: UploadFile) -> Path:
    """Write an uploaded file to a temporary WAV file and return its path."""
    suffix = Path(upload.filename).suffix if upload.filename else ".wav"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(await upload.read())
    tmp.close()
    return Path(tmp.name)


@app.post("/enroll")
async def enroll(
    name: str = Form(...),
    token: str = Form(...),
    audio: UploadFile = File(...),
    phrase_threshold: Optional[float] = Form(None),
):
    # Validate challenge token
    expected_phrase = challenge_store.consume(token)
    if expected_phrase is None:
        raise HTTPException(400, "Invalid challenge token.")

    path = await _save_upload(audio)
    try:
        # Verify the user said the challenge phrase
        transcription = _get_transcriber().transcribe(path)
        p_threshold = phrase_threshold if phrase_threshold is not None else 0.6
        phrase_match, phrase_score = phrase_matches(expected_phrase, transcription, p_threshold)

        if not phrase_match:
            return {
                "status": "failed",
                "speaker": name,
                "reason": "Phrase did not match.",
                "phrase": {
                    "match": False,
                    "expected": expected_phrase,
                    "heard": transcription,
                    "score": round(phrase_score, 4),
                },
            }

        # Phrase matched — enroll the speaker
        _get_verifier().enroll(name, path)
    finally:
        path.unlink(missing_ok=True)

    return {
        "status": "ok",
        "speaker": name,
        "phrase": {
            "match": True,
            "expected": expected_phrase,
            "heard": transcription,
            "score": round(phrase_score, 4),
        },
    }


@app.post("/verify")
async def verify(
    name: str = Form(...),
    audio: UploadFile = File(...),
    threshold: Optional[float] = Form(None),
):
    v = _get_verifier()
    if name not in v.list_speakers():
        raise HTTPException(404, f"Speaker '{name}' is not enrolled.")
    path = await _save_upload(audio)
    try:
        match, score = v.verify(name, path, threshold=threshold)
    finally:
        path.unlink(missing_ok=True)
    return {"match": match, "score": round(score, 4), "speaker": name}


@app.post("/identify")
async def identify(
    audio: UploadFile = File(...),
    threshold: Optional[float] = Form(None),
):
    v = _get_verifier()
    if not v.list_speakers():
        raise HTTPException(400, "No speakers enrolled yet.")
    path = await _save_upload(audio)
    try:
        name, score = v.identify(path, threshold=threshold)
    finally:
        path.unlink(missing_ok=True)
    return {"speaker": name, "score": round(score, 4), "match": name is not None}


@app.get("/speakers")
async def list_speakers():
    return {"speakers": _get_verifier().list_speakers()}


@app.get("/speakers/{name}/enrolled")
async def check_enrolled(name: str):
    enrolled = name in _get_verifier().list_speakers()
    return {"speaker": name, "enrolled": enrolled}


@app.delete("/speakers/{name}")
async def remove_speaker(name: str):
    v = _get_verifier()
    if name not in v.list_speakers():
        raise HTTPException(404, f"Speaker '{name}' is not enrolled.")
    v.remove_speaker(name)
    return {"status": "ok", "removed": name}


@app.post("/challenge")
async def create_challenge():
    token, phrase = challenge_store.create()
    return {"token": token, "phrase": phrase}


@app.post("/verify-challenge")
async def verify_challenge(
    name: str = Form(...),
    token: str = Form(...),
    audio: UploadFile = File(...),
    threshold: Optional[float] = Form(None),
    phrase_threshold: Optional[float] = Form(None),
):
    # Validate challenge token
    expected_phrase = challenge_store.consume(token)
    if expected_phrase is None:
        raise HTTPException(400, "Invalid challenge token.")

    v = _get_verifier()
    if name not in v.list_speakers():
        raise HTTPException(404, f"Speaker '{name}' is not enrolled.")

    path = await _save_upload(audio)
    try:
        # Step 1: verify voice identity
        voice_match, voice_score = v.verify(name, path, threshold=threshold)

        # Step 2: transcribe and check phrase
        transcription = _get_transcriber().transcribe(path)
        p_threshold = phrase_threshold if phrase_threshold is not None else 0.6
        phrase_match, phrase_score = phrase_matches(expected_phrase, transcription, p_threshold)
    finally:
        path.unlink(missing_ok=True)

    overall_match = voice_match and phrase_match

    return {
        "match": overall_match,
        "speaker": name,
        "voice": {"match": voice_match, "score": round(voice_score, 4)},
        "phrase": {
            "match": phrase_match,
            "expected": expected_phrase,
            "heard": transcription,
            "score": round(phrase_score, 4),
        },
    }


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7098)


if __name__ == "__main__":
    main()
