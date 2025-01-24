from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers import trigger, event_log
from app.db import Base, engine

# Initialize the FastAPI app
app = FastAPI(
    title="Event Trigger Platform",
    description="A platform to manage and execute event triggers (Scheduled and API-based).",
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# Include routers
app.include_router(trigger.router, prefix="/triggers", tags=["Triggers"])
app.include_router(event_log.router, prefix="/event-logs", tags=["Event Logs"])

@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint to verify the app is running.
    """
    return {"status": "ok", "message": "Event Trigger Platform is up and running!"}

# health check for db connection

@app.get("/db-health", tags=["Health"])
def db_health_check():
    """
    Health check endpoint to verify the database connection.
    """
    try:
        engine.connect()
        return {"status": "ok", "message": "Database connection is successful!"}
    except Exception as e:
        return {"status": "error", "message": f"Database connection failed: {str(e)}"}


# Configure templates
templates = Jinja2Templates(directory="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})