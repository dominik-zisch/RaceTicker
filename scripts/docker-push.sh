#!/bin/bash
# Script to build and push Race Ticker Docker image to Docker Hub

set -e

# Default values
DOCKERHUB_USERNAME="${DOCKERHUB_USERNAME:-}"
VERSION="${1:-latest}"

# Check if Docker Hub username is set
if [ -z "$DOCKERHUB_USERNAME" ]; then
    echo "Error: DOCKERHUB_USERNAME environment variable not set"
    echo "Usage: DOCKERHUB_USERNAME=yourusername ./scripts/docker-push.sh [version]"
    echo "Example: DOCKERHUB_USERNAME=dominikzisch ./scripts/docker-push.sh v1.0.1"
    exit 1
fi

IMAGE_NAME="${DOCKERHUB_USERNAME}/race-ticker"
FULL_TAG="${IMAGE_NAME}:${VERSION}"

echo "Building image: ${FULL_TAG}"
docker build -t "${FULL_TAG}" .

# If version is not 'latest', also tag as latest
if [ "$VERSION" != "latest" ]; then
    echo "Tagging as latest: ${IMAGE_NAME}:latest"
    docker tag "${FULL_TAG}" "${IMAGE_NAME}:latest"
fi

echo "Pushing to Docker Hub..."
docker push "${FULL_TAG}"

if [ "$VERSION" != "latest" ]; then
    docker push "${IMAGE_NAME}:latest"
fi

echo "✅ Successfully pushed ${FULL_TAG} to Docker Hub"
if [ "$VERSION" != "latest" ]; then
    echo "✅ Also pushed ${IMAGE_NAME}:latest"
fi
