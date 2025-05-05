#!/bin/bash

# Exit on error
set -e

echo "Setting up Personal Portfolio Tracker..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .portfolio-tracker

# Activate virtual environment
echo "Activating virtual environment..."
source .portfolio-tracker/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Check if .env file exists, if not create from example
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit the .env file to add your API keys before starting the app."
    echo "At minimum, you'll need to add your GEMINI_API_KEY."
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p data images static templates

echo "Setup complete!"
echo "To start the app, run: source .portfolio-tracker/bin/activate && python app.py"
echo "Then open your browser to: http://localhost:8000"

# Ask if user wants to start the app now
read -p "Do you want to start the app now? (y/n): " answer
if [[ $answer == "y" || $answer == "Y" ]]; then
    echo "Starting app..."
    python app.py
else
    echo "You can start the app later with: source .portfolio-tracker/bin/activate && python app.py"
fi 