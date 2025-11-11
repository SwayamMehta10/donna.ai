"""
Quick test script for Phase 4 integration
Tests that the agent worker can start and main.py can run
"""

import subprocess
import sys
import time
import os
from pathlib import Path

def test_agent_worker_standalone():
    """Test if agent worker can start by itself"""
    print("\n" + "="*60)
    print("TEST 1: Agent Worker Standalone")
    print("="*60)
    
    env = os.environ.copy()
    env["AGENT_NAME"] = "donna_agent"
    
    try:
        print("Starting agent worker...")
        process = subprocess.Popen(
            [sys.executable, "src/agents/agent.py", "dev"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit
        time.sleep(5)
        
        # Check if still running
        if process.poll() is None:
            print("✅ Agent worker started successfully")
            print(f"✅ PID: {process.pid}")
            
            # Clean up
            process.terminate()
            process.wait(timeout=5)
            print("✅ Agent worker stopped cleanly")
            return True
        else:
            stdout, stderr = process.communicate()
            print("❌ Agent worker died immediately")
            print(f"STDOUT: {stdout[:500]}")
            print(f"STDERR: {stderr[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_imports():
    """Test if all imports work"""
    print("\n" + "="*60)
    print("TEST 2: Import Checks")
    print("="*60)
    
    try:
        print("Importing main.py modules...")
        from src.telephony.room_management import manage_room
        from src.telephony.telephony import (
            setup_twilio_inbound_call,
            setup_twilio_outbound_call,
            create_livekit_inbound_trunk,
            create_livekit_outbound_trunk,
            create_outbound_call
        )
        from src.api.auth import router as auth_router, get_current_user
        from src.models.user_store import user_store
        
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False


def test_env_variables():
    """Test if required environment variables are set"""
    print("\n" + "="*60)
    print("TEST 3: Environment Variables")
    print("="*60)
    
    required_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER",
        "GROQ_API_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "SECRET_KEY"
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            print(f"❌ Missing: {var}")
            missing.append(var)
        else:
            # Show first few characters only
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"✅ Found: {var} = {masked}")
    
    if missing:
        print(f"\n❌ Missing {len(missing)} required variables")
        return False
    else:
        print(f"\n✅ All {len(required_vars)} variables set")
        return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print(" PHASE 4 INTEGRATION TESTS")
    print("="*70)
    
    # Load .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    results = []
    
    # Test 1: Environment variables
    results.append(("Environment Variables", test_env_variables()))
    
    # Test 2: Imports
    results.append(("Imports", test_imports()))
    
    # Test 3: Agent worker (only if previous tests passed)
    if all(r[1] for r in results):
        results.append(("Agent Worker", test_agent_worker_standalone()))
    else:
        print("\n⚠️  Skipping agent worker test due to previous failures")
    
    # Summary
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + "="*70)
    
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("\nYou can now run: python main.py")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nFix the issues above before running main.py")
    
    print("="*70)


if __name__ == "__main__":
    main()
