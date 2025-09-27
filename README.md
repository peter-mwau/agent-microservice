# Agent Microservice

This project is a FastAPI-based microservice designed to provide scalable, high-performance API endpoints for various agent-related operations. It is structured for easy deployment, maintainability, and extensibility, making it suitable for modern microservice architectures.

## Features

- Built with [FastAPI](https://fastapi.tiangolo.com/) for fast, async web APIs
- **AI-Powered Text Tagging**: Intelligent content analysis using Google's Gemini AI
- **Smart Tag Generation**: Creates acronyms (AI, ML) and compound terms automatically
- **Webhook Support**: Handle @agent mentions from discussion platforms
- Simple project structure for easy understanding and extension
- Ready for containerization and cloud deployment

## Getting Started

### Prerequisites

- Python 3.12+
- Git
- Docker (for containerization)
- **Gemini API Key** (for AI tagging functionality)

### Environment Setup

1. Create a `.env` file in the project root:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
MAIN_PLATFORM_SECRET=your_super_secret_webhook_token_here
MAIN_PLATFORM_URL=http://localhost:3000/api/agent-response
MAX_OUTPUT_TOKENS=300
TEMPERATURE=0.7
```

### Clone the Repository

```bash
git clone https://github.com/peter-mwau/agent-microservice.git
cd agent-microservice
```

### Set Up Virtual Environment

```bash
python3 -m venv virtualenv
source virtualenv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the Application

```bash
bash start.sh
```

Or directly with uvicorn:

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000` by default.

## API Endpoints

### Health Check

- **GET** `/` - Returns service status

### Text Tagging (AI-Powered)

- **POST** `/tag` - Analyzes text and generates intelligent tags

#### Request Format:

```json
{
  "text": "Your text content to analyze",
  "max_tags": 5
}
```

#### Response Format:

```json
{
  "text": "Your original text...",
  "tags": ["AI", "machine-learning", "technology", "innovation"],
  "confidence": "high"
}
```

#### Features:

- **Smart Acronym Generation**: Converts "artificial intelligence" → "AI"
- **Compound Terms**: Creates meaningful combinations like "machine-learning"
- **Context-Aware**: Different content types get relevant tag categories
- **Minimum 5 Words**: Validates input has sufficient content for analysis
- **Fallback System**: Ensures reliable tagging even when AI is unavailable

#### Example Usage:

```bash
curl -X POST "http://localhost:8000/tag" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This article discusses machine learning algorithms and neural networks for computer vision applications.",
    "max_tags": 4
  }'
```

**Response:**

```json
{
  "text": "This article discusses machine learning algorithms and neural networks for computer vision applications.",
  "tags": ["ML", "algorithms", "neural-networks", "computer-vision"],
  "confidence": "high"
}
```

### Webhook Endpoint

- **POST** `/webhook` - Handles @agent mentions from discussion platforms

## Docker Usage

### Build the Docker Image

```bash
docker build -t your-dockerhub-username/agent-microservice:latest .
```

### Run the Docker Container

```bash
docker run -d -p 8000:8000 your-dockerhub-username/agent-microservice:latest
```

The API will be available at `http://localhost:8000`.

### Push to Docker Hub

1. Log in to Docker Hub:
   ```bash
   docker login
   ```
2. Tag your image (if not already tagged):

   ```bash
   docker tag agent-microservice your-dockerhub-username/agent-microservice:latest
   ```

3. Push the image:
   ```bash
   docker push your-dockerhub-username/agent-microservice:latest
   ```

#### Troubleshooting: Permission Denied Errors on Linux

If you see errors like `permission denied while trying to connect to the Docker daemon socket`, your user likely does not have permission to access Docker. To fix this:

```bash
sudo usermod -aG docker $USER
```

Then **log out and log back in** (or reboot) for the group change to take effect. After that, try your Docker commands again.

## Project Structure

```
agent-microservice/
├── main.py            # FastAPI application entry point
├── requirements.txt   # Python dependencies
├── start.sh           # Shell script to start the server
├── test_tagging.py    # Python test script for tagging endpoint
├── test_tagging.sh    # Shell script to test tagging with curl
├── .env              # Environment variables (create this)
├── virtualenv/        # Virtual environment (not included in repo)
└── README.md         # This file
```

## Testing

### Test the Tagging Endpoint

**Option 1: Python Test Script**

```bash
python3 test_tagging.py
```

**Option 2: Shell Script with curl**

```bash
./test_tagging.sh
```

**Option 3: Manual curl Test**

```bash
curl -X POST "http://localhost:8000/tag" \
  -H "Content-Type: application/json" \
  -d '{"text": "Discussing artificial intelligence and machine learning", "max_tags": 3}'
```

## How to Contribute

1. Fork this repository
2. Create a new branch: `git checkout -b feature/your-feature-name`
3. Make your changes and commit: `git commit -am 'Add new feature'`
4. Push to your fork: `git push origin feature/your-feature-name`
5. Open a Pull Request describing your changes

Please ensure your code follows PEP8 standards and includes relevant tests/documentation.

## Implementation Details

### Core Components

- **main.py**: Contains the FastAPI app and route definitions
  - `/` - Health check endpoint
  - `/tag` - AI-powered text tagging endpoint
  - `/webhook` - Agent mention handling from platforms
- **requirements.txt**: Lists all required Python packages including Google Generative AI
- **start.sh**: Script to activate virtual environment and start the server
- **test_tagging.py**: Comprehensive async testing of the tagging endpoint
- **test_tagging.sh**: Quick curl-based testing script

### AI Tagging System

The tagging system uses Google's Gemini AI with intelligent preprocessing:

1. **Input Validation**: Ensures minimum 5 words for meaningful analysis
2. **Smart Processing**:
   - Converts related terms to acronyms (AI, ML, NLP)
   - Creates compound terms for better context
   - Handles technical domains intelligently
3. **Fallback Systems**: Multiple layers ensure reliability even when AI fails
4. **Logging**: Comprehensive logging for debugging and monitoring

### Example Endpoints

**Health Check:**

```python
@app.get("/")
async def root():
    return {"message": "AI Agent Microservice is running!", "status": "OK"}
```

**Text Tagging:**

```python
@app.post("/tag", response_model=TaggingResponse)
async def tag_text(request: TaggingRequest):
    # Validates input, calls Gemini AI, processes response
    # Returns intelligent tags with confidence scores
```

## License

This project is licensed under the MIT License.
