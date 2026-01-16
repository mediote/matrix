# Custom Agent Docker

Versão Docker do Custom Agent usando FastAPI com estrutura organizada.

## Estrutura do Projeto

```
custom-agent-docker/
├── src/
│   ├── main.py              # Aplicação FastAPI principal
│   ├── config.py            # Configurações e variáveis de ambiente
│   ├── models/              # Modelos Pydantic (schemas)
│   │   └── schemas.py
│   ├── routes/              # Rotas da API
│   │   ├── agent.py         # Rotas do agente
│   │   └── health.py        # Rotas de health check
│   ├── services/            # Lógica de negócio
│   │   └── agent_service.py # Serviço do agente
│   └── tools/               # Tools do agente
│       └── weather.py       # Tool de clima
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Pré-requisitos

- Docker
- Docker Compose
- Arquivo `.env` com as variáveis de ambiente necessárias

## Configuração

1. Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```

2. Edite o `.env` com suas credenciais:
- `AZURE_OPENAI_ENDPOINT`: Endpoint do Azure OpenAI
- `AZURE_OPENAI_API_VERSION`: Versão da API
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Nome do deployment
- `API_TRACES_INSTRUMENTATION_KEY`: Connection string do Application Insights (opcional)
- `ASPIRE_OTLP_ENDPOINT`: Endpoint OTLP do Aspire Dashboard (padrão: `http://localhost:4317`)

## Execução

### Usando Docker Compose (recomendado)

```bash
docker-compose up --build
```

### Usando Docker diretamente

```bash
docker build -t custom-agent .
docker run -p 8000:8000 --env-file .env custom-agent
```

## Endpoints

- `GET /` - Informações da API
- `POST /agent` - Envia mensagem para o agente
- `GET /health` - Health check

### POST /agent

Envia uma mensagem para o agente. Todos os parâmetros de configuração do agente são opcionais e têm valores padrão.

**Request Body:**
```json
{
  "message": "What's the weather in Seattle?",
  "name": "agent",
  "id": "agent",
  "instructions": "You are a helpful weather assistant.",
  "tools": ["get_weather"]
}
```

**Parâmetros:**
- `message` (obrigatório): A mensagem para enviar ao agente
- `name` (opcional, padrão: `"custom-agent"`): Nome do agente
- `id` (opcional, padrão: `"agent"`): ID do agente
- `instructions` (opcional, padrão: `"You are a helpful weather assistant."`): Instruções para o agente
- `tools` (opcional): Lista de nomes de tools disponíveis (ex: `["get_weather"]`). Se não fornecido ou vazio, o agente não terá tools.

**Response:**
```json
{
  "response": "The weather in Seattle is sunny with a high of 25°C.",
  "trace_id": "abc123..."
}
```

## Exemplo de uso

```bash
# Health check
curl http://localhost:8000/health

# Enviar mensagem para o agente (usando valores padrão, sem tools)
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the weather in Paris?"}'

# Enviar mensagem com tools
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the weather in Tokyo?",
    "tools": ["get_weather"]
  }'

# Enviar mensagem com configuração customizada completa
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the weather in Tokyo?",
    "name": "weather-bot",
    "id": "weather-bot-001",
    "instructions": "You are an expert weather assistant. Always provide detailed weather information.",
    "tools": ["get_weather"]
  }'

# Enviar mensagem sem tools (agente sem ferramentas)
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "instructions": "You are a friendly assistant.",
    "tools": null
  }'
```

**Nota:** O agente é cacheado por configuração. Agentes com a mesma configuração (name, id, instructions, tools) reutilizam a mesma instância.

## Observabilidade com Aspire Dashboard

Para visualizar traces no Aspire Dashboard, execute o container do Aspire:

```bash
docker run --rm -it -d \
    -p 18888:18888 \
    -p 4317:18889 \
    --name aspire-dashboard \
    mcr.microsoft.com/dotnet/aspire-dashboard:latest
```

Certifique-se de que a variável `ASPIRE_OTLP_ENDPOINT` no `.env` esteja configurada corretamente:
- Se o Aspire estiver rodando no mesmo host: `http://localhost:4317`
- Se estiver na mesma rede Docker: `http://aspire-dashboard:18889`

Acesse o Aspire Dashboard em: http://localhost:18888

## Documentação da API

Quando o servidor estiver rodando, acesse:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
