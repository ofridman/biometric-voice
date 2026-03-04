"""FastAPI server for biometric voice recognition."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from biometric_voice.speaker import SpeakerVerifier

app = FastAPI(title="Biometric Voice Recognition API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

verifier: Optional[SpeakerVerifier] = None


def _get_verifier() -> SpeakerVerifier:
    global verifier
    if verifier is None:
        verifier = SpeakerVerifier()
    return verifier


async def _save_upload(upload: UploadFile) -> Path:
    """Write an uploaded file to a temporary WAV file and return its path."""
    suffix = Path(upload.filename).suffix if upload.filename else ".wav"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(await upload.read())
    tmp.close()
    return Path(tmp.name)


@app.post("/enroll")
async def enroll(name: str = Form(...), audio: UploadFile = File(...)):
    path = await _save_upload(audio)
    try:
        _get_verifier().enroll(name, path)
    finally:
        path.unlink(missing_ok=True)
    return {"status": "ok", "speaker": name}


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


@app.delete("/speakers/{name}")
async def remove_speaker(name: str):
    v = _get_verifier()
    if name not in v.list_speakers():
        raise HTTPException(404, f"Speaker '{name}' is not enrolled.")
    v.remove_speaker(name)
    return {"status": "ok", "removed": name}


def main():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7098)


if __name__ == "__main__":
    main()
