#!/bin/bash
set -e

# Load .env file if exists
if [ -f .env ]; then
    echo "Loading .env file..."
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        # Remove spaces around = and quotes
        line=$(echo "$line" | sed 's/ *= */=/g' | sed 's/"//g')
        export "$line"
    done < .env
fi

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-custom-agent-rg}"
LOCATION="${LOCATION:-brazilsouth}"
ACR_NAME="${ACR_NAME:-customagentacr}"
CONTAINER_APP_NAME="${CONTAINER_APP_NAME:-custom-agent}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "=== Azure Container Apps Deployment ==="
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "ACR Name: $ACR_NAME"
echo "Container App: $CONTAINER_APP_NAME"
echo ""

# Check required environment variables
if [ -z "$AZURE_OPENAI_API_KEY" ]; then
    echo "Error: AZURE_OPENAI_API_KEY is not set"
    exit 1
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN is not set"
    exit 1
fi

# Login check
echo "Checking Azure login..."
az account show > /dev/null 2>&1 || { echo "Please login with 'az login'"; exit 1; }

# Create Resource Group
echo "Creating Resource Group..."
az group create --name $RESOURCE_GROUP --location $LOCATION --output none

# Create Azure Container Registry
echo "Creating Azure Container Registry..."
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --admin-enabled true \
    --output none

# Get ACR credentials
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)

# Build and push image
echo "Building and pushing Docker image..."
az acr build \
    --registry $ACR_NAME \
    --image $CONTAINER_APP_NAME:$IMAGE_TAG \
    --file Dockerfile \
    .

CONTAINER_IMAGE="$ACR_LOGIN_SERVER/$CONTAINER_APP_NAME:$IMAGE_TAG"

# Deploy with Bicep
echo "Deploying Container App..."
az deployment group create \
    --resource-group $RESOURCE_GROUP \
    --template-file deploy/azure-container-app.bicep \
    --parameters \
        containerAppName=$CONTAINER_APP_NAME \
        containerImage=$CONTAINER_IMAGE \
        azureOpenAiEndpoint="${AZURE_OPENAI_ENDPOINT:-https://medio-mkaf0sdy-swedencentral.cognitiveservices.azure.com/}" \
        azureOpenAiApiKey=$AZURE_OPENAI_API_KEY \
        azureOpenAiApiVersion="${AZURE_OPENAI_API_VERSION:-2025-04-01-preview}" \
        azureOpenAiDeploymentName="${AZURE_OPENAI_DEPLOYMENT_NAME:-gpt-5.2-chat}" \
        githubToken=$GITHUB_TOKEN \
        enableOtel="${ENABLE_OTEL:-true}" \
        otlpEndpoint="${OTEL_EXPORTER_OTLP_ENDPOINT:-}" \
        acrLoginServer=$ACR_LOGIN_SERVER \
        acrUsername=$ACR_USERNAME \
        acrPassword=$ACR_PASSWORD \
    --output none

# Get the URL
APP_URL=$(az containerapp show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo "=== Deployment Complete ==="
echo "Container App URL: https://$APP_URL"
echo "Health endpoint: https://$APP_URL/health"
echo "API docs: https://$APP_URL/docs"
