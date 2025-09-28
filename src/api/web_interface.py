"""
FastAPI web interface for monitoring and controlling the AI Voice Agent
Provides REST endpoints for status, control, and debugging
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import uvicorn
from datetime import datetime

# Handle relative imports for both module and direct execution
try:
    from ..llm.agent_runner import AIVoiceAgent
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from llm.agent_runner import AIVoiceAgent

# Pydantic models for API
class AgentStatus(BaseModel):
    running: bool
    current_step: Optional[str]
    last_check: Optional[datetime]
    error_count: int
    pending_interactions: int
    pending_actions: int
    active_conflicts: int

class UserCommand(BaseModel):
    command: str
    parameters: Optional[Dict[str, Any]] = None

class ConflictSummary(BaseModel):
    conflict_id: str
    type: str
    severity: str
    description: str
    suggested_action: str

# Initialize FastAPI app
app = FastAPI(
    title="AI Voice Agent API",
    description="Monitor and control the Gmail/Calendar AI Voice Agent",
    version="1.0.0"
)

# Global agent instance
agent_instance: Optional[AIVoiceAgent] = None
agent_task: Optional[asyncio.Task] = None

@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup"""
    global agent_instance
    agent_instance = AIVoiceAgent()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global agent_instance, agent_task
    if agent_instance:
        await agent_instance.stop()
    if agent_task:
        agent_task.cancel()

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "message": "AI Voice Agent API",
        "status": "running",
        "endpoints": {
            "/status": "Get agent status",
            "/start": "Start the agent",
            "/stop": "Stop the agent",
            "/force-check": "Force immediate check",
            "/conflicts": "Get current conflicts",
            "/dashboard": "Web dashboard (HTML)"
        }
    }

@app.get("/status", response_model=AgentStatus)
async def get_status():
    """Get current agent status"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    status = agent_instance.get_status()
    return AgentStatus(**status)

@app.post("/start")
async def start_agent(background_tasks: BackgroundTasks):
    """Start the agent monitoring"""
    global agent_instance, agent_task
    
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    if agent_instance.running:
        return {"message": "Agent is already running"}
    
    # Start agent in background
    agent_task = asyncio.create_task(agent_instance.start())
    background_tasks.add_task(lambda: agent_task)
    
    return {"message": "Agent started successfully"}

@app.post("/stop")
async def stop_agent():
    """Stop the agent monitoring"""
    global agent_instance, agent_task
    
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    await agent_instance.stop()
    
    if agent_task:
        agent_task.cancel()
        agent_task = None
    
    return {"message": "Agent stopped successfully"}

@app.post("/force-check")
async def force_check():
    """Force an immediate check of emails and calendar"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    status = await agent_instance.force_check()
    return {"message": "Forced check completed", "status": status}

@app.get("/conflicts")
async def get_conflicts() -> List[ConflictSummary]:
    """Get current conflicts detected by the agent"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    conflicts = agent_instance.state.get("conflicts", [])
    
    conflict_summaries = []
    for conflict in conflicts:
        conflict_summaries.append(ConflictSummary(
            conflict_id=conflict["conflict_id"],
            type=conflict["type"],
            severity=conflict["severity"],
            description=f"Conflict involving {len(conflict.get('events_involved', []))} events and {len(conflict.get('emails_involved', []))} emails",
            suggested_action=conflict["suggested_action"]
        ))
    
    return conflict_summaries

@app.get("/important-items")
async def get_important_items():
    """Get current important items identified by the agent"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return agent_instance.state.get("important_items", [])

@app.get("/interactions")
async def get_user_interactions():
    """Get recent user interactions"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    interactions = agent_instance.state.get("user_interactions", [])
    
    # Return only recent interactions (last 24 hours)
    recent_interactions = []
    now = datetime.now()
    
    for interaction in interactions:
        if isinstance(interaction.get("timestamp"), datetime):
            time_diff = now - interaction["timestamp"]
            if time_diff.days < 1:
                recent_interactions.append(interaction)
    
    return recent_interactions

@app.post("/simulate-user-response")
async def simulate_user_response(command: UserCommand):
    """Simulate a user response for testing purposes"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # Add a simulated user interaction
    interaction = {
        "interaction_id": f"sim_{datetime.now().timestamp()}",
        "timestamp": datetime.now(),
        "query": "Simulated query",
        "response": command.command,
        "action_requested": command.parameters.get("action", "general"),
        "status": "completed"
    }
    
    agent_instance.state.setdefault("user_interactions", []).append(interaction)
    
    return {"message": "User response simulated", "interaction": interaction}

@app.get("/logs")
async def get_logs(lines: int = 50):
    """Get recent log entries"""
    try:
        with open("agent.log", "r") as f:
            log_lines = f.readlines()
            return {"logs": log_lines[-lines:]}
    except FileNotFoundError:
        return {"logs": ["Log file not found"]}

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Web dashboard for monitoring the agent"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Voice Agent Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .card {
                background: white;
                border-radius: 8px;
                padding: 20px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .status {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .status-indicator {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                display: inline-block;
            }
            .running { background-color: #4CAF50; }
            .stopped { background-color: #f44336; }
            .button {
                background-color: #2196F3;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                margin: 5px;
            }
            .button:hover {
                background-color: #1976D2;
            }
            .error { color: #f44336; }
            .warning { color: #ff9800; }
            .success { color: #4CAF50; }
            .refresh-btn {
                position: fixed;
                top: 20px;
                right: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AI Voice Agent Dashboard</h1>
            
            <button class="button refresh-btn" onclick="refreshData()">Refresh</button>
            
            <div class="card">
                <h2>Agent Status</h2>
                <div class="status" id="status-section">
                    Loading...
                </div>
                <div style="margin-top: 15px;">
                    <button class="button" onclick="startAgent()">Start Agent</button>
                    <button class="button" onclick="stopAgent()">Stop Agent</button>
                    <button class="button" onclick="forceCheck()">Force Check</button>
                </div>
            </div>
            
            <div class="card">
                <h2>Current Conflicts</h2>
                <div id="conflicts-section">Loading...</div>
            </div>
            
            <div class="card">
                <h2>Important Items</h2>
                <div id="important-items-section">Loading...</div>
            </div>
            
            <div class="card">
                <h2>Recent Interactions</h2>
                <div id="interactions-section">Loading...</div>
            </div>
        </div>

        <script>
            async function refreshData() {
                await Promise.all([
                    loadStatus(),
                    loadConflicts(),
                    loadImportantItems(),
                    loadInteractions()
                ]);
            }

            async function loadStatus() {
                try {
                    const response = await fetch('/status');
                    const status = await response.json();
                    
                    const statusHtml = `
                        <div>
                            <span class="status-indicator ${status.running ? 'running' : 'stopped'}"></span>
                            <strong>${status.running ? 'Running' : 'Stopped'}</strong>
                        </div>
                        <div>Current Step: ${status.current_step || 'Unknown'}</div>
                        <div>Last Check: ${status.last_check ? new Date(status.last_check).toLocaleString() : 'Never'}</div>
                        <div class="${status.error_count > 0 ? 'error' : ''}">Errors: ${status.error_count}</div>
                        <div>Pending Interactions: ${status.pending_interactions}</div>
                        <div>Pending Actions: ${status.pending_actions}</div>
                        <div class="${status.active_conflicts > 0 ? 'warning' : ''}">Active Conflicts: ${status.active_conflicts}</div>
                    `;
                    
                    document.getElementById('status-section').innerHTML = statusHtml;
                } catch (error) {
                    document.getElementById('status-section').innerHTML = '<div class="error">Failed to load status</div>';
                }
            }

            async function loadConflicts() {
                try {
                    const response = await fetch('/conflicts');
                    const conflicts = await response.json();
                    
                    if (conflicts.length === 0) {
                        document.getElementById('conflicts-section').innerHTML = '<div class="success">No conflicts detected</div>';
                        return;
                    }
                    
                    const conflictsHtml = conflicts.map(conflict => `
                        <div style="border-left: 4px solid ${conflict.severity === 'critical' ? '#f44336' : conflict.severity === 'high' ? '#ff9800' : '#2196F3'}; padding-left: 10px; margin: 10px 0;">
                            <strong>${conflict.type}</strong> (${conflict.severity})
                            <div>${conflict.description}</div>
                            <div><em>Suggested: ${conflict.suggested_action}</em></div>
                        </div>
                    `).join('');
                    
                    document.getElementById('conflicts-section').innerHTML = conflictsHtml;
                } catch (error) {
                    document.getElementById('conflicts-section').innerHTML = '<div class="error">Failed to load conflicts</div>';
                }
            }

            async function loadImportantItems() {
                try {
                    const response = await fetch('/important-items');
                    const items = await response.json();
                    
                    if (items.length === 0) {
                        document.getElementById('important-items-section').innerHTML = '<div>No important items currently</div>';
                        return;
                    }
                    
                    const itemsHtml = items.map(item => `
                        <div style="border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 4px;">
                            <strong>${item.type}</strong>: ${item.summary}
                            <div><em>Urgency: ${item.urgency}</em></div>
                            ${item.suggested_action ? `<div>Action: ${item.suggested_action}</div>` : ''}
                        </div>
                    `).join('');
                    
                    document.getElementById('important-items-section').innerHTML = itemsHtml;
                } catch (error) {
                    document.getElementById('important-items-section').innerHTML = '<div class="error">Failed to load important items</div>';
                }
            }

            async function loadInteractions() {
                try {
                    const response = await fetch('/interactions');
                    const interactions = await response.json();
                    
                    if (interactions.length === 0) {
                        document.getElementById('interactions-section').innerHTML = '<div>No recent interactions</div>';
                        return;
                    }
                    
                    const interactionsHtml = interactions.map(interaction => `
                        <div style="border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 4px;">
                            <div><strong>${new Date(interaction.timestamp).toLocaleString()}</strong></div>
                            <div>Query: ${interaction.query}</div>
                            <div>Response: ${interaction.response || 'Pending...'}</div>
                            <div>Status: <span class="${interaction.status === 'completed' ? 'success' : interaction.status === 'failed' ? 'error' : 'warning'}">${interaction.status}</span></div>
                        </div>
                    `).join('');
                    
                    document.getElementById('interactions-section').innerHTML = interactionsHtml;
                } catch (error) {
                    document.getElementById('interactions-section').innerHTML = '<div class="error">Failed to load interactions</div>';
                }
            }

            async function startAgent() {
                try {
                    const response = await fetch('/start', { method: 'POST' });
                    const result = await response.json();
                    alert(result.message);
                    setTimeout(refreshData, 1000);
                } catch (error) {
                    alert('Failed to start agent');
                }
            }

            async function stopAgent() {
                try {
                    const response = await fetch('/stop', { method: 'POST' });
                    const result = await response.json();
                    alert(result.message);
                    setTimeout(refreshData, 1000);
                } catch (error) {
                    alert('Failed to stop agent');
                }
            }

            async function forceCheck() {
                try {
                    const response = await fetch('/force-check', { method: 'POST' });
                    const result = await response.json();
                    alert(result.message);
                    setTimeout(refreshData, 2000);
                } catch (error) {
                    alert('Failed to force check');
                }
            }

            // Auto-refresh every 30 seconds
            setInterval(refreshData, 30000);

            // Load initial data
            refreshData();
        </script>
    </body>
    </html>
    """
    return html_content

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the FastAPI server"""
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Voice Agent Web Interface")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    
    args = parser.parse_args()
    
    run_server(args.host, args.port)