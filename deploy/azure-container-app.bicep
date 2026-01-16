@description('Name of the Container App')
param containerAppName string = 'custom-agent'

@description('Name of the Container App Environment')
param containerAppEnvName string = 'custom-agent-env'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Container image to deploy')
param containerImage string

@description('Azure OpenAI Endpoint')
@secure()
param azureOpenAiEndpoint string = 'https://medio-mkaf0sdy-swedencentral.cognitiveservices.azure.com/'

@description('Azure OpenAI API Key')
@secure()
param azureOpenAiApiKey string

@description('Azure OpenAI API Version')
param azureOpenAiApiVersion string = '2025-04-01-preview'

@description('Azure OpenAI Deployment Name')
param azureOpenAiDeploymentName string = 'gpt-5.2-chat'

@description('GitHub Token for git operations')
@secure()
param githubToken string

@description('Enable OpenTelemetry')
param enableOtel bool = true

@description('OTLP Exporter Endpoint')
param otlpEndpoint string = ''

@description('ACR Login Server')
param acrLoginServer string

@description('ACR Username')
param acrUsername string

@description('ACR Password')
@secure()
param acrPassword string

// Container App Environment
resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppEnvName
  location: location
  properties: {
    zoneRedundant: false
  }
}

// Container App
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: acrLoginServer
          username: acrUsername
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acrPassword
        }
        {
          name: 'azure-openai-endpoint'
          value: azureOpenAiEndpoint
        }
        {
          name: 'azure-openai-api-key'
          value: azureOpenAiApiKey
        }
        {
          name: 'github-token'
          value: githubToken
        }
      ]
    }
    template: {
      containers: [
        {
          name: containerAppName
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              secretRef: 'azure-openai-endpoint'
            }
            {
              name: 'AZURE_OPENAI_API_KEY'
              secretRef: 'azure-openai-api-key'
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: azureOpenAiApiVersion
            }
            {
              name: 'AZURE_OPENAI_DEPLOYMENT_NAME'
              value: azureOpenAiDeploymentName
            }
            {
              name: 'GITHUB_TOKEN'
              secretRef: 'github-token'
            }
            {
              name: 'ENABLE_OTEL'
              value: string(enableOtel)
            }
            {
              name: 'ENABLE_INSTRUMENTATION'
              value: string(enableOtel)
            }
            {
              name: 'OTEL_EXPORTER_OTLP_ENDPOINT'
              value: otlpEndpoint
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 30
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output containerAppName string = containerApp.name
