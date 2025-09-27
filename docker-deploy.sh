#!/bin/bash

# Docker build and deployment script for Agent Microservice
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="agent-microservice"
CONTAINER_NAME="agent-microservice"
PORT=8000

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating a template..."
        cat > .env << EOF
GEMINI_API_KEY=AIzaSyBfOsPzGWYG9mbAFTwXLfWJOE2KEpoBZNs
MAIN_PLATFORM_SECRET=your_super_secret_webhook_token_here
MAIN_PLATFORM_URL=http://localhost:3000/api/agent-response
MAX_OUTPUT_TOKENS=300
TEMPERATURE=0.7
EOF
        print_warning "Please update the .env file with your actual values before running!"
        return 1
    fi
    return 0
}

# Function to build Docker image
build_image() {
    print_status "Building Docker image: $IMAGE_NAME"
    docker build -t $IMAGE_NAME .
    print_status "Docker image built successfully!"
}

# Function to run container
run_container() {
    print_status "Running container: $CONTAINER_NAME"
    
    # Stop existing container if running
    if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
        print_warning "Stopping existing container..."
        docker stop $CONTAINER_NAME
        docker rm $CONTAINER_NAME
    fi
    
    # Run new container
    docker run -d \
        --name $CONTAINER_NAME \
        -p $PORT:8000 \
        --env-file .env \
        --restart unless-stopped \
        $IMAGE_NAME
    
    print_status "Container started successfully on port $PORT"
}

# Function to show logs
show_logs() {
    print_status "Showing container logs..."
    docker logs -f $CONTAINER_NAME
}

# Function to test the service
test_service() {
    print_status "Testing the service..."
    sleep 5
    
    # Health check
    if curl -s http://localhost:$PORT/ > /dev/null; then
        print_status "✅ Health check passed!"
        
        # Test tagging endpoint
        print_status "Testing tagging endpoint..."
        response=$(curl -s -X POST "http://localhost:$PORT/tag" \
            -H "Content-Type: application/json" \
            -d '{"text": "This is a test of artificial intelligence and machine learning", "max_tags": 3}')
        
        if echo "$response" | grep -q "tags"; then
            print_status "✅ Tagging endpoint working!"
            echo "Sample response: $response"
        else
            print_error "❌ Tagging endpoint failed"
            echo "Response: $response"
        fi
    else
        print_error "❌ Health check failed!"
        print_status "Container logs:"
        docker logs $CONTAINER_NAME
    fi
}

# Main script logic
case "$1" in
    "build")
        build_image
        ;;
    "run")
        if check_env_file; then
            run_container
        fi
        ;;
    "logs")
        show_logs
        ;;
    "test")
        test_service
        ;;
    "deploy")
        if check_env_file; then
            build_image
            run_container
            test_service
        fi
        ;;
    "stop")
        print_status "Stopping container..."
        docker stop $CONTAINER_NAME
        docker rm $CONTAINER_NAME
        print_status "Container stopped!"
        ;;
    "compose")
        if check_env_file; then
            print_status "Starting with docker-compose..."
            docker-compose up -d
            print_status "Services started!"
        fi
        ;;
    *)
        echo "Usage: $0 {build|run|deploy|logs|test|stop|compose}"
        echo ""
        echo "Commands:"
        echo "  build   - Build the Docker image"
        echo "  run     - Run the container"
        echo "  deploy  - Build, run, and test (full deployment)"
        echo "  logs    - Show container logs"
        echo "  test    - Test the running service"
        echo "  stop    - Stop and remove the container"
        echo "  compose - Use docker-compose to start services"
        exit 1
        ;;
esac