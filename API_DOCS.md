# Biometric Voice Recognition API

**Base URL:** `http://localhost:7098`
**Production URL:** `https://tai-ubuntu.cow-court.ts.net/voice`


Interactive docs available at `http://localhost:7098/docs` (Swagger UI).

---

## POST `/enroll`

Enroll a new speaker with liveness detection. Requires a challenge token from `/challenge` — the user must say the challenge phrase so the system can confirm a live person is enrolling.

### Request

| Field | Type | In | Required | Description |
|-------|------|----|----------|-------------|
| `name` | string | form | yes | Speaker name / identifier |
| `token` | string | form | yes | Challenge token from `/challenge` |
| `audio` | file | form | yes | Audio of the user saying the challenge phrase (WAV recommended, 16 kHz, 5–10s) |
| `phrase_threshold` | float | form | no | Phrase match threshold (default: `0.6`, higher = stricter) |

**Content-Type:** `multipart/form-data`

### cURL example

```bash
# Step 1: get a challenge
CHALLENGE=$(curl -s -X POST http://localhost:7098/challenge)
TOKEN=$(echo $CHALLENGE | jq -r '.token')
PHRASE=$(echo $CHALLENGE | jq -r '.phrase')
echo "Say: $PHRASE"

# Step 2: record and enroll
curl -X POST http://localhost:7098/enroll \
  -F "name=Alice" \
  -F "token=$TOKEN" \
  -F "audio=@enrollment.wav"
```

### Response `200 OK` — enrolled successfully

```json
{
  "status": "ok",
  "speaker": "Alice",
  "phrase": {
    "match": true,
    "expected": "blue cat seven",
    "heard": "blue cat seven",
    "score": 0.95
  }
}
```

### Response `200 OK` — phrase did not match (enrollment rejected)

```json
{
  "status": "failed",
  "speaker": "Alice",
  "reason": "Phrase did not match.",
  "phrase": {
    "match": false,
    "expected": "blue cat seven",
    "heard": "hello world",
    "score": 0.18
  }
}
```

### Error `400 Bad Request`

```json
{
  "detail": "Invalid challenge token."
}
```

---

## POST `/verify`

Verify whether an audio sample matches an enrolled speaker (1:1 comparison).

### Request

| Field | Type | In | Required | Description |
|-------|------|----|----------|-------------|
| `name` | string | form | yes | Enrolled speaker name to verify against |
| `audio` | file | form | yes | Audio file to test |
| `threshold` | float | form | no | Cosine similarity threshold (default: `0.25`, higher = stricter) |

**Content-Type:** `multipart/form-data`

### cURL example

```bash
curl -X POST http://localhost:7098/verify \
  -F "name=Alice" \
  -F "audio=@test.wav"
```

### Response `200 OK`

```json
{
  "match": true,
  "score": 0.8234,
  "speaker": "Alice"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `match` | boolean | `true` if score meets or exceeds the threshold |
| `score` | float | Cosine similarity score (range: -1.0 to 1.0, higher = more similar) |
| `speaker` | string | The speaker name that was tested against |

### Error `404 Not Found`

```json
{
  "detail": "Speaker 'Alice' is not enrolled."
}
```

---

## POST `/identify`

Identify who is speaking by comparing against all enrolled speakers (1:N comparison).

### Request

| Field | Type | In | Required | Description |
|-------|------|----|----------|-------------|
| `audio` | file | form | yes | Audio file to identify |
| `threshold` | float | form | no | Cosine similarity threshold (default: `0.25`) |

**Content-Type:** `multipart/form-data`

### cURL example

```bash
curl -X POST http://localhost:7098/identify \
  -F "audio=@unknown.wav"
```

### Response `200 OK` — match found

```json
{
  "speaker": "Alice",
  "score": 0.7891,
  "match": true
}
```

### Response `200 OK` — no match

```json
{
  "speaker": null,
  "score": 0.1234,
  "match": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `speaker` | string \| null | Best matching speaker name, or `null` if no one exceeds the threshold |
| `score` | float | Cosine similarity score of the best match |
| `match` | boolean | `true` if a speaker was identified above the threshold |

### Error `400 Bad Request`

```json
{
  "detail": "No speakers enrolled yet."
}
```

---

## GET `/speakers`

List all enrolled speakers.

### cURL example

```bash
curl http://localhost:7098/speakers
```

### Response `200 OK`

```json
{
  "speakers": ["Alice", "Bob", "Charlie"]
}
```

Returns an empty list if no speakers are enrolled:

```json
{
  "speakers": []
}
```

---

## DELETE `/speakers/{name}`

Remove an enrolled speaker and their stored embedding.

### Path parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Speaker name to remove |

### cURL example

```bash
curl -X DELETE http://localhost:7098/speakers/Alice
```

### Response `200 OK`

```json
{
  "status": "ok",
  "removed": "Alice"
}
```

### Error `404 Not Found`

```json
{
  "detail": "Speaker 'Alice' is not enrolled."
}
```

---

## GET `/speakers/{name}/enrolled`

Check if a specific speaker has been enrolled.

### Path parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Speaker name to check |

### cURL example

```bash
curl http://localhost:7098/speakers/Alice/enrolled
```

### Response `200 OK` — speaker is enrolled

```json
{
  "speaker": "Alice",
  "enrolled": true
}
```

### Response `200 OK` — speaker is not enrolled

```json
{
  "speaker": "Alice",
  "enrolled": false
}
```

---

## POST `/challenge`

Generate a random challenge phrase for liveness verification. Returns a token and phrase that the user must speak. Tokens are single-use — consumed on verification, no expiry.

### cURL example

```bash
curl -X POST http://localhost:7098/challenge
```

### Response `200 OK`

```json
{
  "token": "noPi1z2_-NVpU0GvXk8m...",
  "phrase": "blue cat seven"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `token` | string | One-time token to submit with `/verify-challenge` |
| `phrase` | string | The phrase the user must say aloud (3 common words) |

---

## POST `/verify-challenge`

Verify a speaker's identity with liveness detection. The user must say the phrase from a previously issued challenge. Checks both voice identity and spoken phrase content.

### Request

| Field | Type | In | Required | Description |
|-------|------|----|----------|-------------|
| `name` | string | form | yes | Enrolled speaker name to verify against |
| `token` | string | form | yes | Challenge token from `/challenge` |
| `audio` | file | form | yes | Audio of the user saying the challenge phrase |
| `threshold` | float | form | no | Voice cosine similarity threshold (default: `0.25`) |
| `phrase_threshold` | float | form | no | Phrase match threshold (default: `0.6`, higher = stricter) |

**Content-Type:** `multipart/form-data`

### cURL example

```bash
# Step 1: get a challenge
TOKEN=$(curl -s -X POST http://localhost:7098/challenge | jq -r '.token')
PHRASE=$(curl -s -X POST http://localhost:7098/challenge | jq -r '.phrase')
echo "Say: $PHRASE"

# Step 2: record and submit
curl -X POST http://localhost:7098/verify-challenge \
  -F "name=Alice" \
  -F "token=$TOKEN" \
  -F "audio=@response.wav"
```

### Response `200 OK` — both voice and phrase match

```json
{
  "match": true,
  "speaker": "Alice",
  "voice": {
    "match": true,
    "score": 0.8234
  },
  "phrase": {
    "match": true,
    "expected": "blue cat seven",
    "heard": "blue cat seven",
    "score": 1.0
  }
}
```

### Response `200 OK` — voice matches but wrong phrase (replay attack)

```json
{
  "match": false,
  "speaker": "Alice",
  "voice": {
    "match": true,
    "score": 0.7891
  },
  "phrase": {
    "match": false,
    "expected": "blue cat seven",
    "heard": "hello world test",
    "score": 0.21
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `match` | boolean | `true` only if **both** voice and phrase match |
| `speaker` | string | The speaker name tested against |
| `voice.match` | boolean | Whether the voice embedding matched |
| `voice.score` | float | Cosine similarity score for voice |
| `phrase.match` | boolean | Whether the spoken phrase matched the challenge |
| `phrase.expected` | string | The phrase the user was asked to say |
| `phrase.heard` | string | What the ASR transcribed from the audio |
| `phrase.score` | float | Fuzzy text similarity (0.0–1.0) |

### Error `400 Bad Request`

```json
{
  "detail": "Invalid challenge token."
}
```

### Error `404 Not Found`

```json
{
  "detail": "Speaker 'Alice' is not enrolled."
}
```

---

## Error format

All errors follow FastAPI's standard format:

```json
{
  "detail": "Error message describing what went wrong."
}
```

| Status code | Meaning |
|-------------|---------|
| `400` | Bad request (e.g., no speakers enrolled for identify) |
| `404` | Speaker not found |
| `422` | Validation error (missing or invalid fields) |

### Validation error example (`422`)

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "name"],
      "msg": "Field required",
      "input": null
    }
  ]
}
```
