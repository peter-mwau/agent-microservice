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

# Let's try to list available models first to debug
try:
    available_models = genai.list_models()
    logger.info("Available models:")
    for model_info in available_models:
        if 'generateContent' in model_info.supported_generation_methods:
            logger.info(f"  - {model_info.name}")
except Exception as e:
    logger.error(f"Error listing models: {e}")

# Try different model names based on what's actually available
model_names_to_try = [
    'models/gemini-2.5-flash',
    'models/gemini-2.0-flash',
    'models/gemini-flash-latest',
    'models/gemini-pro-latest',
    'models/gemini-2.5-pro',
    'gemini-pro'
]

model = None
for model_name in model_names_to_try:
    try:
        model = genai.GenerativeModel(model_name)
        logger.info(f"Successfully initialized model: {model_name}")
        break
    except Exception as e:
        logger.warning(f"Failed to initialize model {model_name}: {e}")
        continue

if model is None:
    logger.error("Could not initialize any Gemini model!")
    raise ValueError("No available Gemini model could be initialized")

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


class TaggingRequest(BaseModel):
    """Request model for text tagging endpoint."""
    text: str
    max_tags: int = 5  # Optional: maximum number of tags to return (default 5)


class TaggingResponse(BaseModel):
    """Response model for text tagging endpoint."""
    text: str
    tags: list[str]
    confidence: str = "high"  # Could be "high", "medium", "low"

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
    if model is None:
        logger.error("Model not initialized!")
        return "I apologize, but the AI model is not available. Please check the configuration."

    try:
        # Try async first
        logger.info("Attempting async generation...")
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=MAX_OUTPUT_TOKENS,
                temperature=TEMPERATURE,
            )
        )
        return response.text
    except Exception as async_error:
        logger.warning(f"Async generation failed: {async_error}")

        # Fallback to synchronous generation wrapped in async
        try:
            logger.info("Trying synchronous generation as fallback...")
            import asyncio

            def sync_generate():
                return model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=MAX_OUTPUT_TOKENS,
                        temperature=TEMPERATURE,
                    )
                )

            response = await asyncio.get_event_loop().run_in_executor(None, sync_generate)
            return response.text
        except Exception as sync_error:
            logger.error(
                f"Both async and sync Gemini API calls failed. Async: {async_error}, Sync: {sync_error}")
            return "I apologize, but I encountered a technical issue with the AI service. Please try again in a moment."


async def generate_tags(text: str, max_tags: int = 5) -> list[str]:
    """Analyzes text and generates relevant tags using Gemini with intelligent acronym and compound term handling."""

    # Enhanced prompt that encourages acronyms and compound terms
    tag_prompt = f"""
    You are an expert content analyzer. Analyze the following text and generate exactly {max_tags} unique, relevant tags.
    
    IMPORTANT INSTRUCTIONS:
    - Generate smart, meaningful tags that capture key concepts
    - Use common acronyms when applicable (e.g., "AI" for artificial intelligence, "ML" for machine learning, "IT" for information technology)
    - Create compound terms for related concepts (e.g., "data-science", "web-development", "stock-market")
    - Each tag should be 1-4 words maximum, lowercase (except for acronyms like AI, ML, IT, etc.)
    - Focus on: main topics, themes, concepts, categories, industries, domains, technologies
    - Avoid generic words like "text", "content", "information", "article", "about"
    - Make tags specific and actionable
    - Return ONLY the tags, one per line, no numbering or explanations
    - Prioritize acronyms and compound terms over single generic words
    
    Examples of good tags:
    - "AI" instead of "artificial intelligence" 
    - "ML" instead of "machine learning"
    - "data-science" instead of separate "data" and "science"
    - "web-development" instead of "web" and "development"
    - "climate-change" instead of "climate" and "change"
    
    Text to analyze:
    "{text}"
    
    Generate {max_tags} smart tags:
    """

    try:
        logger.info(
            f"Sending enhanced prompt to Gemini for smart tag generation...")
        response = await model.generate_content_async(
            tag_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=200,  # More tokens for better responses
                temperature=0.7,  # Balanced temperature for consistency with creativity
            )
        )

        if not response or not response.text:
            logger.warning("Empty response from Gemini API")
            raise Exception("Empty response from Gemini")

        # Parse the response to extract tags
        tags_text = response.text.strip()
        logger.info(f"Raw Gemini response for tags: {tags_text}")

        # Clean and parse tags
        lines = tags_text.split('\n')
        tags = []

        for line in lines:
            # Remove numbering, bullets, and extra whitespace
            clean_line = line.strip()
            # Remove common prefixes (numbers, bullets, dashes, etc.)
            import re
            clean_line = re.sub(r'^[\d\.\)\-\*•\s]+', '', clean_line)
            clean_line = clean_line.strip()

            # Keep acronyms in uppercase, but make other terms lowercase
            if clean_line:
                # Check if it's likely an acronym (2-4 uppercase letters)
                if re.match(r'^[A-Z]{2,4}$', clean_line):
                    processed_line = clean_line  # Keep acronyms as-is
                else:
                    processed_line = clean_line.lower()

                if len(processed_line) > 1 and processed_line not in tags:
                    tags.append(processed_line)

        logger.info(f"Parsed tags from Gemini: {tags}")

        # If Gemini failed, use smart keyword extraction with acronym detection
        if len(tags) < 2:
            logger.info(
                "Not enough tags from Gemini, using smart keyword extraction")
            tags = smart_keyword_extraction(text, max_tags)

        # Ensure we have at least 2 tags
        if len(tags) < 2:
            logger.info(
                "Still not enough tags, adding intelligent fallback tags")
            # Create contextual fallback tags based on text content
            fallback_tags = create_contextual_fallback_tags(text)
            for fallback_tag in fallback_tags:
                if fallback_tag not in tags:
                    tags.append(fallback_tag)
                if len(tags) >= max_tags:
                    break

        # Return up to max_tags
        final_tags = tags[:max_tags]
        logger.info(f"Final generated smart tags: {final_tags}")
        return final_tags

    except Exception as e:
        logger.error(f"Error generating tags: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

        # Emergency fallback with smart keyword extraction
        try:
            logger.info("Attempting smart emergency keyword extraction")
            emergency_tags = smart_keyword_extraction(text, max_tags)
            if len(emergency_tags) >= 2:
                logger.info(
                    f"Emergency smart tags generated: {emergency_tags}")
                return emergency_tags
        except Exception as emergency_e:
            logger.error(
                f"Smart emergency fallback also failed: {emergency_e}")

        # Final fallback - varied contextual tags
        return create_contextual_fallback_tags(text)[:max_tags]


def smart_keyword_extraction(text: str, max_tags: int) -> list[str]:
    """Extract keywords intelligently, creating acronyms and compound terms where appropriate."""
    import re

    # Define common acronym patterns
    acronym_patterns = {
        r'\b(artificial intelligence|AI)\b': 'AI',
        r'\b(machine learning|ML)\b': 'ML',
        r'\b(deep learning|DL)\b': 'DL',
        r'\b(neural network|NN)\b': 'neural-networks',
        r'\b(computer vision|CV)\b': 'computer-vision',
        r'\b(natural language processing|NLP)\b': 'NLP',
        r'\b(data science|data-science)\b': 'data-science',
        r'\b(information technology|IT)\b': 'IT',
        r'\b(user interface|UI)\b': 'UI',
        r'\b(user experience|UX)\b': 'UX',
        r'\b(application programming interface|API)\b': 'API',
        r'\b(stock market)\b': 'stock-market',
        r'\b(climate change)\b': 'climate-change',
        r'\b(web development|web-development)\b': 'web-development',
        r'\b(software engineering|software-engineering)\b': 'software-engineering',
        r'\b(project management|project-management)\b': 'project-management',
    }

    text_lower = text.lower()
    extracted_tags = []

    # First, look for known acronym patterns
    for pattern, tag in acronym_patterns.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            if tag not in extracted_tags:
                extracted_tags.append(tag)

    # Then extract meaningful compound terms and single words
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text)  # Words with 4+ characters
    potential_tags = []

    for word in words:
        clean_word = word.lower()
        if clean_word not in ['this', 'that', 'with', 'from', 'they', 'have', 'were', 'been', 'their', 'said', 'each', 'which', 'such', 'will', 'more', 'very', 'what', 'when', 'where', 'much', 'some', 'time', 'about', 'after', 'first', 'well', 'also']:
            potential_tags.append(clean_word)

    # Add unique meaningful words
    for tag in potential_tags:
        if tag not in extracted_tags and len(extracted_tags) < max_tags:
            extracted_tags.append(tag)

    return extracted_tags


def create_contextual_fallback_tags(text: str) -> list[str]:
    """Create intelligent fallback tags based on text content."""
    text_lower = text.lower()

    # Domain-specific fallback tags based on content
    if any(word in text_lower for word in ['machine', 'learning', 'artificial', 'intelligence', 'neural', 'algorithm']):
        return ['AI', 'ML', 'technology', 'algorithms', 'data-science']
    elif any(word in text_lower for word in ['cooking', 'recipe', 'food', 'kitchen', 'dish']):
        return ['cooking', 'food', 'recipes', 'culinary', 'kitchen']
    elif any(word in text_lower for word in ['stock', 'market', 'investment', 'trading', 'financial']):
        return ['finance', 'stock-market', 'investment', 'trading', 'economics']
    elif any(word in text_lower for word in ['climate', 'environment', 'weather', 'temperature', 'carbon']):
        return ['climate-change', 'environment', 'weather', 'sustainability', 'ecology']
    elif any(word in text_lower for word in ['technology', 'software', 'computer', 'digital']):
        return ['technology', 'software', 'digital', 'computing', 'tech']
    else:
        return ['general-topic', 'content-analysis', 'text-review', 'information', 'analysis']
        return error_tags[:max_tags]


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


@app.post("/tag", response_model=TaggingResponse)
async def tag_text(request: TaggingRequest):
    """
    Analyzes the provided text and returns relevant tags.

    This endpoint uses Gemini AI to analyze text content and generate
    meaningful tags that describe the themes, topics, or categories
    present in the text.
    """
    logger.info(
        f"Received tagging request for text: '{request.text[:100]}...'")

    # Validate input - check for minimum word count
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty"
        )

    word_count = len(request.text.strip().split())
    if word_count < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Text must contain at least 5 words. Current text has {word_count} words."
        )

    if request.max_tags < 2 or request.max_tags > 10:
        raise HTTPException(
            status_code=400,
            detail="max_tags must be between 2 and 10"
        )

    try:
        # Generate tags using Gemini
        tags = await generate_tags(request.text, request.max_tags)

        # Ensure we have at least 2 tags as specified in requirements
        if len(tags) < 2:
            tags = ["general", "content"] + tags
            # Remove duplicates while preserving order
            tags = list(dict.fromkeys(tags))

        logger.info(f"Generated tags: {tags}")

        return TaggingResponse(
            text=request.text,
            tags=tags[:request.max_tags],  # Ensure we don't exceed max_tags
            confidence="high" if len(tags) >= 2 else "medium"
        )

    except Exception as e:
        logger.error(f"Error in tag_text endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while generating tags"
        )


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
