import socketio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Socket.IO server with AsyncIO and FastAPI app
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=["http://localhost:5173"])
app = FastAPI()
socketio_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Configure CORS Middleware for FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the Pydantic model for form data
class FormData(BaseModel):
    specialization: str
    year: str
    scheme: str
    specific_ece_specs: str = None

@app.post("/submit_form")
async def submit_form(data: FormData):
    """
    Handle form submission and return a structured response.
    """
    try:
        result = {
            "specialization": data.specialization,
            "year": data.year,
            "scheme": data.scheme,
            "specific_ece_specs": data.specific_ece_specs,
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

# Define the prompt template
template = """ 
Answer the question below.

Here is the conversation history: {context}
Question: {question}
Answer:
"""

# Initialize the Ollama LLM
try:
    model_name = "llama3.2"
    logger.info(f"Initializing Ollama model: {model_name}")
    model = OllamaLLM(model=model_name)
except Exception as e:
    logger.error(f"Failed to initialize model '{model_name}': {e}")
    raise e

# Create the prompt template
try:
    prompt = ChatPromptTemplate.from_template(template)
    logger.info("Prompt template created successfully.")
except Exception as e:
    logger.error(f"Failed to create prompt template: {e}")
    raise e

# Combine prompt and model into a chain
try:
    chain = prompt | model
    logger.info("Chain created successfully.")
except Exception as e:
    logger.error(f"Failed to create chain: {e}")
    raise e

user_states = {}

@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")
    user_states[sid] = {}
    await sio.emit('response', {'message': 'Connected successfully.'}, to=sid)

@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")
    user_states.pop(sid, None)

@sio.event
async def send_message(sid, data):
    user_message = data.get('message', '').strip()
    logger.info(f"Received message from {sid}: {user_message}")

    if sid not in user_states:
        user_states[sid] = {}

    context = data.get('context', '')

    try:
        input_data = {"context": context, "question": user_message}
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, chain.invoke, input_data)

        new_context = f"{context}\nUser: {user_message}\nAI: {result}"
        await sio.emit('response', {'message': result, 'context': new_context}, to=sid)
    except Exception as e:
        logger.error(f"Error processing message from {sid}: {e}")
        await sio.emit('response', {'message': 'Sorry, something went wrong.'}, to=sid)
