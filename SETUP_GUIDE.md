# 🚀 AI Voice Agent - Complete Setup Guide

## 📋 Prerequisites & API Setup

### 1. **Google APIs Setup** (Required)

#### A. Enable Google APIs
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Enable these APIs:
   - Gmail API
   - Google Calendar API

#### B. Create OAuth 2.0 Credentials
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client ID"
3. Choose "Desktop Application"
4. Download the JSON file
5. Place it as:
   - `credentials/gmail_credentials.json` (for Gmail)
   - `credentials/calendar_credentials.json` (for Calendar)

### 2. **Free LLM Service** (Choose One)

#### Option A: Ollama (Local - Recommended for Privacy)
```bash
# Install Ollama
# Windows: Download from https://ollama.ai
# Or use winget
winget install Ollama.Ollama

# Start Ollama and pull a model
ollama pull llama3.2
ollama serve
```

#### Option B: Groq (Cloud - Fast & Free)
1. Sign up at [Groq Console](https://console.groq.com)
2. Generate API key
3. Add to environment variables (see step 4)

### 3. **Voice Service Setup** (Optional)

#### Twilio (for Voice Calls)
1. Sign up at [Twilio Console](https://console.twilio.com)
2. Get free trial account
3. Note: Account SID, Auth Token, Phone Number

### 4. **Environment Configuration**

Create a `.env` file in the project root:

```env
# LLM Configuration
LLM_PROVIDER=ollama                    # Options: ollama, groq
LLM_MODEL=llama3.2                     # For Ollama: llama3.2, mistral, etc.
LLM_API_URL=http://localhost:11434     # Ollama default URL
LLM_API_KEY="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"                           # For Groq: your API key

# Google API Credentials
GMAIL_CREDENTIALS_PATH=credentials/gmail_credentials.json
GMAIL_TOKEN_PATH=credentials/gmail_token.json
CALENDAR_CREDENTIALS_PATH=credentials/calendar_credentials.json
CALENDAR_TOKEN_PATH=credentials/calendar_token.json

# Twilio Configuration (Optional)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
USER_PHONE_NUMBER=+1987654321

# Monitoring Settings
CHECK_INTERVAL=300                     # Check every 5 minutes
MAX_EMAILS=50                         # Max emails to fetch per check
TIMEZONE=America/New_York
```

### 5. **Directory Structure Setup**

Create these directories:
```bash
mkdir credentials
mkdir logs
```

---

## 🏃‍♂️ Running the Application

### 1. **Install Dependencies**
```bash
# Activate virtual environment
.\myenv\Scripts\activate

# All dependencies should already be installed, but if needed:
pip install -r requirements.txt
```

### 2. **First-Time OAuth Setup**
```bash
# Run the application - it will open browser for OAuth
python -m src.main

# Or from the src directory:
cd src
python main.py
```

The first run will:
1. Open browser windows for Gmail and Calendar OAuth
2. Ask for permissions
3. Save tokens automatically

### 3. **Access the Dashboard**
- Web Interface: `http://localhost:8000`
- API Endpoints: `http://localhost:8000/docs`

---

## 🔄 Application Flow

### **Phase 1: Data Collection** 
```
Gmail API ──┐
            ├─► LangGraph State Manager
Calendar ───┘
```

### **Phase 2: AI Analysis**
```
Emails ──┐
         ├─► Free LLM (Ollama/Groq) ──► Importance Scores
Events ──┘                              Action Items
```

### **Phase 3: Conflict Detection**
```
Calendar Events ──► Conflict Detector ──► Schedule Issues
Email Requests ──┘                       Meeting Conflicts
```

### **Phase 4: User Interaction**
```
Critical Issues ──► Voice Call (Twilio) ──► User Response
                    │                       │
                    └─► Console Fallback ───┘
```

### **Phase 5: Action Execution**
```
User Decisions ──► Schedule Updates
              ├─► Email Responses  
              └─► Meeting Reschedules
```

---

## 🎮 Usage Examples

### **Scenario 1: Meeting Conflict**
1. Agent detects overlapping meetings
2. Calls user: "You have a conflict at 2 PM - client meeting and dentist appointment"
3. User responds: "Reschedule the dentist"
4. Agent updates calendar and sends notifications

### **Scenario 2: Urgent Email**
1. Important email from boss with "URGENT" in subject
2. Agent calls: "You received an urgent email about the project deadline"
3. User: "Schedule a team meeting for tomorrow"
4. Agent creates calendar event and invites team

### **Scenario 3: Daily Summary**
1. Agent runs every 5 minutes
2. Finds 3 new emails, 1 calendar update
3. No conflicts → continues monitoring
4. Web dashboard shows current status

---

## 🛠️ Configuration Options

### **LLM Providers**
- **Ollama**: Best for privacy, runs locally
- **Groq**: Fastest inference, requires internet
- **OpenAI Compatible**: Any API following OpenAI format

### **Monitoring Frequency**
- Default: 5 minutes
- Adjust `CHECK_INTERVAL` in .env
- Shorter intervals = faster response, more API calls

### **Voice Options**
- **Twilio**: Professional voice calls
- **Console**: Text-based fallback for testing
- **Future**: Local TTS integration

---

## 🔧 Troubleshooting

### **Common Issues**

#### Import Errors
```bash
# Run as module to fix relative imports
python -m src.main

# Or set PYTHONPATH
set PYTHONPATH=.
python src/main.py
```

#### OAuth Issues
```bash
# Delete token files to re-authenticate
rm credentials/*_token.json
```

#### LLM Connection Issues
```bash
# For Ollama, ensure it's running
ollama serve

# Test connection
curl http://localhost:11434/api/tags
```

#### Missing Dependencies
```bash
# Reinstall all packages
pip install -r requirements.txt
```

---

## 📊 Monitoring & Logs

### **Web Dashboard**
- Status: `http://localhost:8000`
- Recent activity, conflicts, pending actions
- Manual controls for testing

### **Log Files**
- `logs/agent.log` - Application logs
- `logs/api.log` - API access logs

### **API Testing**
- FastAPI docs: `http://localhost:8000/docs`
- Test endpoints directly

---

## 🚀 Production Deployment

### **For 24-Hour Hackathon**
1. Use Groq for fast LLM responses
2. Configure shorter check intervals (1-2 minutes)
3. Use console notifications for demo
4. Focus on core conflict detection

### **For Real Usage**
1. Set up proper OAuth consent screen
2. Use production Twilio account
3. Implement proper error handling
4. Add user authentication

---

## 🎯 Key Features Implemented

✅ **LangGraph Workflow** - 10-node state machine  
✅ **Gmail Integration** - OAuth2, email analysis  
✅ **Calendar Integration** - Event fetching, conflict detection  
✅ **Free LLM Analysis** - Ollama/Groq support  
✅ **Voice Calling** - Twilio integration  
✅ **Web Dashboard** - FastAPI interface  
✅ **Async Processing** - Non-blocking operations  
✅ **Error Handling** - Circuit breakers, retries  
✅ **Type Safety** - Full typing with TypedDict  

Ready to run your AI voice agent! 🤖📞