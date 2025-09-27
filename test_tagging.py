#!/usr/bin/env python3
"""
Test script for the tagging endpoint.
Run this script to test the /tag endpoint functionality.
"""

import httpx
import asyncio
import json


async def test_tagging_endpoint():
    """Test the tagging endpoint with various text samples."""

    base_url = "http://localhost:8000"

    # Test cases
    test_cases = [
        {
            "text": "This is an article about machine learning and artificial intelligence. It covers neural networks, deep learning algorithms, and their applications in computer vision and natural language processing.",
            "max_tags": 4
        },
        {
            "text": "I love cooking Italian food, especially making fresh pasta and pizza from scratch. My favorite dishes include carbonara, margherita pizza, and tiramisu for dessert.",
            "max_tags": 5
        },
        {
            "text": "The stock market experienced significant volatility today as investors reacted to the Federal Reserve's interest rate decision. Technology stocks were particularly affected, with major indices closing down 2.5%.",
            "max_tags": 3
        },
        {
            "text": "Climate change is causing rising sea levels, more frequent extreme weather events, and shifts in ecosystems worldwide. Scientists urge immediate action to reduce greenhouse gas emissions.",
            "max_tags": 4
        },
        # Test case for word count validation (should fail)
        {
            "text": "Too few words",  # Only 3 words - should fail
            "max_tags": 3
        },
        # Test case for exactly 5 words (should pass)
        {
            "text": "This text has exactly five words",  # Exactly 5 words
            "max_tags": 3
        }
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test health check first
        try:
            response = await client.get(f"{base_url}/")
            print("✅ Health check:", response.json())
        except Exception as e:
            print("❌ Server not running:", e)
            return

        # Test tagging endpoint with each case
        for i, test_case in enumerate(test_cases, 1):
            try:
                print(f"\n--- Test Case {i} ---")
                print(f"Text: {test_case['text'][:100]}...")
                print(f"Max tags: {test_case['max_tags']}")

                response = await client.post(f"{base_url}/tag", json=test_case)

                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Status: {response.status_code}")
                    print(f"📝 Tags: {result['tags']}")
                    print(f"🎯 Confidence: {result['confidence']}")
                else:
                    print(f"❌ Status: {response.status_code}")
                    print(f"Error: {response.text}")

            except Exception as e:
                print(f"❌ Error testing case {i}: {e}")

if __name__ == "__main__":
    print("🚀 Testing Tagging Endpoint")
    print("=" * 50)
    asyncio.run(test_tagging_endpoint())
