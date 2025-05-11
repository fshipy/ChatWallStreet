import os
import base64
import json
import httpx
from typing import List, Dict, Any
from dotenv import load_dotenv
from PIL import Image
import io

# Load environment variables
load_dotenv()

# Set LLM backend from environment variables
LLM_BACKEND = os.getenv("LLM_BACKEND", "gemini")  # Default to Gemini
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

def encode_image(image_path: str) -> str:
    """
    Encode an image to base64 for API requests.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded image
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def optimize_image(image_path: str, max_size: int = 4 * 1024 * 1024) -> str:
    """
    Optimize image size if needed to ensure it's under max_size.
    
    Args:
        image_path: Path to the image
        max_size: Maximum size in bytes
        
    Returns:
        Path to optimized image (could be the same if no optimization needed)
    """
    file_size = os.path.getsize(image_path)
    
    # If file is already smaller than max size, return original path
    if file_size <= max_size:
        return image_path
    
    # Open image and resize/compress if needed
    img = Image.open(image_path)
    
    # Calculate compression quality
    quality = 95
    temp_path = f"{image_path}.optimized.jpg"
    
    # Binary search to find optimal quality setting
    min_q, max_q = 5, 95
    while min_q <= max_q:
        quality = (min_q + max_q) // 2
        
        # Try compression at current quality
        img.save(temp_path, format="JPEG", quality=quality, optimize=True)
        
        # Check if size is acceptable
        new_size = os.path.getsize(temp_path)
        if new_size <= max_size:
            if min_q == max_q:
                break
            min_q = quality + 1
        else:
            max_q = quality - 1
    
    return temp_path

async def extract_positions_from_image(image_path: str) -> List[Dict[str, Any]]:
    """
    Use LLM to extract stock positions from an image.
    
    Args:
        image_path: Path to the screenshot image
        
    Returns:
        List of positions in the format [{"symbol": "AAPL", "shares": 10.5}, ...]
    """
    # Optimize image if needed
    optimized_image_path = optimize_image(image_path)
    
    if LLM_BACKEND == "gemini":
        return await extract_positions_gemini(optimized_image_path)
    elif LLM_BACKEND == "anthropic":
        return await extract_positions_anthropic(optimized_image_path)
    else:
        # Default to OpenAI
        return await extract_positions_openai(optimized_image_path)

async def extract_positions_openai(image_path: str) -> List[Dict[str, Any]]:
    """
    Extract positions using OpenAI's GPT-4 Vision.
    
    Args:
        image_path: Path to the screenshot image
        
    Returns:
        List of positions in the format [{"symbol": "AAPL", "shares": 10.5}, ...]
    """
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API key is required but not provided")
    
    # Encode image to base64
    base64_image = encode_image(image_path)
    
    # Create the payload
    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user", 
                "content": [
                    {
                        "type": "text", 
                        "text": "Extract JSON array of {symbol, shares} from this screenshot of stock positions. Return ONLY the JSON array, nothing else. Make sure all shares are correctly parsed as numbers."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 1000
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    # Make the API request
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response_data = response.json()
    
    # Extract and parse the result
    try:
        content = response_data["choices"][0]["message"]["content"]
        
        # Clean up the content to extract just the JSON
        content = content.strip()
        
        # If the response is wrapped in code blocks, remove them
        if content.startswith("```json"):
            content = content.replace("```json", "", 1)
        if content.startswith("```"):
            content = content.replace("```", "", 1)
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        
        # Parse the JSON
        positions = json.loads(content)
        
        # Ensure all shares are converted to float
        for position in positions:
            if "shares" in position:
                position["shares"] = float(position["shares"])
        
        return positions
    except Exception as e:
        print(f"Error parsing OpenAI response: {e}")
        print(f"Original response: {response_data}")
        return []

async def extract_positions_gemini(image_path: str) -> List[Dict[str, Any]]:
    """
    Extract positions using Google's Gemini Vision.
    
    Args:
        image_path: Path to the screenshot image
        
    Returns:
        List of positions in the format [{"symbol": "AAPL", "shares": 10.5}, ...]
    """
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API key is required but not provided")
    
    # Encode image to base64
    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()
    
    # Create the payload - using Gemini 2.0 Flash (gemini-flash-vision)
    payload = {
        "contents": [{
            "parts": [
                {"text": "Extract JSON array of {symbol, shares} from this screenshot of stock positions. Return ONLY the JSON array, nothing else. Make sure all shares are correctly parsed as numbers."},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(image_bytes).decode('utf-8')
                    }
                }
            ]
        }]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Make the API request - using Gemini Flash Vision model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload
        )
        response_data = response.json()
    
    # Extract and parse the result
    try:
        content = response_data["candidates"][0]["content"]["parts"][0]["text"]
        
        # Clean up the content to extract just the JSON
        content = content.strip()
        
        # If the response is wrapped in code blocks, remove them
        if content.startswith("```json"):
            content = content.replace("```json", "", 1)
        if content.startswith("```"):
            content = content.replace("```", "", 1)
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        
        # Parse the JSON
        positions = json.loads(content)
        
        # Ensure all shares are converted to float
        for position in positions:
            if "shares" in position:
                position["shares"] = float(position["shares"])
        
        return positions
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        print(f"Original response: {response_data}")
        return []

async def extract_positions_anthropic(image_path: str) -> List[Dict[str, Any]]:
    """
    Extract positions using Anthropic's Claude Vision.
    
    Args:
        image_path: Path to the screenshot image
        
    Returns:
        List of positions in the format [{"symbol": "AAPL", "shares": 10.5}, ...]
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("Anthropic API key is required but not provided")
    
    # Encode image to base64
    base64_image = encode_image(image_path)
    
    # Create the payload
    payload = {
        "model": "claude-3-opus-20240229",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract JSON array of {symbol, shares} from this screenshot of stock positions. Return ONLY the JSON array, nothing else. Make sure all shares are correctly parsed as numbers."
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64_image
                        }
                    }
                ]
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY
    }
    
    # Make the API request
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )
        response_data = response.json()
    
    # Extract and parse the result
    try:
        content = response_data["content"][0]["text"]
        
        # Clean up the content to extract just the JSON
        content = content.strip()
        
        # If the response is wrapped in code blocks, remove them
        if content.startswith("```json"):
            content = content.replace("```json", "", 1)
        if content.startswith("```"):
            content = content.replace("```", "", 1)
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        
        # Parse the JSON
        positions = json.loads(content)
        
        # Ensure all shares are converted to float
        for position in positions:
            if "shares" in position:
                position["shares"] = float(position["shares"])
        
        return positions
    except Exception as e:
        print(f"Error parsing Anthropic response: {e}")
        print(f"Original response: {response_data}")
        return []

async def chat_with_portfolio(query: str, holdings: List[Dict[str, Any]]) -> str:
    """
    Send a query about the portfolio to the chosen LLM.
    
    Args:
        query: User's question about the portfolio
        holdings: Current portfolio holdings
        
    Returns:
        LLM's response to the query
    """
    portfolio_json = json.dumps(holdings, indent=2)
    
    if LLM_BACKEND == "gemini":
        return await chat_with_portfolio_gemini(query, portfolio_json)
    elif LLM_BACKEND == "anthropic":
        return await chat_with_portfolio_anthropic(query, portfolio_json)
    else:
        # Default to OpenAI
        return await chat_with_portfolio_openai(query, portfolio_json)

async def chat_with_portfolio_openai(query: str, portfolio_json: str) -> str:
    """
    Send a query about the portfolio to OpenAI.
    
    Args:
        query: User's question about the portfolio
        portfolio_json: JSON string of portfolio data
        
    Returns:
        OpenAI's response to the query
    """
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API key is required but not provided")
    
    # Create the payload
    payload = {
        "model": "gpt-4",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful financial assistant. You are analyzing a user's stock portfolio."
            },
            {
                "role": "user",
                "content": f"Here is my portfolio data:\n{portfolio_json}\n\nMy question is: {query}"
            }
        ],
        "max_tokens": 1000
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    # Make the API request
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response_data = response.json()
    
    # Extract the response
    try:
        return response_data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error parsing OpenAI chat response: {e}")
        return f"Error analyzing portfolio: {str(e)}"

async def chat_with_portfolio_gemini(query: str, portfolio_json: str) -> str:
    """
    Send a query about the portfolio to Gemini.
    
    Args:
        query: User's question about the portfolio
        portfolio_json: JSON string of portfolio data
        
    Returns:
        Gemini's response to the query
    """
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API key is required but not provided")
    
    # Create the payload - using Gemini 2.0 Flash for text
    payload = {
        "contents": [{
            "parts": [
                {"text": f"You are a helpful financial assistant. Use the provided portfolio data (symbols, shares, tags, latest price) to answer the user's question with your knowledge of the stock market.\n\nHere is the portfolio data:\n{portfolio_json}\n\nThe user's question is: {query}"}
            ]
        }]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Make the API request - using Gemini 1.5 Flash model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload
        )
        response_data = response.json()
    
    # Extract the response
    try:
        return response_data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Error parsing Gemini chat response: {e}")
        return f"Error analyzing portfolio: {str(e)}"

async def chat_with_portfolio_anthropic(query: str, portfolio_json: str) -> str:
    """
    Send a query about the portfolio to Anthropic's Claude.
    
    Args:
        query: User's question about the portfolio
        portfolio_json: JSON string of portfolio data
        
    Returns:
        Claude's response to the query
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("Anthropic API key is required but not provided")
    
    # Create the payload
    payload = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful financial assistant. You are analyzing a user's stock portfolio."
            },
            {
                "role": "user",
                "content": f"Here is my portfolio data:\n{portfolio_json}\n\nMy question is: {query}"
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY
    }
    
    # Make the API request
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )
        response_data = response.json()
    
    # Extract the response
    try:
        return response_data["content"][0]["text"]
    except Exception as e:
        print(f"Error parsing Anthropic chat response: {e}")
        return f"Error analyzing portfolio: {str(e)}" 