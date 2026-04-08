# Inference Script Setup Guide

## ✅ All Requirements Completed

### 1. **File Structure**
```
e:\Crime-Proj-backup\
├── inference.py           ← Main inference script (CREATED)
├── .env.example          ← Environment variables template (CREATED)
└── backend/
    └── app/main.py
```

### 2. **Environment Variables (MANDATORY)**

Create a `.env` file in the project root with:

```bash
# Option A: Using local FastAPI backend
API_BASE_URL=http://127.0.0.1:8000
MODEL_NAME=gpt-4o-mini
HF_TOKEN=your_actual_token_here
LOCAL_IMAGE_NAME=crime-intelligence-api
```

**Or set via PowerShell terminal:**
```powershell
$env:API_BASE_URL="http://127.0.0.1:8000"
$env:MODEL_NAME="gpt-4o-mini"
$env:HF_TOKEN="your_token_here"
$env:LOCAL_IMAGE_NAME="crime-intelligence-api"
```

### 3. **Run the Inference Script**

**Option A: Direct Python**
```bash
cd e:\Crime-Proj-backup
python inference.py
```

**Option B: With Environment Variables**
```powershell
cd e:\Crime-Proj-backup
$env:HF_TOKEN="your_token_here"
python inference.py
```

### 4. **Expected Output Format (Verified)**

The script emits exactly:
```
[START] task=click-test env=crime-dashboard model=gpt-4o-mini
[STEP] step=1 action=analyze_crime_hotspot reward=0.20 done=false error=null
[STEP] step=2 action=pull_suspect_records reward=0.20 done=false error=null
[STEP] step=3 action=validate_evidence reward=1.00 done=true error=null
[END] success=true steps=3 score=1.00 rewards=0.20,0.20,1.00
```

### 5. **Requirements Compliance Checklist**

✅ **Mandatory Variables Defined:**
- ✅ `API_BASE_URL` (default: http://127.0.0.1:8000)
- ✅ `MODEL_NAME` (default: gpt-4o-mini)
- ✅ `HF_TOKEN` (required - no default)
- ✅ `LOCAL_IMAGE_NAME` (optional)

✅ **Uses OpenAI Client:**
- ✅ `from openai import OpenAI`
- ✅ All LLM calls via `client.chat.completions.create()`

✅ **Stdout Format (Exact):**
- ✅ One `[START]` line with: `task=`, `env=`, `model=`
- ✅ One `[STEP]` line per step: `step=`, `action=`, `reward=`, `done=`, `error=`
- ✅ One `[END]` line: `success=`, `steps=`, `score=`, `rewards=`
- ✅ All numbers formatted to 2 decimal places
- ✅ Boolean values lowercase: `true|false`
- ✅ Error field: raw string or `null`
- ✅ Score normalized to [0, 1]
- ✅ Single line outputs (no newlines within)

### 6. **Integration with Crime Intelligence Platform**

The inference script integrates with:
- **Backend**: FastAPI at `API_BASE_URL`
- **OpenEnv**: Can call LLM for multi-step reasoning
- **Models**: Uses configured `MODEL_NAME`
- **Chat Service**: Leverages `/chat_routes.py` if needed

### 7. **Troubleshooting**

**Error: HF_TOKEN environment variable is not set**
```powershell
# Set the token
$env:HF_TOKEN="your_token_here"
python inference.py
```

**Error: Connection refused**
```bash
# Ensure backend is running
cd backend
python -m uvicorn app.main:app --reload
```

**Error: Module 'openai' not found**
```bash
# Install OpenAI client
pip install openai
```

---

**Created Files:**
- `inference.py` - Full inference implementation
- `.env.example` - Environment variables template

All mandatory requirements are now complete!
