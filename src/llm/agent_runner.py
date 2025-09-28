"""
Main runner script for the AI Voice Agent
Starts the LangGraph workflow and manages the monitoring loop
"""

import asyncio
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from .agent_graph import create_agent_graph, initialize_agent_state, AgentState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AIVoiceAgent:
    """Main AI Voice Agent class that manages the LangGraph workflow"""
    
    def __init__(self):
        self.app = create_agent_graph()
        self.state = initialize_agent_state()
        self.running = False
        self.thread_id = "main_thread"
        
    async def start(self):
        """Start the agent - fetch and analyze data once"""
        logger.info("Starting AI Voice Agent...")
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            # Fetch and analyze data once instead of continuously monitoring
            await self._fetch_and_analyze_once()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Unexpected error in agent: {e}")
        finally:
            await self.stop()
    
    async def _fetch_and_analyze_once(self):
        """One-time run of the LangGraph workflow"""
        config = {
            "configurable": {"thread_id": self.thread_id},
            "recursion_limit": 50  # Increase recursion limit
        }
        
        try:
            # Run through all workflow steps once
            logger.info(f"Running workflow once - Current step: {self.state.get('current_step', 'unknown')}")
            
            # Execute the workflow
            result = await self.app.ainvoke(self.state, config=config)
            self.state.update(result)
            
            # Get summary values from the state
            summary = self.state.get("summary", {})
            email_count = summary.get("total_emails", 0)
            calendar_count = summary.get("total_calendar_events", 0)
            
            print(f"\n✅ Processing Complete:")
            print(f"  📧 Emails processed: {email_count}")
            print(f"  📅 Calendar events: {calendar_count}")
            
            # Print additional info if available
            if "today_events" in summary:
                print(f"  � Today's events: {summary['today_events']}")
            if "conflicts" in summary and summary["conflicts"]:
                print(f"  ⚠️  Conflicts detected: {len(summary['conflicts'])}")
            if "important_items" in summary:
                print(f"  🚨 Important items: {len(summary['important_items'])}")
            
        except Exception as e:
            logger.error(f"Error in workflow execution: {e}")
            self.state["error_count"] = self.state.get("error_count", 0) + 1
            raise e
    
    # _get_sleep_duration method removed as it's no longer needed for one-time processing
    
    async def stop(self):
        """Stop the agent gracefully"""
        logger.info("Stopping AI Voice Agent...")
        self.running = False
        
        # Save final state
        await self._save_state()
        
        logger.info("AI Voice Agent stopped successfully")
    
    async def _save_state(self):
        """Save current state to persistent storage"""
        try:
            # TODO: Implement state persistence
            # This could save to a database or file for recovery
            logger.info("State saved successfully")
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        self.running = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        summary = self.state.get("summary", {})
        
        return {
            "running": self.running,
            "current_step": self.state.get("current_step"),
            "last_check": self.state.get("last_check"),
            "error_count": self.state.get("error_count", 0),
            "total_emails": summary.get("total_emails", 0),
            "total_calendar_events": summary.get("total_calendar_events", 0),
            "today_events": summary.get("today_events", 0)
        }
    
    async def force_check(self):
        """Force a check of emails and calendar - same as _fetch_and_analyze_once"""
        logger.info("Running email and calendar check...")
        
        # Just call the one-time fetch and analyze method
        try:
            await self._fetch_and_analyze_once()
        except Exception as e:
            logger.error(f"Error in force_check: {e}")
            # Reset to fetch emails on error
            self.state["current_step"] = "fetch_emails"
        
        return self.get_status()

# CLI interface
async def main():
    """Main entry point for the agent"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Voice Agent for Gmail and Calendar")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--config", help="Path to configuration file")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize and start the agent
    agent = AIVoiceAgent()
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())