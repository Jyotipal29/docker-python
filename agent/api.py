import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import asyncio
import logging
from contextlib import asynccontextmanager
import uvicorn

# Import from your twitter_bot.py file
from agent.twitter_bot import (
    browser_launcher,
    run_bot_session,
    main_bot_loop,
    BOT_TASKS,
    BROWSER_SESSIONS
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("twitter-bot-api")

# Pydantic models for API requests and responses
class BotResponse(BaseModel):
    session_id: str
    status: str
    message: str





# Set up application lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown - clean up browser sessions and running tasks
    for task_id, task_info in list(BOT_TASKS.items()):
        if task_info.get("running", False):
            task_info["running"] = False
            logger.info(f"Stopping bot task {task_id}")
    
    for session_id, page in list(BROWSER_SESSIONS.items()):
        try:
            if not page.is_closed():
                await page.close()
                logger.info(f"Closed browser session {session_id}")
        except Exception as e:
            logger.error(f"Error closing browser session {session_id}: {e}")

# Initialize FastAPI
app = FastAPI(
    title="Twitter Bot API",
    description="API to control Twitter engagement bot",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dictionary to map session_ids to background tasks
running_tasks = {}

@app.get("/")
async def root():
    """Root endpoint to check if the API is running"""
    return {"status": "Twitter Bot API is running", "version": "1.0.0"}



@app.post("/start", response_model=BotResponse)
async def start_bot(background_tasks: BackgroundTasks):
    """Start the Twitter bot"""
    try:
        # First make sure no existing bots are running
        await stop_bot()
        
        # Launch a new browser session
        session_id = await browser_launcher()
        
        if session_id.startswith("browser_error"):
            raise HTTPException(status_code=500, detail=f"Failed to launch browser: {session_id}")
        
        # Initialize the agent
        session_id, agent_executor = await run_bot_session(session_id)
        
        # Create a new task ID
        task_id = str(uuid.uuid4())
        
        # Create a tracking record before starting
        BOT_TASKS[task_id] = {
            "session_id": session_id,
            "running": True,
            "start_time": asyncio.get_event_loop().time(),
            "task": None  # Will be filled by the actual task
        }
        
        # Create and store the actual task
        task = asyncio.create_task(main_bot_loop(session_id, agent_executor))
        BOT_TASKS[task_id]["task"] = task
        
        return {
            "session_id": session_id,
            "status": "started",
            "message": "Twitter bot started successfully"
        }
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")


@app.post("/stop", response_model=BotResponse)
async def stop_bot():
    """Stop the running Twitter bot and close the browser"""
    try:
        # First, set all running flags to false
        for task_id, task_info in list(BOT_TASKS.items()):
            BOT_TASKS[task_id]["running"] = False
            
            # If there's a task object that's cancelable, cancel it
            if "task" in task_info and task_info["task"] and not task_info["task"].done():
                task_info["task"].cancel()
                logger.info(f"Canceled running task {task_id}")
        
        # Give tasks a moment to handle cancellation before closing browser
        await asyncio.sleep(0.5)
        
        # Close all browser sessions
        browser_closed = False
        for session_id, page in list(BROWSER_SESSIONS.items()):
            try:
                if not page.is_closed():
                    # Try to get the browser through context
                    context = page.context
                    browser = context.browser if context else None
                    
                    # Close page
                    await page.close()
                    
                    # Close context
                    if context:
                        await context.close()
                    
                    # Close browser
                    if browser:
                        await browser.close()
                        
                    logger.info(f"Closed Twitter browser")
                    browser_closed = True
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            
            # Only need to process the first one since there's only one browser
            break
        
        # Give a moment for tasks to fully stop before clearing dictionaries
        await asyncio.sleep(0.5)
        
        # Now clear the dictionaries
        BROWSER_SESSIONS.clear()
        BOT_TASKS.clear()
        
        status_message = "Twitter bot stopped and browser closed" if browser_closed else "Twitter bot stopped"
        
        return {
            "session_id": "main",
            "status": "stopped",
            "message": status_message
        }
    except Exception as e:
        logger.error(f"Error stopping bot: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error stopping bot: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)