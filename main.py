# main.py
import os
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks, Request
from pydantic import BaseModel, HttpUrl
import httpx
import google.generativeai as genai
from dotenv import load_dotenv
import logging
import os

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration from Environment ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MAIN_PLATFORM_SECRET = os.getenv("MAIN_PLATFORM_SECRET")
MAIN_PLATFORM_URL = os.getenv("MAIN_PLATFORM_URL")

# Load your new configuration
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", 300))  # Default to 300
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))  # Default to 0.7

print(f"GEMINI_API_KEY: {GEMINI_API_KEY}")
print(f"MAIN_PLATFORM_SECRET: {MAIN_PLATFORM_SECRET}")
print(f"MAIN_PLATFORM_URL: {MAIN_PLATFORM_URL}")

# Validate that we have the crucial configs
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set!")
if not MAIN_PLATFORM_SECRET:
    raise ValueError("MAIN_PLATFORM_SECRET environment variable is not set!")

# --- Configure Gemini ---
genai.configure(api_key=GEMINI_API_KEY)
# Initialize the model (using Gemini 1.5 Flash for speed and cost, but you can use Gemini 1.5 Pro)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- Initialize FastAPI App ---
app = FastAPI(
    title="AI Agent Microservice",
    description="A microservice to handle @agent mentions using Gemini.",
    version="0.1.0"
)

# --- Pydantic Models for Request/Response ---


class AgentWebhookRequest(BaseModel):
    """The payload your main platform will send to the /webhook endpoint."""
    thread_id: str
    message_id: str
    query: str
    user_id: str
    user_name: str = "A User"  # Optional but useful for personalization
    context: list[str] = []    # Optional: previous messages for context


class AgentResponsePayload(BaseModel):
    """The payload this service will send back to the main platform."""
    thread_id: str
    message_id: str
    text: str
    agent_id: str = "ai_agent_001"  # Identifier for your agent

# --- Helper Functions ---


def build_prompt(user_query: str, user_name: str, message_history: list[str]) -> str:
    """
    Constructs the prompt for Gemini based on the request and context.
    This is where you define your agent's personality and task.
    """
    system_instruction = """
    You are 'ForumBot', a helpful AI assistant in a discussion forum.
    Your tone is professional, friendly, and concise. Your goal is to assist users based on their direct queries.
    If the user's request is unclear, ask for clarification. If you cannot help, politely state why.
    """

    # Build the context from recent messages if they exist
    context_block = ""
    if message_history:
        context_block = "Here is the recent conversation context for your awareness:\n"
        # Last 3 msgs
        context_block += "\n".join(
            [f"- {msg}" for msg in message_history[-3:]])
        context_block += "\n\n"

    user_prompt = f"""
    {context_block}
    The user '{user_name}' has directly asked you this:
    \"{user_query}\"

    Please provide your helpful response:
    """

    full_prompt = f"{system_instruction}\n\n{user_prompt}"
    logger.info(f"Prompt being sent to Gemini: {full_prompt}")
    return full_prompt


async def call_gemini(prompt: str) -> str:
    """Sends the prompt to the Gemini API and returns the response text."""
    try:
        # Generate content using the model
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=MAX_OUTPUT_TOKENS,
                temperature=TEMPERATURE,
            )
        )
        return response.text
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return "I apologize, but I encountered a technical issue. Please try again in a moment."


async def post_to_main_platform(payload: AgentResponsePayload):
    """Sends the agent's response back to the main discussion platform."""
    async with httpx.AsyncClient() as client:
        try:
            headers = {"Authorization": f"Bearer {MAIN_PLATFORM_SECRET}"}
            response = await client.post(MAIN_PLATFORM_URL, json=payload.dict(), headers=headers, timeout=30.0)
            response.raise_for_status()  # Raises an exception for 4xx/5xx responses
            logger.info(
                f"Successfully posted response back to main platform for thread {payload.thread_id}")
        except httpx.HTTPError as e:
            logger.error(f"Failed to post back to main platform: {e}")

# --- API Endpoints ---


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "AI Agent Microservice is running!", "status": "OK"}


@app.post("/webhook")
async def handle_webhook(
    request: AgentWebhookRequest,
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """
    The primary webhook endpoint. Your main platform calls this when a user tags @agent.
    It validates the request, then queues the AI processing in a background task.
    """
    logger.info(
        f"Received webhook for thread {request.thread_id}, query: '{request.query}'")

    # 1. Authenticate the request
    if authorization != f"Bearer {MAIN_PLATFORM_SECRET}":
        logger.warning(
            f"Unauthorized webhook attempt with token: {authorization}")
        raise HTTPException(
            status_code=401, detail="Invalid authentication token")

    # 2. Acknowledge receipt immediately and process in the background
    background_tasks.add_task(process_agent_request, request)

    return {
        "status": "processing",
        "message": "Your request has been received and is being processed by the agent.",
        "thread_id": request.thread_id
    }


async def process_agent_request(request: AgentWebhookRequest):
    """Background task to handle the LLM call and callback."""
    logger.info(
        f"Background processing started for message {request.message_id}")

    # 1. Build the prompt for Gemini
    prompt = build_prompt(request.query, request.user_name, request.context)

    # 2. Call the Gemini API
    agent_response_text = await call_gemini(prompt)

    # 3. Prepare the payload to send back to the main platform
    response_payload = AgentResponsePayload(
        thread_id=request.thread_id,
        message_id=request.message_id,
        text=agent_response_text
    )

    # 4. Send the response back
    await post_to_main_platform(response_payload)

    logger.info(
        f"Background processing completed for message {request.message_id}")
