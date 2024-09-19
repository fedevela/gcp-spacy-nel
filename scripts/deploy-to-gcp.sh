#!/bin/bash

# Variables
PROJECT_ID="federicoveladataartcomproject"
IMAGE_NAME="spacy-nel"
REGION="us-central1"
TAG="v1"

# Set the project ID
gcloud config set project $PROJECT_ID

# Deploy the Docker image to Cloud Run
echo "Deploying the Docker image to Cloud Run..."
gcloud run deploy $IMAGE_NAME \
  --image gcr.io/$PROJECT_ID/$IMAGE_NAME:$TAG \
  --region $REGION \
  --allow-unauthenticated

echo "Deployment completed!"
