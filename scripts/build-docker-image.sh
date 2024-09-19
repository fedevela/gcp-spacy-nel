#!/bin/bash

# Variables
IMAGE_NAME="spacy-nel"
TAG="v1"

# Build the Docker image
echo "Building Docker image..."
docker build -t $IMAGE_NAME:$TAG .

echo "Docker image $IMAGE_NAME:$TAG built successfully!"
