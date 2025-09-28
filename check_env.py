"""
Helper script to check environment variables
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
print("Loading .env file...")
load_dotenv(override=True)

# Print LLM-related environment variables
print("\nEnvironment variables for LLM:")
print(f"LLM_PROVIDER: {os.getenv('LLM_PROVIDER')}")
print(f"LLM_MODEL: {os.getenv('LLM_MODEL')}")
print(f"LLM_API_KEY: {os.getenv('LLM_API_KEY')[:5]}...{os.getenv('LLM_API_KEY')[-4:] if os.getenv('LLM_API_KEY') and len(os.getenv('LLM_API_KEY')) > 9 else 'Not set or too short'}")

# Check if key environment variables are set
if not os.getenv('LLM_API_KEY'):
    print("\n❌ LLM_API_KEY is not set in environment")
    
    # Check file content directly to diagnose the issue
    with open('.env', 'r') as f:
        env_content = f.read()
        print("\n.env file content (partial):")
        lines = env_content.splitlines()
        for line in lines[:10]:  # Only show the first few lines
            if "API_KEY" in line:
                # Show line but mask most of the actual key
                if "=" in line:
                    key_parts = line.split("=", 1)
                    if len(key_parts) > 1 and len(key_parts[1]) > 10:
                        masked = key_parts[1][:5] + "..." + key_parts[1][-4:]
                        print(f"{key_parts[0]}={masked}")
                    else:
                        print(line)
                else:
                    print(line)
            else:
                print(line)
else:
    print("\n✅ LLM_API_KEY is properly set in environment")
    
# Check for any syntax issues in .env file
try:
    with open('.env', 'r') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        line = line.strip()
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
            
        # Check for proper KEY=value format
        if '=' not in line:
            print(f"\n❌ Line {i+1} is missing '=' character: {line}")
            continue
            
        # Check for quotes that might cause issues
        if ('"' in line or "'" in line) and not line.startswith('#'):
            print(f"\n❌ Line {i+1} contains quotes which might cause issues: {line}")
            
except Exception as e:
    print(f"\n❌ Error reading .env file: {e}")