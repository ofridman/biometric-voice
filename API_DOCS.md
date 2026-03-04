# Biometric Voice Recognition API

**Base URL:** `http://localhost:7098`
**Production URL:** `https://tai-ubuntu.cow-court.ts.net/voice`


Interactive docs available at `http://localhost:7098/docs` (Swagger UI).

---

## POST `/enroll`

Enroll a new speaker by uploading a voice sample.

### Request

| Field | Type | In | Required | Description |
|-------|------|----|----------|-------------|
| `name` | string | form | yes | Speaker name / identifier |
| `audio` | file | form | yes | Audio file (WAV recommended, 16 kHz, 5–10s of speech) |

**Content-Type:** `multipart/form-data`

### cURL example

```bash
curl -X POST http://localhost:7098/enroll \
  -F "name=Alice" \
  -F "audio=@samples/alice.wav"
```

### Response `200 OK`

```json
{
  "status": "ok",
  "speaker": "Alice"
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
