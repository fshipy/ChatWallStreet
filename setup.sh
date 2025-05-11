#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default to venv if no argument provided
USE_CONDA=false
if [ "$1" == "--conda" ]; then
    USE_CONDA=true
fi

echo -e "${BLUE}Setting up ChatWallStreet environment...${NC}"

if [ "$USE_CONDA" = true ]; then
    # Check if conda is installed
    if ! command -v conda &> /dev/null; then
        echo -e "${YELLOW}Conda is not installed. Please install conda first.${NC}"
        exit 1
    fi

    # Create or activate conda environment
    if ! conda env list | grep -q "chatwallstreet"; then
        echo -e "${GREEN}Creating conda environment...${NC}"
        conda create -n chatwallstreet python=3.10 -y
    else
        echo -e "${GREEN}Conda environment already exists.${NC}"
    fi

    # Activate conda environment
    echo -e "${GREEN}Activating conda environment...${NC}"
    eval "$(conda shell.bash hook)"
    conda activate chatwallstreet

else
    # Check if Python 3 is installed
    if ! command -v python3 &> /dev/null; then
        echo -e "${YELLOW}Python 3 is not installed. Please install Python 3 first.${NC}"
        exit 1
    fi

    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        echo -e "${GREEN}Creating virtual environment...${NC}"
        python3 -m venv .venv
    else
        echo -e "${GREEN}Virtual environment already exists.${NC}"
    fi

    # Activate virtual environment
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
python -m pip install --upgrade pip

# Install requirements
echo -e "${GREEN}Installing required packages...${NC}"
pip install -r requirements.txt

# # Start the application
echo -e "${GREEN}Starting the application...${NC}"
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000 