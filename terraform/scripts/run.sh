#!/bin/bash

# Variables
IMAGE_NAME="spacy-nel"
TAG="v1"

# Build the Docker image
echo "Building Docker image..."
docker build -t $IMAGE_NAME:$TAG .

# Run the Docker container locally
echo "Running Docker container locally..."
docker run -p 8080:8080 $IMAGE_NAME:$TAG

echo "Docker container is running locally!"
