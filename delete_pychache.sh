#!/bin/bash

# Function to delete __pycache__ directories and .pyc files
delete_pycache() {
    local directory="$1"
    
    # Find and delete all .pyc files
    find "$directory" -type f -name "*.pyc" -exec rm -f {} \;

    # Find and delete all __pycache__ directories
    find "$directory" -type d -name "__pycache__" -exec rm -rf {} +
}

# Call the function with the current directory or replace with your target directory
delete_pycache "."
