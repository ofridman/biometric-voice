# Biometric Voice Recognition

Speaker enrollment, verification, and identification powered by [SpeechBrain](https://speechbrain.readthedocs.io/) ECAPA-TDNN embeddings.

## Setup

```bash
pip install -e .

# Optional – enable microphone recording
pip install -e ".[record]"
```

The first run downloads the pretrained `spkrec-ecapa-voxceleb` model (~80 MB).

## Usage

### Enroll a speaker

```bash
biometric-voice enroll "Alice" samples/alice.wav
```

### Verify a speaker

```bash
biometric-voice verify "Alice" test.wav
# Exit code 0 = match, 1 = no match
```

### Identify who is speaking

```bash
biometric-voice identify unknown.wav
```

### Record from microphone

```bash
biometric-voice record sample.wav --duration 5
```

### List / remove enrolled speakers

```bash
biometric-voice list
biometric-voice remove "Alice"
```

### Custom threshold

Use `-t` to adjust the cosine-similarity threshold (default 0.25, higher = stricter):

```bash
biometric-voice verify "Alice" test.wav -t 0.40
```

## Python API

```python
from biometric_voice.speaker import SpeakerVerifier

verifier = SpeakerVerifier()

verifier.enroll("Alice", "samples/alice.wav")

match, score = verifier.verify("Alice", "test.wav")
print(f"Match: {match}, Score: {score:.4f}")

name, score = verifier.identify("unknown.wav")
print(f"Speaker: {name}, Score: {score:.4f}")
```

## Project structure

```
biometric_voice/
├── __init__.py
├── speaker.py      # Core SpeakerVerifier class
└── cli.py          # Command-line interface
data/
├── enrolled_speakers/   # Copies of enrollment audio
├── embeddings.json      # Stored speaker embeddings
└── pretrained_models/   # Cached SpeechBrain model
```
