#!/bin/bash

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install requirements
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Please edit .env file and add your BOT_TOKEN"
fi

echo "Setup complete! To run the bot:"
echo "1. Edit .env file and add your bot token"
echo "2. Run: source venv/bin/activate"
echo "3. Run: python main.py"