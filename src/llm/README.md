# AI Voice Agent - LangGraph Implementation

This directory contains the LangGraph implementation for the AI Voice Agent that monitors Gmail and Calendar events.

## Architecture Overview

The agent is built using LangGraph as a state machine with the following nodes:

1. **fetch_emails_node** - Fetches new emails from Gmail API
2. **fetch_calendar_node** - Fetches calendar events from Google Calendar API  
3. **analyze_emails_node** - Uses LLM to analyze email importance and required actions
4. **analyze_calendar_node** - Uses LLM to analyze calendar event importance
5. **detect_conflicts_node** - Detects scheduling conflicts and issues
6. **prepare_user_interaction_node** - Prepares summary for user notification
7. **call_user_node** - Initiates voice call to user
8. **process_user_response_node** - Processes user's voice response
9. **execute_actions_node** - Executes user-requested actions
10. **monitor_node** - Returns to monitoring mode

## State Management

The agent maintains state using TypedDict classes:

- **AgentState** - Main state container
- **EmailData** - Individual email information
- **CalendarEvent** - Individual calendar event information  
- **UserInteraction** - User interaction records
- **Conflict** - Detected conflict information

## Key Features

### Continuous Monitoring
- Automatically fetches emails every 5 minutes
- Checks calendar events every 15 minutes
- Responds to user input within 30 seconds

### Intelligent Analysis
- Uses free LLM (like Ollama) to analyze importance
- Detects conflicts between meetings and travel time
- Prioritizes urgent items requiring immediate attention

### Voice Interaction
- Calls user when critical issues are detected
- Processes natural language responses
- Executes actions based on user decisions

### Web Dashboard
- Real-time monitoring interface at `/dashboard`
- REST API for external integrations
- Status monitoring and control endpoints

## Usage

### Starting the Agent
```python
from src.llm.agent_runner import AIVoiceAgent
import asyncio

agent = AIVoiceAgent()
asyncio.run(agent.start())
```

### Using the Web Interface
```python
from src.api.web_interface import run_server

# Start web server on localhost:8000
run_server()
```

### API Endpoints

- `GET /status` - Get agent status
- `POST /start` - Start agent monitoring
- `POST /stop` - Stop agent
- `POST /force-check` - Force immediate check
- `GET /conflicts` - Get current conflicts
- `GET /dashboard` - Web dashboard

## Configuration

The agent requires:

1. **Gmail API credentials** - For email access
2. **Google Calendar API credentials** - For calendar access
3. **LLM setup** - Free LLM like Ollama or Groq
4. **Voice service** - For calling users (Twilio, etc.)

## Error Handling

- Automatic retry on transient failures
- Error counting with circuit breaker
- Graceful degradation when services are unavailable
- Persistent state recovery

## Development Notes

This is designed for a 24-hour hackathon with:
- Minimal external dependencies
- Free/open-source tools only
- Rapid development and debugging
- Clear separation of concerns

The LangGraph structure makes it easy to:
- Debug workflow issues
- Add new nodes or modify existing ones
- Visualize the agent's decision flow
- Handle complex state transitions