# System Overview — How Biometric Voice Recognition Works

## The big picture

This system turns a person's voice into a unique numerical fingerprint (called an **embedding**) and uses it to confirm or discover their identity. It does **not** recognize what someone is saying — it recognizes **who** is speaking.

---

## 1. The model: ECAPA-TDNN

The core of the system is a pretrained neural network called **ECAPA-TDNN** (`speechbrain/spkrec-ecapa-voxceleb`), downloaded from HuggingFace the first time the service starts.

- **Architecture**: Emphasized Channel Attention, Propagation and Aggregation Time Delay Neural Network
- **Trained on**: VoxCeleb dataset — over 7,000 speakers, over 1 million utterances from celebrities extracted from YouTube videos
- **What it learned**: To map any audio clip to a 192-dimensional vector that captures the unique vocal characteristics of the speaker (pitch, timbre, vocal tract shape, speaking rhythm)
- **Text-independent**: It works regardless of what words are spoken

### Model files location

```
data/pretrained_models/
├── hyperparams.yaml          # Model architecture config
├── embedding_model.ckpt      # Neural network weights (~80 MB)
├── classifier.ckpt           # Classification head weights
├── mean_var_norm_emb.ckpt    # Embedding normalization stats
└── label_encoder.txt         # Speaker label mappings
```

These are downloaded once from HuggingFace and cached locally.

---

## 2. How enrollment works

When you enroll a speaker (e.g., "Alice"):

```
Audio file (WAV) ──> Resample to 16 kHz mono
                         │
                         ▼
                  ECAPA-TDNN model
                         │
                         ▼
              192-dimensional embedding
              (a list of 192 float numbers)
                         │
                    ┌────┴────┐
                    ▼         ▼
           embeddings.json   data/enrolled_speakers/Alice/
           (the vector)      (copy of the original audio)
```

**Step by step:**

1. The audio file is loaded and converted to 16 kHz mono (the format the model expects)
2. The ECAPA-TDNN model processes the entire audio waveform and outputs a **192-dimensional vector** — this is the speaker's voiceprint
3. The vector is serialized as a JSON array of floats and saved to `embeddings.json` under the speaker's name
4. A copy of the original audio is stored in `data/enrolled_speakers/<name>/` for reference

### What the embedding looks like

```json
{
  "Alice": [0.0234, -0.1891, 0.4521, 0.0078, ..., -0.3012],
  "Bob":   [0.1456, 0.0923, -0.2187, 0.3341, ..., 0.0891]
}
```

Each speaker's identity is reduced to 192 numbers. These numbers encode vocal characteristics in a way where:
- Same person, different words → similar vectors
- Different people, same words → different vectors

---

## 3. How verification works (1:1)

Verification answers: **"Is this audio from Alice?"**

```
Test audio ──> ECAPA-TDNN ──> test embedding
                                    │
                                    ▼
                           cosine similarity
                                    │
                   ┌────────────────┤
                   ▼                ▼
          Alice's stored     score (0.0 to 1.0)
          embedding               │
                                  ▼
                          score >= threshold?
                           │            │
                          YES           NO
                        MATCH        NO MATCH
```

**Cosine similarity** measures the angle between two vectors:
- **1.0** = identical direction = same speaker
- **0.0** = perpendicular = unrelated
- **-1.0** = opposite = maximally different

The **threshold** (default `0.25`) determines the cutoff. Scores above it are considered a match.

---

## 4. How identification works (1:N)

Identification answers: **"Who is speaking?"**

```
Test audio ──> ECAPA-TDNN ──> test embedding
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
               cosine sim     cosine sim      cosine sim
               vs Alice        vs Bob         vs Charlie
                 0.82           0.15            0.41
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                            highest score = 0.82
                            0.82 >= 0.25 threshold?
                                   YES
                                    ▼
                            Result: "Alice"
```

The test embedding is compared against **every** enrolled speaker. The highest-scoring match is returned if it exceeds the threshold.

---

## 5. Where all the data lives

```
data/
├── pretrained_models/           # Cached ECAPA-TDNN model from HuggingFace
│   ├── hyperparams.yaml         #   Model config
│   ├── embedding_model.ckpt     #   Network weights (~80 MB)
│   ├── classifier.ckpt          #   Classification head
│   ├── mean_var_norm_emb.ckpt   #   Normalization parameters
│   └── label_encoder.txt        #   Label mappings
│
├── embeddings.json              # All enrolled speaker vectors
│                                #   { "name": [192 floats], ... }
│
└── enrolled_speakers/           # Backup copies of enrollment audio
    ├── Alice/
    │   └── alice.wav
    └── Bob/
        └── bob.wav
```

| Data | Format | Purpose |
|------|--------|---------|
| `pretrained_models/` | PyTorch checkpoints + YAML | The neural network itself — downloaded once, never modified |
| `embeddings.json` | JSON `{ name: float[] }` | The voiceprint database — this is what gets compared during verify/identify |
| `enrolled_speakers/` | WAV files | Original enrollment audio kept for reference — not used during verification |

---

## 6. Security and privacy considerations

- **Embeddings are not reversible** — you cannot reconstruct someone's voice from the 192-float vector. The embedding is a lossy, one-way transformation.
- **Embeddings are stored in plaintext JSON** — anyone with file access can read them. In a production system, consider encrypting `embeddings.json` at rest.
- **Audio copies are stored unencrypted** — the `enrolled_speakers/` directory contains raw audio files. Consider whether you need to retain these.
- **No authentication on the API** — the FastAPI server has no auth. Anyone who can reach port 7098 can enroll, verify, or delete speakers.

---

## 7. Threshold tuning guide

| Threshold | Behavior | Use case |
|-----------|----------|----------|
| `0.15` | Very permissive — more false positives | Convenience-first (smart home) |
| `0.25` | Default — balanced | General purpose |
| `0.40` | Strict — fewer false positives | Security-sensitive applications |
| `0.60` | Very strict — may reject legitimate users | High-security access control |

The right threshold depends on your tolerance for false accepts vs false rejects. Test with your specific microphone and environment.
