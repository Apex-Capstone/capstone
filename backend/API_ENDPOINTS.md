# API Endpoints Reference

Base URL: `/v1`

## Authentication

### POST /v1/auth/login
Login with email/password and receive JWT tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "role": "trainee",
    "full_name": "John Doe"
  }
}
```

### POST /v1/auth/refresh
Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

---

## Cases

### GET /v1/cases
List all available cases (id, title, objectives).

**Query Parameters:**
- `skip`: Offset (default: 0)
- `limit`: Limit (default: 100)
- `difficulty`: Filter by difficulty level
- `category`: Filter by category

**Response:**
```json
{
  "cases": [
    {
      "id": 1,
      "title": "Breaking Bad News: Terminal Cancer",
      "description": "Patient with stage 4 lung cancer",
      "objectives": "Practice SPIKES protocol",
      "difficulty_level": "advanced"
    }
  ],
  "total": 10
}
```

### GET /v1/cases/{case_id}
Get detailed case information.

**Response:**
```json
{
  "id": 1,
  "title": "Breaking Bad News: Terminal Cancer",
  "description": "...",
  "script": "Full patient scenario...",
  "objectives": "Practice SPIKES protocol",
  "patient_background": "Patient history...",
  "expected_spikes_flow": "..."
}
```

---

## Sessions

### POST /v1/sessions
Create a new session for a case.

**Request:**
```json
{
  "case_id": 1
}
```

**Response:**
```json
{
  "id": 123,
  "user_id": 1,
  "case_id": 1,
  "state": "active",
  "current_spikes_stage": "setting",
  "started_at": "2025-11-03T10:00:00Z"
}
```

### POST /v1/sessions/{session_id}/turns
Submit trainee text turn; returns patient reply with updated SPIKES stage.

**Request:**
```json
{
  "text": "Hello, I understand this must be a difficult time for you."
}
```

**Response:**
```json
{
  "turn": {
    "id": 456,
    "session_id": 123,
    "turn_number": 2,
    "role": "assistant",
    "text": "Thank you doctor. I'm quite worried about the results.",
    "spikes_stage": "perception"
  },
  "patient_reply": "Thank you doctor. I'm quite worried about the results.",
  "audio_url": null,
  "spikes_stage": "perception"
}
```

### POST /v1/sessions/{session_id}/audio
Upload audio file (wav/ogg/mp3). Server performs ASR → normalized text → same processing as /turns.

**Request:**
- Form data with `audio_file` field
- Supported formats: wav, ogg, mp3

**Response:**
```json
{
  "turn": {
    "id": 458,
    "session_id": 123,
    "turn_number": 4,
    "role": "assistant",
    "text": "I appreciate your concern...",
    "audio_url": "https://s3.../audio.wav",
    "spikes_stage": "knowledge"
  },
  "patient_reply": "I appreciate your concern...",
  "audio_url": "https://s3.../audio.wav",
  "spikes_stage": "knowledge"
}
```

### GET /v1/sessions/{session_id}
Get session detail (state, metrics snapshot).

**Response:**
```json
{
  "id": 123,
  "user_id": 1,
  "case_id": 1,
  "state": "active",
  "current_spikes_stage": "empathy",
  "started_at": "2025-11-03T10:00:00Z",
  "ended_at": null,
  "duration_seconds": 0,
  "turns": [...]
}
```

### GET /v1/sessions/{session_id}/turns
Get paginated transcript of session turns.

**Query Parameters:**
- `skip`: Offset (default: 0)
- `limit`: Limit (default: 100)

**Response:**
```json
{
  "turns": [
    {
      "id": 456,
      "session_id": 123,
      "turn_number": 1,
      "role": "user",
      "text": "Hello, how are you feeling?",
      "timestamp": "2025-11-03T10:01:00Z"
    },
    {
      "id": 457,
      "session_id": 123,
      "turn_number": 2,
      "role": "assistant",
      "text": "I'm very anxious about my diagnosis.",
      "timestamp": "2025-11-03T10:01:15Z"
    }
  ],
  "total": 15,
  "skip": 0,
  "limit": 100
}
```

### POST /v1/sessions/{session_id}:close
Close session and finalize feedback.

**Response:**
```json
{
  "id": 789,
  "session_id": 123,
  "empathy_score": 8.5,
  "communication_score": 7.8,
  "spikes_completion_score": 9.0,
  "overall_score": 8.4,
  "strengths": "Excellent use of empathetic language\nGood use of open-ended questions",
  "areas_for_improvement": "Consider more pauses for patient responses",
  "detailed_feedback": "Overall Score: 8.4/10\n..."
}
```

### GET /v1/sessions/{session_id}/feedback
Get feedback for a previously closed session.

**Response:**
```json
{
  "id": 789,
  "session_id": 123,
  "empathy_score": 8.5,
  "spikes_completion_score": 9.0,
  "overall_score": 8.4,
  "eo_counts_by_dimension": {
    "Feeling": {"explicit": 3, "implicit": 2},
    "Judgment": {"explicit": 1, "implicit": 0},
    "Appreciation": {"explicit": 2, "implicit": 1}
  },
  "elicitation_counts_by_type": {
    "direct": {"Feeling": 2, "Judgment": 1, "Appreciation": 1},
    "indirect": {"Feeling": 1, "Judgment": 0, "Appreciation": 0}
  },
  "response_counts_by_type": {
    "understanding": 4,
    "sharing": 2,
    "acceptance": 3
  },
  "spikes_coverage": {
    "S": true,
    "P": true,
    "I": true,
    "K": true,
    "E": true,
    "S": true
  },
  "spikes_timestamps": {
    "S": {"start_ts": "2025-11-03T10:01:00Z", "end_ts": "2025-11-03T10:02:00Z"},
    "P": {"start_ts": "2025-11-03T10:02:00Z", "end_ts": "2025-11-03T10:03:00Z"}
  },
  "question_breakdown": {
    "open": 8,
    "closed": 3,
    "eliciting": 5,
    "ratio_open": 0.73
  },
  "strengths": "Excellent use of empathetic language\nGood use of open-ended questions",
  "areas_for_improvement": "Consider more pauses for patient responses",
  "detailed_feedback": "Overall Score: 8.4/10",
  "created_at": "2025-11-03T10:15:00Z"
}
```

**Error Responses:**
- `404 Not Found`: Session not found or feedback not found (session not closed yet)
- `403 Forbidden`: User does not own the session

---

## Admin

### GET /v1/admin/sessions
Filter sessions by user, case, date (admin only).

**Query Parameters:**
- `user_id`: Filter by user ID
- `case_id`: Filter by case ID
- `start_date`: Filter by start date
- `end_date`: Filter by end date
- `skip`: Offset
- `limit`: Limit

**Response:**
```json
{
  "sessions": [...],
  "total": 50,
  "skip": 0,
  "limit": 20
}
```

### GET /v1/admin/sessions/{id}
Get session transcript + metrics timeline (admin only).

**Response:**
```json
{
  "session": {
    "id": 123,
    "user_id": 1,
    "case_id": 1,
    "turns": [...]
  },
  "metrics_timeline": [
    {
      "turn_number": 1,
      "timestamp": "2025-11-03T10:01:00Z",
      "empathy_score": 7.5,
      "question_type": "open",
      "spikes_stage": "setting"
    }
  ]
}
```

### GET /v1/admin/aggregates
Get cohort/case aggregates (admin only).

**Response:**
```json
{
  "user_stats": {
    "total_users": 150,
    "users_by_role": {
      "trainee": 145,
      "admin": 5
    },
    "active_users_last_30_days": 85
  },
  "session_stats": {
    "total_sessions": 450,
    "completed_sessions": 380,
    "active_sessions": 15,
    "average_duration_seconds": 1200
  },
  "performance_stats": {
    "average_empathy_score": 7.8,
    "average_communication_score": 7.5,
    "average_spikes_completion": 8.2,
    "average_overall_score": 7.8
  }
}
```

### POST /v1/admin/cases
Create patient case (admin only).

**Request:**
```json
{
  "title": "New Case",
  "description": "Case description",
  "script": "Full patient scenario...",
  "objectives": "Learning objectives",
  "difficulty_level": "intermediate",
  "category": "oncology",
  "patient_background": "Patient history",
  "expected_spikes_flow": "Expected progression"
}
```

**Response:**
```json
{
  "id": 5,
  "title": "New Case",
  "...": "..."
}
```

---

## Documentation

- Swagger UI: `http://localhost:8000/v1/docs`
- ReDoc: `http://localhost:8000/v1/redoc`
- OpenAPI JSON: `http://localhost:8000/v1/openapi.json`

## Authentication

All endpoints except `/auth/login` and `/auth/register` require authentication.

Include the JWT token in the `Authorization` header:
```
Authorization: Bearer <access_token>
```

