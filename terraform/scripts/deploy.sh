#!/bin/bash

# Variables
PROJECT_ID="federicoveladataartcomproject"
IMAGE_NAME="spacy-nel"
REGION="us-central1"
TAG="v1"

# # Authenticate with Google Cloud
# echo "Authenticating with Google Cloud..."
# gcloud auth login

# Set the project ID
gcloud config set project $PROJECT_ID

# # Enable necessary APIs
# echo "Enabling necessary APIs..."
# gcloud services enable run.googleapis.com
# gcloud services enable containerregistry.googleapis.com

# Build the Docker image
# echo "Building Docker image..."
# docker build -t gcr.io/$PROJECT_ID/$IMAGE_NAME:$TAG .

# Push the Docker image to Google Container Registry (GCR)
# echo "Pushing Docker image to Google Container Registry..."
# docker push gcr.io/$PROJECT_ID/$IMAGE_NAME:$TAG

# Deploy the Docker image to Cloud Run
echo "Deploying the Docker image to Cloud Run..."
gcloud run deploy $IMAGE_NAME \
  --image gcr.io/$PROJECT_ID/$IMAGE_NAME:$TAG \
  --region $REGION \
  --allow-unauthenticated

echo "Deployment completed!"
