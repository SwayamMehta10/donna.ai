# AI Voice Agent - LangGraph Implementation

A comprehensive AI agent that monitors Gmail and Google Calendar, identifies important events and conflicts, and interacts with users via voice calls to manage their schedule.

## 🎯 Project Overview

This hackathon project creates an intelligent voice assistant that:
- 📧 Monitors Gmail for important emails
- 📅 Tracks Google Calendar events  
- 🤖 Uses free LLM to analyze importance and detect conflicts
- 📞 Calls users when action is needed
- 🔄 Executes user requests automatically

## 🏗️ Architecture

Built using **LangGraph** for workflow orchestration:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Fetch Emails   │────│ Analyze Emails  │────│ Detect Conflicts│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Fetch Calendar  │────│Analyze Calendar │────│ User Interaction│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │ Execute Actions │
                                               └─────────────────┘
```

## 🛠️ Tech Stack (All Free!)

### Core Framework
- **LangGraph** - Workflow orchestration
- **FastAPI** - Web interface and API
- **Python 3.9+** - Main language

### APIs & Services  
- **Gmail API** - Email access
- **Google Calendar API** - Calendar management
- **Twilio** - Voice calls (free tier)

### Free LLM Options
- **Ollama** - Local LLM (recommended)
- **Groq** - Free cloud LLM
- **Together AI** - Free tier available

### Additional Tools
- **Pydantic** - Data validation
- **AsyncIO** - Async operations
- **Rich** - Beautiful console output

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone <your-repo>
cd personal_assistant

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Credentials

Create `credentials/` folder and add:
- `gmail_credentials.json` - Gmail API credentials
- `calendar_credentials.json` - Calendar API credentials

### 3. Configure Environment

```bash
# Copy example configuration
copy src\config\settings_example.py src\config\settings.py

# Create .env file from example
python src\config\settings_example.py
copy .env.example .env
```

Edit `.env` with your settings:
```env
# LLM (choose one)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2

# Phone settings
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
USER_PHONE_NUMBER=+1234567890
```

### 4. Setup Free LLM

**Option A: Ollama (Recommended)**
```bash
# Install Ollama
winget install Ollama.Ollama

# Pull model
ollama pull llama3.2
```

**Option B: Groq (Cloud)**
1. Sign up at https://groq.com
2. Get free API key
3. Set `LLM_PROVIDER=groq` in .env

### 5. Run the Agent

```bash
# Start the agent
python src\main_example.py

# Or run web interface only
python src\api\web_interface.py
```

## 📊 Web Dashboard

Access the dashboard at: http://localhost:8000/dashboard

Features:
- Real-time agent status
- Current conflicts and important items
- User interaction history
- Control buttons (start/stop/force check)

## 🔧 Configuration

### Email Monitoring
- Checks Gmail every 5 minutes
- Analyzes importance using LLM
- Detects action-required emails

### Calendar Analysis  
- Monitors next 7 days of events
- Detects scheduling conflicts
- Calculates travel time issues

### User Interaction
- Calls user for critical issues
- 5-minute response timeout
- Natural language processing

## 📁 Project Structure

```
personal_assistant/
├── src/
│   ├── llm/
│   │   ├── agent_graph.py      # Main LangGraph workflow
│   │   ├── agent_runner.py     # Agent execution logic
│   │   └── README.md           # LangGraph documentation
│   ├── api/
│   │   ├── web_interface.py    # FastAPI web interface
│   │   ├── gmail.py            # Gmail API integration
│   │   └── calendar.py         # Calendar API integration
│   ├── services/
│   │   ├── conflict_detector.py # Conflict detection logic
│   │   ├── notification.py     # Voice calling service
│   │   └── scheduler.py        # Action execution
│   ├── config/
│   │   └── settings_example.py # Configuration template
│   └── main_example.py         # Example usage
├── credentials/                # API credentials (create manually)
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

## 🎯 Hackathon Focus

Designed for rapid development:

### Phase 1 (Hours 1-8): Core Setup
- [x] LangGraph workflow implementation
- [x] Gmail/Calendar API integration
- [x] Basic LLM analysis
- [x] Web dashboard

### Phase 2 (Hours 9-16): Intelligence
- [ ] Advanced conflict detection
- [ ] Voice calling integration
- [ ] Natural language processing
- [ ] Action execution

### Phase 3 (Hours 17-24): Polish
- [ ] Error handling and resilience
- [ ] UI improvements  
- [ ] Demo preparation
- [ ] Documentation

## 🔍 Key Features

### Intelligent Analysis
- **Email Importance**: Uses LLM to score emails (0-1)
- **Conflict Detection**: Identifies scheduling overlaps
- **Priority Assessment**: Determines what needs immediate attention

### Voice Interaction
- **Proactive Calls**: Calls user when conflicts detected
- **Natural Language**: Processes voice responses with LLM
- **Action Execution**: Reschedules meetings, sends emails

### Monitoring Dashboard
- **Real-time Status**: Live agent status and metrics
- **Conflict Visualization**: Clear conflict summaries
- **Control Interface**: Start/stop/force check buttons

## 🚨 Troubleshooting

### Common Issues

**Agent won't start:**
```bash
# Check LLM service
ollama list  # For Ollama
curl http://localhost:11434  # Test Ollama

# Check credentials
ls credentials/
```

**No emails/events:**
```bash
# Test API access
python -c "from src.api.gmail import test_connection; test_connection()"
```

**LLM errors:**
```bash
# For Ollama
ollama ps  # Check running models
ollama pull llama3.2  # Re-download if needed
```

### Debug Mode
```bash
# Enable debug logging
DEBUG_MODE=true python src\main_example.py
```

## 📞 Voice Integration Options

### Free Tiers Available:
1. **Twilio** - $15 free credit
2. **Vonage** - €2 free credit  
3. **Plivo** - $5 free credit

### Setup Example (Twilio):
```python
# In .env file
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_PHONE_NUMBER=+1234567890
USER_PHONE_NUMBER=+0987654321
```

## 🏆 Demo Script

For hackathon presentation:

1. **Show Dashboard** - Real-time monitoring
2. **Simulate Conflict** - Add overlapping meetings
3. **Voice Interaction** - Demonstrate calling feature
4. **Action Execution** - Show automatic rescheduling
5. **Analytics** - Display conflict resolution stats

## 🤝 Contributing

For hackathon collaboration:

1. **Fork the repository**
2. **Create feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit changes** (`git commit -m 'Add amazing feature'`)
4. **Push to branch** (`git push origin feature/amazing-feature`)
5. **Open Pull Request**

## 📝 License

MIT License - Perfect for hackathon projects!

## 🙏 Acknowledgments

- **LangGraph** - Amazing workflow framework
- **Ollama** - Free local LLM hosting
- **FastAPI** - Lightning-fast web framework
- **Google APIs** - Reliable email/calendar access

---

**Built with ❤️ for hackathons!** 🚀