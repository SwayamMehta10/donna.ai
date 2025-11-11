"""
Web Portal Server - Dashboard and Authentication
Port: 8020
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
import os
import aiohttp
import asyncio

import logging
load_dotenv()
from src.utils.mylogger import logging

# Import auth router and user store
from src.api.auth import router as auth_router, get_current_user
from src.models.user_store import user_store

# Initialize FastAPI app
app = FastAPI(title="Donna.ai - Web Portal")

# Add session middleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Include auth router
app.include_router(auth_router)


# ============= WEB PORTAL ROUTES =============

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve login page"""
    user = await get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard")
    
    with open("frontend/login.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve dashboard page"""
    print("=== Dashboard route accessed ===")
    print(f"Session data: {request.session}")
    
    user = await get_current_user(request)
    print(f"User retrieved in dashboard: {bool(user)}")
    
    if not user:
        print("No user found, redirecting to login")
        return RedirectResponse(url="/")
    
    print(f"User {user.get('email')} accessing dashboard")
    with open("frontend/dashboard.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/activate-agent")
async def activate_agent(request: Request):
    """
    Activate Donna - triggers src/main.py to fetch context and initiate call
    """
    print("\n" + "="*60)
    print("ACTIVATE-AGENT ENDPOINT CALLED")
    print("="*60)
    
    try:
        # Step 1: Get current user
        print("Step 1: Getting current user...")
        user = await get_current_user(request)
        print(f"User result: {user}")
        
        if not user:
            print("ERROR: No user found in session")
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        print(f"Step 2: User authenticated - {user['email']}")
        
        # Check if user has phone number
        if not user.get('phone'):
            print(f"ERROR: User {user['email']} has no phone number")
            raise HTTPException(status_code=400, detail="Please add your phone number first")
        
        print(f"Step 3: User phone validated - {user['phone']}")
        
        # Step 4: Call src/main.py API to fetch context and initiate call
        print("Step 4: Calling src/main.py to fetch context and initiate call...")
        
        context_fetcher_url = "http://localhost:8000/fetch-and-call"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    context_fetcher_url,
                    json={
                        "unique_code": user.get('user_id', user.get('unique_code', 'user123')),
                        "name": user.get('name', user.get('email').split('@')[0]),
                        "phone": user['phone'],
                        "email": user.get('email')
                    },
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as response:
                    result = await response.json()
                    print(f"Context fetcher response: {result}")
                    
                    if response.status == 200 and result.get("status") == "success":
                        print(f"SUCCESS: Call initiated to {user['phone']}")
                        return {
                            "message": "Agent activated! You should receive a call shortly.",
                            "phone": user['phone']
                        }
                    else:
                        error_msg = result.get("message", "Unknown error")
                        print(f"ERROR: Call failed - {error_msg}")
                        raise HTTPException(status_code=500, detail=f"Failed to activate agent: {error_msg}")
                        
            except aiohttp.ClientConnectorError:
                print("ERROR: Cannot connect to src/main.py server on port 8000")
                raise HTTPException(
                    status_code=503, 
                    detail="Context fetcher service not available. Please ensure src/main.py is running on port 8000"
                )
            except asyncio.TimeoutError:
                print("ERROR: Request to src/main.py timed out")
                raise HTTPException(status_code=504, detail="Request timed out while fetching context")
            
    except HTTPException as http_ex:
        print(f"HTTPException caught: {http_ex.detail}")
        raise
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "web_portal"}


# Run the application 
if __name__ == "__main__":
    import uvicorn
    print("Starting Web Portal on port 8020...")
    uvicorn.run(app, host="0.0.0.0", port=8020)
