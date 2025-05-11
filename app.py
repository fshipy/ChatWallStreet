import os
import shutil
import base64
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request, Body
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# Import our modules
import storage
import parser
import price_fetcher

# Create FastAPI app
app = FastAPI(
    title="Personal Portfolio Tracker",
    description="A zero-setup Python/CSV web app to track your stock positions from screenshots.",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories if they don't exist
os.makedirs("images", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Models for request validation
class EditPosition(BaseModel):
    symbol: str
    tag: str
    shares: float

class ChatRequest(BaseModel):
    query: str

class PastedImage(BaseModel):
    image_data: str  # Base64 encoded image data
    tag: str

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main HTML interface."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api", response_class=JSONResponse)
async def api_root():
    """API information endpoint."""
    return {"message": "Welcome to Personal Portfolio Tracker API. Go to /docs for API documentation."}

async def process_image(filename: str, tag: str):
    """Helper function to process an image and extract positions."""
    try:
        # Extract positions from image using LLM
        positions = await parser.extract_positions_from_image(filename)
        
        # If no positions were found, return error
        if not positions:
            raise HTTPException(status_code=400, detail="Could not extract any positions from the image")
        
        # Update holdings in CSV
        storage.update_holdings(positions, tag)
        
        return {
            "message": f"Successfully extracted {len(positions)} positions for tag '{tag}'",
            "positions": positions
        }
    except Exception as e:
        # Clean up the file in case of error
        if os.path.exists(filename):
            os.remove(filename)
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@app.post("/upload")
async def upload_image(
    image: UploadFile = File(...),
    tag: str = Form(...)
):
    """
    Upload a screenshot of stock positions and extract them using LLM.
    
    Args:
        image: Screenshot file
        tag: Label for these positions (e.g., broker, account, etc.)
        
    Returns:
        Extracted positions
    """
    # Create unique filename 
    timestamp = storage.datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"images/{timestamp}_{tag}_{image.filename}"
    
    # Save uploaded file
    with open(filename, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    
    return await process_image(filename, tag)

@app.post("/paste")
async def paste_image(data: PastedImage):
    """
    Handle pasted image data and extract positions using LLM.
    
    Args:
        data: Object containing base64 image data and tag
        
    Returns:
        Extracted positions
    """
    try:
        # Decode base64 image data
        image_data = base64.b64decode(data.image_data.split(',')[1] if ',' in data.image_data else data.image_data)
        
        # Create unique filename
        timestamp = storage.datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"images/{timestamp}_{data.tag}_pasted.png"
        
        # Save the image
        with open(filename, "wb") as f:
            f.write(image_data)
        
        return await process_image(filename, data.tag)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")

@app.post("/update")
async def update_positions(
    image: UploadFile = File(...),
    tag: str = Form(...)
):
    """
    Update existing positions with new screenshot.
    This is an alias for /upload.
    """
    return await upload_image(image, tag)

@app.get("/positions")
async def get_positions(
    exclude: Optional[List[str]] = Query(None),
    include: Optional[List[str]] = Query(None),
    group_by_symbol: bool = Query(False, alias="group_by"),
    hide_options: bool = Query(False)
):
    """
    Get current portfolio positions with live price data.
    
    Args:
        exclude: Tags to exclude from results
        include: Tags to include in results (if None, include all)
        group_by_symbol: Whether to aggregate positions by symbol
        hide_options: Whether to hide options (symbols ending with numbers)
        
    Returns:
        List of positions with price and value
    """
    # Read holdings from CSV
    holdings = storage.read_holdings()
    
    # Apply filters
    filtered_holdings = storage.filter_holdings(holdings, include, exclude, hide_options=hide_options)
    
    # Group by symbol if requested
    if group_by_symbol:
        filtered_holdings = storage.group_by_symbol(filtered_holdings)
    
    # Fetch current prices and calculate values
    enriched_holdings = await price_fetcher.get_portfolio_values(filtered_holdings)
    
    # Calculate total portfolio value
    total_value = sum(holding.get("value", 0) for holding in enriched_holdings)
    
    return {
        "positions": enriched_holdings,
        "total_value": round(total_value, 2),
        "position_count": len(enriched_holdings)
    }

@app.patch("/edit")
async def edit_position(position: EditPosition):
    """
    Manually edit a position.
    
    Args:
        position: Position data with symbol, tag, and shares
        
    Returns:
        Success message
    """
    # Update the position in the CSV
    storage.edit_holding(position.symbol, position.tag, position.shares)
    
    return {"message": f"Position updated: {position.symbol} ({position.tag}) - {position.shares} shares"}

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat with an LLM about your portfolio.
    
    Args:
        request: Chat request with query
        
    Returns:
        LLM's response
    """
    # Read holdings
    holdings = storage.read_holdings()
    
    # Get current prices and values
    enriched_holdings = await price_fetcher.get_portfolio_values(holdings)
    
    # Send to LLM for analysis
    response = await parser.chat_with_portfolio(request.query, enriched_holdings)
    
    return {"response": response}

# For running the app directly
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True) 