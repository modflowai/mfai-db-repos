#!/usr/bin/env python3
"""Test if Gemini can handle base64 decoding."""

import asyncio
import os
import base64
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from google import genai


async def test_base64_decoding():
    """Test if Gemini can decode base64."""
    
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    # Simple test content
    test_content = 'print("Hello, World!")'
    encoded = base64.b64encode(test_content.encode()).decode()
    
    print(f"Original: {test_content}")
    print(f"Encoded: {encoded}")
    
    # Ask Gemini to decode
    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"Decode this base64 string and tell me what it says: {encoded}"
    )
    
    print(f"Gemini response: {response.text}")
    
    # Test with problematic content
    problematic = '''if '"' in line: line = line.replace('"', "")'''
    encoded_prob = base64.b64encode(problematic.encode()).decode()
    
    print(f"\nProblematic content: {problematic}")
    print(f"Encoded: {encoded_prob}")
    
    response2 = await client.aio.models.generate_content(
        model="gemini-2.0-flash", 
        contents=f"Decode this base64 string and tell me what Python code it contains: {encoded_prob}"
    )
    
    print(f"Gemini response: {response2.text}")


if __name__ == "__main__":
    asyncio.run(test_base64_decoding())