from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import socketio
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Socket.IO and FastAPI setup
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=["http://localhost:5175"])
app = FastAPI()
socketio_app = socketio.ASGIApp(sio, other_asgi_app=app)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for form data
class FormData(BaseModel):
    specialization: str
    year_of_entry: str
    scheme: str
    specific_specialization: str = None  # Optional field

@app.post("/submit_form")
async def submit_form(data: FormData):
    """
    Handle form submission and return a structured response.
    """
    try:
        result = {
            "specialization": data.specialization,
            "year_of_entry": data.year_of_entry,
            "scheme": data.scheme,
            "specific_specialization": data.specific_specialization,
        }
        logger.info(f"Form submitted successfully: {result}")
        return {"message": "Form submitted successfully", "data": result}
    except Exception as e:
        logger.error(f"Error submitting form: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    try:
        return {"status": "OK", "dependencies": "All systems operational"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "ERROR", "details": str(e)}

# Socket.IO handlers
@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")
    await sio.emit('response', {'message': 'Welcome!'}, to=sid)

@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")

@sio.event
async def send_message(sid, data):
    logger.info(f"Message received from {sid}: {data}")
    await sio.emit('response', {'message': f"Echo: {data}"}, to=sid)

# To run the server: `uvicorn server:socketio_app --reload --host 0.0.0.0 --port 8000`
