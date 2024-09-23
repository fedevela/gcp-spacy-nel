# Makefile

# Variables
IMAGE_NAME := spacy-nel
TAG := v1
PROJECT_ID := federicoveladataartcomproject
REGION := us-central1

# Phony targets
.PHONY: all build run push deploy rundev

# Default target
all: build

# Run the app locally
run:
	@echo "Running the application locally..."
	python3 app.py

# Run the app locally in watch mode
rundev:
	@echo "Running the application in development mode with live reloading..."
	watchmedo auto-restart --recursive --pattern="*.py" -- python3 app.py

# Build the Docker image
build:
	@echo "Building Docker image..."
	docker build -t $(IMAGE_NAME):$(TAG) .
	@echo "Docker image $(IMAGE_NAME):$(TAG) built successfully!"

# Tag and push the Docker image to Google Container Registry
push: build
	@echo "Tagging Docker image for Google Container Registry..."
	docker tag $(IMAGE_NAME):$(TAG) gcr.io/$(PROJECT_ID)/$(IMAGE_NAME):$(TAG)
	@echo "Pushing Docker image to Google Container Registry..."
	docker push gcr.io/$(PROJECT_ID)/$(IMAGE_NAME):$(TAG)

# Deploy the Docker image to Google Cloud Run
deploy: push
	@echo "Setting Google Cloud project..."
	gcloud config set project $(PROJECT_ID)
	@echo "Deploying the Docker image to Cloud Run..."
	gcloud run deploy $(IMAGE_NAME) \
		--image gcr.io/$(PROJECT_ID)/$(IMAGE_NAME):$(TAG) \
		--region $(REGION) \
		--allow-unauthenticated
	@echo "Deployment completed!"
