# 📡 API ENDPOINT REFERENCE - Police Intelligence System

## Authentication
All endpoints require JWT Bearer token:
```
Authorization: Bearer <jwt_token>
```

Role requirement: `police` or `admin`

---

## DISPATCH & RESOURCE MANAGEMENT (6 endpoints)

### 1. Auto-Assign Case to Officer
```
POST /dispatch/auto-assign
Content-Type: application/json

Request:
{
  "case_id": 1,
  "auto_assign": true
}

Response (200):
{
  "success": true,
  "message": "Case assigned to BADGE-001",
  "dispatch": {
    "id": 1,
    "case_id": 1,
    "assigned_officer": "BADGE-001",
    "estimated_arrival": 8,
    "status": "assigned"
  }
}
```

### 2. Get Dispatch Queue
```
GET /dispatch/queue?status=pending

Query Parameters:
  - status: pending | assigned | en_route | on_scene | completed (optional)

Response (200):
[
  {
    "id": 1,
    "case_id": 1,
    "status": "assigned",
    "officer_badge": "BADGE-001",
    "estimated_arrival": 8,
    "created_at": "2024-01-15T10:30:00Z",
    "assigned_at": "2024-01-15T10:32:00Z"
  }
]
```

### 3. List Available Officers
```
GET /dispatch/officers

Response (200):
[
  {
    "id": 1,
    "badge_id": "BADGE-001",
    "status": "available",
    "workload": 1,
    "current_location": "Mumbai Downtown",
    "latitude": 19.076,
    "longitude": 72.877,
    "shift": "day",
    "rank": "Officer"
  }
]
```

### 4. Complete Dispatch
```
POST /dispatch/complete/1

Response (200):
{
  "success": true,
  "message": "Dispatch completed and officer released"
}
```

### 5. Get Dispatch Details
```
GET /dispatch/1

Response (200):
{
  "id": 1,
  "case": {
    "id": 1,
    "case_id": "CASE-2024-001",
    "crime_type": "Robbery",
    "location": "Mumbai Downtown",
    "severity": "high"
  },
  "officer": {
    "id": 1,
    "badge_id": "BADGE-001",
    "location": "Mumbai Downtown"
  },
  "status": "assigned",
  "estimated_arrival": 8,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 6. Get Officer Dispatch Statistics
```
GET /dispatch/stats/1

Response (200):
{
  "officer_id": 1,
  "badge_id": "BADGE-001",
  "current_status": "available",
  "workload": 1,
  "total_dispatches": 15,
  "completed_dispatches": 14,
  "active_dispatches": 1,
  "location": {
    "latitude": 19.076,
    "longitude": 72.877,
    "description": "Mumbai Downtown"
  }
}
```

---

## CASE INTELLIGENCE & PATTERN DETECTION (7 endpoints)

### 1. Get Case Intelligence Report
```
GET /cases/intelligent/1

Response (200):
{
  "case": {
    "id": 1,
    "case_id": "CASE-2024-001",
    "crime_type": "Robbery",
    "description": "Jewelry store robbery",
    "location": "Mumbai Downtown",
    "severity": "high",
    "status": "investigating",
    "incident_time": "2024-01-15T08:30:00Z",
    "assigned_officer_id": 1
  },
  "similar_cases": [
    {
      "id": 2,
      "case_id": "CASE-2024-002",
      "crime_type": "Robbery",
      "location": "Mumbai Harbor",
      "similarity_score": 0.82,
      "severity": "high"
    }
  ],
  "linked_cases": [
    {
      "link_id": 1,
      "link_type": "series",
      "similarity_score": 0.87,
      "confirmed": false,
      "linked_case": {...},
      "reason": "Auto-detected series pattern"
    }
  ],
  "evidence_count": 3,
  "evidence": [...]
}
```

### 2. Find Similar Cases
```
GET /cases/similar/1?threshold=0.7

Query Parameters:
  - threshold: 0.0-1.0 (optional, default 0.7)

Response (200):
{
  "case_id": 1,
  "similar_cases_found": 2,
  "similar_cases": [
    {
      "id": 2,
      "case_id": "CASE-2024-002",
      "crime_type": "Robbery",
      "location": "Mumbai Harbor",
      "incident_time": "2024-01-14T20:15:00Z",
      "similarity_score": 0.82,
      "severity": "high"
    }
  ]
}
```

### 3. Get Linked Cases
```
GET /cases/linked/1

Response (200):
{
  "case_id": 1,
  "linked_count": 2,
  "links": [
    {
      "link_id": 1,
      "link_type": "series",
      "similarity_score": 0.87,
      "confirmed": false,
      "linked_case": {
        "id": 2,
        "case_id": "CASE-2024-002",
        "crime_type": "Robbery",
        "location": "Mumbai Harbor",
        "incident_time": "2024-01-14T20:15:00Z"
      },
      "reason": "Auto-detected series pattern"
    }
  ]
}
```

### 4. Manually Link Cases
```
POST /cases/link
Content-Type: application/json

Request:
{
  "case_id_1": 1,
  "case_id_2": 2,
  "link_type": "series",
  "reason": "Same jewelry store targets, same MO"
}

Response (200):
{
  "success": true,
  "link_id": 1,
  "message": "Cases linked as series"
}
```

### 5. List Potential Serial Crimes
```
GET /cases/serial

Response (200):
{
  "potential_series_found": 1,
  "series": [
    {
      "primary_case_id": "CASE-2024-001",
      "crime_type": "Robbery",
      "case_count": 3,
      "severity": "high",
      "location": "Mumbai Downtown",
      "cases": [
        {
          "id": 1,
          "case_id": "CASE-2024-001",
          "incident_time": "2024-01-15T08:30:00Z"
        }
      ]
    }
  ]
}
```

### 6. Log Evidence Chain Action
```
POST /evidence/1/chain
Content-Type: application/json

Request:
{
  "action": "viewed"
}

Response (200):
{
  "success": true,
  "message": "Evidence action logged: viewed",
  "timestamp": "2024-01-15T10:45:00Z"
}
```

### 7. Get Evidence Chain of Custody
```
GET /evidence/1/chain

Response (200):
{
  "evidence_id": 1,
  "chain_entries": 3,
  "chain": [
    {
      "timestamp": "2024-01-15T08:45:00Z",
      "officer_id": 1,
      "action": "uploaded"
    },
    {
      "timestamp": "2024-01-15T09:30:00Z",
      "officer_id": 4,
      "action": "viewed"
    }
  ]
}
```

---

## SUSPECT DATABASE & CRIMINAL INTELLIGENCE (8 endpoints)

### 1. Create New Suspect
```
POST /suspects
Content-Type: application/json

Request:
{
  "name": "John Doe",
  "description": "Height: 5'10, Athletic build",
  "age": 28,
  "photo_url": "https://...",
  "primary_crimes": ["Theft", "Robbery"],
  "modus_operandi": "Targets jewelry stores at night"
}

Response (200):
{
  "success": true,
  "suspect_id": "SUSP-20240115101500",
  "message": "Suspect John Doe created"
}
```

### 2. Search Suspects
```
GET /suspects/search?q=raj&search_type=name

Query Parameters:
  - q: search query (min 2 chars) REQUIRED
  - search_type: name | description | modus_operandi | all (optional, default: all)

Response (200):
{
  "query": "raj",
  "search_type": "name",
  "results_count": 1,
  "suspects": [
    {
      "id": 1,
      "suspect_id": "SUSP-2024-001",
      "name": "Raj Kumar",
      "age": 28,
      "description": "Height: 5'10\"",
      "photo_url": "...",
      "risk_score": 0.85,
      "is_wanted": true,
      "primary_crimes": ["Theft", "Robbery"]
    }
  ]
}
```

### 3. Get Suspect Intelligence
```
GET /suspects/1

Response (200):
{
  "id": 1,
  "suspect_id": "SUSP-2024-001",
  "name": "Raj Kumar",
  "age": 28,
  "description": "Height: 5'10\", Medium build, Tattoo on left arm",
  "photo_url": "...",
  "arrest_count": 5,
  "conviction_count": 2,
  "primary_crimes": ["Theft", "Robbery"],
  "modus_operandi": "Targets jewelry stores, operates at night",
  "risk_score": 0.85,
  "recidivism_probability": 0.87,
  "gang_affiliated": true,
  "gang_name": "Downtown Gang",
  "is_wanted": true,
  "warrant_type": "felony",
  "last_seen": "2024-01-14T20:15:00Z",
  "last_location": "Mumbai Downtown",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T09:00:00Z"
}
```

### 4. Register Arrest
```
POST /suspects/1/arrest
Content-Type: application/json

Request:
{
  "crime_type": "Robbery",
  "case_id": 1
}

Response (200):
{
  "success": true,
  "suspect_id": "SUSP-2024-001",
  "arrest_count": 6,
  "recidivism_risk": 0.89,
  "message": "Arrest registered for Raj Kumar"
}
```

### 5. Register Conviction
```
POST /suspects/1/conviction
Content-Type: application/json

Request:
{
  "crime_type": "Robbery"
}

Response (200):
{
  "success": true,
  "suspect_id": "SUSP-2024-001",
  "conviction_count": 3,
  "recidivism_risk": 0.91,
  "message": "Conviction registered for Raj Kumar"
}
```

### 6. Mark as Wanted
```
POST /suspects/1/wanted
Content-Type: application/json

Request:
{
  "warrant_type": "felony"
}

Response (200):
{
  "success": true,
  "suspect_id": "SUSP-2024-001",
  "is_wanted": true,
  "warrant_type": "felony",
  "message": "Raj Kumar marked as wanted for felony"
}
```

### 7. List Wanted Suspects
```
GET /suspects/wanted/list

Response (200):
{
  "wanted_count": 3,
  "suspects": [
    {
      "id": 1,
      "suspect_id": "SUSP-2024-001",
      "name": "Raj Kumar",
      "age": 28,
      "photo_url": "...",
      "warrant_type": "felony",
      "last_seen": "2024-01-14T20:15:00Z",
      "last_location": "Mumbai Downtown",
      "primary_crimes": ["Theft", "Robbery"],
      "risk_score": 0.85
    }
  ]
}
```

### 8. List High-Risk Suspects
```
GET /suspects/risk/high?threshold=0.7

Query Parameters:
  - threshold: 0.0-1.0 (optional, default 0.7)

Response (200):
{
  "risk_threshold": 0.7,
  "high_risk_count": 3,
  "suspects": [
    {
      "id": 3,
      "suspect_id": "SUSP-2024-003",
      "name": "Vikram Mehta",
      "arrest_count": 8,
      "conviction_count": 3,
      "recidivism_risk": 0.92,
      "primary_crimes": ["Assault", "Robbery"],
      "gang_affiliated": true
    }
  ]
}
```

### 9. Get Gang Members & Network
```
GET /suspects/gang/Downtown%20Gang

Response (200):
{
  "gang_name": "Downtown Gang",
  "member_count": 2,
  "members": [
    {
      "id": 1,
      "suspect_id": "SUSP-2024-001",
      "name": "Raj Kumar",
      "risk_score": 0.85,
      "primary_crimes": ["Theft", "Robbery"],
      "last_location": "Mumbai Downtown"
    }
  ]
}
```

---

## ERROR RESPONSES

### 403 Forbidden (No Permission)
```json
{
  "detail": "Not authenticated or insufficient permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 400 Bad Request
```json
{
  "detail": "Invalid request body or parameters"
}
```

---

## USAGE EXAMPLES

### Example 1: Complete Dispatch Workflow
```bash
# 1. Get available officers
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/dispatch/officers

# 2. Auto-dispatch a case
curl -X POST http://localhost:8000/dispatch/auto-assign \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"case_id": 1}'

# 3. Check dispatch status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/dispatch/queue

# 4. Complete dispatch when done
curl -X POST http://localhost:8000/dispatch/complete/1 \
  -H "Authorization: Bearer $TOKEN"
```

### Example 2: Investigate Serial Crimes
```bash
# 1. Find similar cases
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/cases/similar/1

# 2. Check for serial crime patterns
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/cases/serial

# 3. Manually link related cases
curl -X POST http://localhost:8000/cases/link \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "case_id_1": 1,
    "case_id_2": 2,
    "link_type": "series",
    "reason": "Same MO and timeline"
  }'
```

### Example 3: Criminal Intelligence
```bash
# 1. Search for suspects
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/suspects/search?q=john&search_type=name"

# 2. Get suspect intelligence
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/suspects/1

# 3. Register arrest
curl -X POST http://localhost:8000/suspects/1/arrest \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"crime_type": "Robbery", "case_id": 1}'

# 4. Check high-risk suspects
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/suspects/risk/high?threshold=0.75"
```

---

**API Version:** 3.0.0
**Last Updated:** April 8, 2026
**Status:** ✅ Production Ready
