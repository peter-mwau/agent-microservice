#!/bin/bash

# Test script for the tagging endpoint using curl
echo "🚀 Testing Tagging Endpoint with curl"
echo "====================================="

# Check if server is running
echo "📡 Testing server health..."
curl -s http://localhost:8000/ | jq . 2>/dev/null || echo "❌ Server not responding or jq not installed"

echo ""
echo "📝 Testing tagging endpoint..."

# Test case 1: AI/ML content
echo "--- Test 1: AI/ML Content ---"
curl -X POST "http://localhost:8000/tag" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This article discusses machine learning algorithms, neural networks, and deep learning applications in computer vision and natural language processing.",
    "max_tags": 4
  }' | jq . 2>/dev/null || echo "Response received (install jq for better formatting)"

echo ""
echo "--- Test 2: Cooking Content ---"
curl -X POST "http://localhost:8000/tag" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I love cooking Italian food, especially making fresh pasta and pizza from scratch. My favorite dishes include carbonara and tiramisu.",
    "max_tags": 3
  }' | jq . 2>/dev/null || echo "Response received (install jq for better formatting)"

echo ""
echo "--- Test 3: Finance Content ---"
curl -X POST "http://localhost:8000/tag" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The stock market experienced volatility as investors reacted to interest rate changes. Technology stocks were particularly affected.",
    "max_tags": 5
  }' | jq . 2>/dev/null || echo "Response received (install jq for better formatting)"

echo ""
echo "--- Test 4: Error Case (text too short) ---"
curl -X POST "http://localhost:8000/tag" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hi",
    "max_tags": 2
  }' | jq . 2>/dev/null || echo "Response received (install jq for better formatting)"

echo ""
echo "✅ Tests completed!"