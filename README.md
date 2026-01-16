# Matrix - Agent Framework API

API FastAPI para orquestração de agentes de IA usando o Microsoft Agent Framework, com suporte a workflows dinâmicos e múltiplos formatos de execução.

## Características

- 🤖 **Agentes de IA**: Criação e execução de agentes com ferramentas configuráveis
- 🔄 **Workflows Dinâmicos**: Orquestração de múltiplos agentes e funções em workflows complexos
- 🛠️ **Ferramentas**: Suporte a ferramentas como code interpreter e execução de comandos CLI
- 📊 **Observabilidade**: Integração com Azure Monitor e Aspire Dashboard para traces e métricas
- 🐳 **Docker Ready**: Containerização completa com Docker e Docker Compose

## Estrutura do Projeto

```
matrix/
├── src/
│   ├── main.py                  # Aplicação FastAPI principal
│   ├── config.py                # Configurações e variáveis de ambiente
│   ├── models/                  # Modelos Pydantic (schemas)
│   │   └── schemas.py           # Schemas de requisição/resposta e workflows
│   ├── routes/                  # Rotas da API
│   │   ├── agent.py             # Rotas do agente
│   │   ├── health.py            # Rotas de health check
│   │   └── workflow.py          # Rotas de orquestração de workflows
│   ├── services/                # Lógica de negócio
│   │   ├── agent_service.py     # Serviço do agente
│   │   └── workflow_service.py  # Serviço de orquestração de workflows
│   └── tools/                   # Tools do agente
│       └── cli.py               # Tool de execução de comandos CLI
├── deploy/                      # Scripts de deploy
│   ├── azure-container-app.bicep
│   └── deploy.sh
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
└── WORKFLOW_EXAMPLES.md         # Exemplos de workflows dinâmicos
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
- `RATE_LIMIT_INTERVAL_SECONDS`: Intervalo mínimo em segundos entre chamadas à API OpenAI (padrão: `1.0`)

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
- `POST /workflow` - Executa workflows dinâmicos de orquestração
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

## Exemplos de Uso

### Endpoint de Agente

```bash
# Health check
curl http://localhost:8000/health

# Enviar mensagem para o agente (usando valores padrão)
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how can you help me?"}'

# Enviar mensagem com configuração customizada
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Analyze this data: [1, 2, 3, 4, 5]",
    "name": "data-analyzer",
    "instructions": "You are a data analysis expert.",
    "tools": ["code_interpreter"]
  }'
```

### Endpoint de Workflow

```bash
# Workflow simples: dois agentes em sequência
curl -X POST http://localhost:8000/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {
      "name": "simple-pipeline",
      "executors": [
        {
          "type": "agent",
          "name": "processor",
          "instructions": "Process the input"
        },
        {
          "type": "agent",
          "name": "formatter",
          "instructions": "Format the output"
        }
      ],
      "edges": [
        {
          "from_executor": "processor",
          "to_executor": "formatter",
          "edge_type": "direct"
        }
      ],
      "start_executor": "processor"
    },
    "input_message": "Process this: Hello World"
  }'

# Workflow com agente + função CLI
curl -X POST http://localhost:8000/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {
      "name": "agent-cli-workflow",
      "executors": [
        {
          "type": "agent",
          "name": "command_gen",
          "instructions": "Generate a CLI command"
        },
        {
          "type": "function",
          "name": "executor",
          "function_name": "execute_command"
        }
      ],
      "edges": [
        {
          "from_executor": "command_gen",
          "to_executor": "executor",
          "edge_type": "direct"
        }
      ],
      "start_executor": "command_gen"
    },
    "input_message": "List Python files in current directory"
  }'
```

**Nota:** O agente é cacheado por configuração. Agentes com a mesma configuração (name, id, instructions, tools) reutilizam a mesma instância.

## Rate Limiting

Para evitar erros de rate limit da OpenAI, o sistema implementa um rate limiter que controla o intervalo mínimo entre chamadas à API.

### Configuração

Configure o intervalo mínimo através da variável de ambiente `RATE_LIMIT_INTERVAL_SECONDS`:

```bash
# .env
RATE_LIMIT_INTERVAL_SECONDS=2.0  # 2 segundos entre cada chamada
```

**Valores recomendados:**
- `1.0` (padrão): Para uso normal
- `2.0`: Para evitar rate limits em uso intenso
- `3.0` ou mais: Para contas com limites mais restritivos

### Como Funciona

O rate limiter:
- ✅ Garante um intervalo mínimo entre chamadas à API OpenAI
- ✅ Aplica automaticamente em todos os agentes e workflows
- ✅ É thread-safe e funciona com execuções concorrentes
- ✅ Registra logs quando está aguardando (nível DEBUG)

### Exemplo de Uso

Com `RATE_LIMIT_INTERVAL_SECONDS=2.0`:
- Chamada 1: executa imediatamente
- Chamada 2: aguarda 2 segundos após a primeira
- Chamada 3: aguarda 2 segundos após a segunda
- E assim por diante...

Isso garante que você não exceda os limites de taxa da OpenAI mesmo com múltiplas requisições simultâneas.

## Workflows Dinâmicos

O projeto inclui uma camada de orquestração dinâmica baseada no [Microsoft Agent Framework Workflows](https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/overview), permitindo criar e executar workflows complexos sem recompilar código.

### POST /workflow

Cria e executa workflows dinâmicos compostos por múltiplos executores (agentes ou funções) conectados por edges.

**Request Body:**
```json
{
  "workflow": {
    "name": "data-analysis-pipeline",
    "description": "Analisa e formata dados",
    "executors": [
      {
        "type": "agent",
        "name": "analyzer",
        "agent_name": "data-analyzer",
        "instructions": "Você é um analista de dados. Analise os dados fornecidos.",
        "tools": ["code_interpreter"]
      },
      {
        "type": "agent",
        "name": "formatter",
        "agent_name": "data-formatter",
        "instructions": "Você formata dados de forma clara e organizada."
      }
    ],
    "edges": [
      {
        "from_executor": "analyzer",
        "to_executor": "formatter",
        "edge_type": "direct"
      }
    ],
    "start_executor": "analyzer",
    "workflow_type": "sequential"
  },
  "input_message": "Analise estes dados: [10, 20, 30, 40, 50]",
  "streaming": false
}
```

**Parâmetros do Workflow:**

- `name` (obrigatório): Nome único do workflow
- `description` (opcional): Descrição do workflow
- `executors` (obrigatório): Lista de executores
  - **Agent Executor:**
    - `type`: `"agent"`
    - `name`: Nome único do executor
    - `agent_name`: Nome do agente (opcional)
    - `agent_id`: ID do agente (opcional)
    - `instructions`: Instruções para o agente
    - `tools`: Lista de ferramentas (opcional, ex: `["code_interpreter", "execute_command"]`)
  - **Function Executor:**
    - `type`: `"function"`
    - `name`: Nome único do executor
    - `function_name`: Nome da função (ex: `"execute_command"`)
    - `parameters`: Parâmetros para a função (opcional)
- `edges` (obrigatório): Lista de conexões entre executores
  - `from_executor`: Nome do executor origem
  - `to_executor`: Nome do executor destino
  - `edge_type`: Tipo de edge (`"direct"`, `"conditional"`, `"fan_out"`, `"fan_in"`)
  - `condition`: Condição para edges condicionais (opcional)
- `start_executor` (obrigatório): Nome do executor inicial
- `workflow_type` (opcional): Tipo do workflow (`"sequential"`, `"parallel"`, `"conditional"`, `"dynamic"`)

**Parâmetros da Requisição:**

- `workflow` (obrigatório): Definição do workflow
- `input_message` (obrigatório): Mensagem inicial para o workflow
- `streaming` (opcional, padrão: `false`): Se `true`, retorna eventos em tempo real

**Response:**
```json
{
  "output": "Análise completa dos dados...",
  "trace_id": "abc123...",
  "execution_steps": [
    {
      "step": "executor_created",
      "executor": "analyzer",
      "type": "agent"
    },
    {
      "step": "edge_added",
      "from": "analyzer",
      "to": "formatter",
      "type": "direct"
    },
    {
      "step": "workflow_built",
      "status": "success"
    },
    {
      "step": "workflow_execution_completed",
      "status": "success",
      "output_length": 150
    }
  ],
  "workflow_id": "data-analysis-pipeline"
}
```

### Exemplos de Workflows

#### Workflow Sequencial Simples

Dois agentes em sequência: análise → formatação

```bash
curl -X POST http://localhost:8000/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {
      "name": "analyze-and-format",
      "executors": [
        {
          "type": "agent",
          "name": "analyzer",
          "instructions": "Analise os dados fornecidos",
          "tools": ["code_interpreter"]
        },
        {
          "type": "agent",
          "name": "formatter",
          "instructions": "Formate o resultado de forma clara"
        }
      ],
      "edges": [
        {
          "from_executor": "analyzer",
          "to_executor": "formatter",
          "edge_type": "direct"
        }
      ],
      "start_executor": "analyzer"
    },
    "input_message": "Analise: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]"
  }'
```

#### Workflow com Função Customizada

Agente gera comando → Executa comando CLI

```bash
curl -X POST http://localhost:8000/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {
      "name": "agent-command-pipeline",
      "executors": [
        {
          "type": "agent",
          "name": "command_generator",
          "instructions": "Gere um comando CLI apropriado baseado na solicitação"
        },
        {
          "type": "function",
          "name": "executor",
          "function_name": "execute_command",
          "parameters": {
            "working_directory": "."
          }
        }
      ],
      "edges": [
        {
          "from_executor": "command_generator",
          "to_executor": "executor",
          "edge_type": "direct"
        }
      ],
      "start_executor": "command_generator"
    },
    "input_message": "Liste os arquivos Python no diretório atual"
  }'
```

#### Workflow Multi-Estágio

Pipeline com três estágios: análise → validação → formatação

```bash
curl -X POST http://localhost:8000/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {
      "name": "three-stage-pipeline",
      "executors": [
        {
          "type": "agent",
          "name": "analyzer",
          "instructions": "Analise o conteúdo fornecido",
          "tools": ["code_interpreter"]
        },
        {
          "type": "agent",
          "name": "validator",
          "instructions": "Valide a análise anterior"
        },
        {
          "type": "agent",
          "name": "formatter",
          "instructions": "Formate o resultado final"
        }
      ],
      "edges": [
        {
          "from_executor": "analyzer",
          "to_executor": "validator",
          "edge_type": "direct"
        },
        {
          "from_executor": "validator",
          "to_executor": "formatter",
          "edge_type": "direct"
        }
      ],
      "start_executor": "analyzer"
    },
    "input_message": "Analise este código: def hello(): print(\"Hello\")"
  }'
```

#### Workflow de Desenvolvimento Completo

Pipeline completa de desenvolvimento: análise → planejamento → codificação → testes → commit → push

```bash
curl -X POST http://localhost:8000/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {
      "name": "development-pipeline",
      "description": "Pipeline completa de desenvolvimento automatizado",
      "executors": [
        {
          "type": "agent",
          "name": "analyser",
          "agent_name": "architect_analyser",
          "instructions": "Você é um analista de código especializado. Analise o código fornecido e identifique problemas e oportunidades de melhoria.",
          "tools": ["code_interpreter"]
        },
        {
          "type": "agent",
          "name": "planner",
          "agent_name": "architect_planner",
          "instructions": "Você é um planejador de desenvolvimento. Crie um plano detalhado de ação baseado na análise.",
          "tools": []
        },
        {
          "type": "agent",
          "name": "coder",
          "agent_name": "architect_coder",
          "instructions": "Você é um desenvolvedor experiente. Implemente as mudanças conforme o plano fornecido usando as ferramentas disponíveis.",
          "tools": ["code_interpreter", "execute_command"]
        },
        {
          "type": "agent",
          "name": "tester",
          "agent_name": "architect_tester",
          "instructions": "Você é um especialista em testes. Valide o código implementado e forneça feedback sobre a qualidade.",
          "tools": ["code_interpreter", "execute_command"]
        },
        {
          "type": "agent",
          "name": "pusher",
          "agent_name": "architect_pusher",
          "instructions": "Você é responsável por fazer commit e push das mudanças. Faça commit com mensagens claras e faça push para o repositório remoto na branch main.",
          "tools": ["execute_command"]
        },
        {
          "type": "agent",
          "name": "puller",
          "agent_name": "architect_puller",
          "instructions": "Você é responsável por verificar o status final do repositório e fornecer um resumo do que foi realizado.",
          "tools": ["execute_command"]
        }
      ],
      "edges": [
        {
          "from_executor": "analyser",
          "to_executor": "planner",
          "edge_type": "direct"
        },
        {
          "from_executor": "planner",
          "to_executor": "coder",
          "edge_type": "direct"
        },
        {
          "from_executor": "coder",
          "to_executor": "tester",
          "edge_type": "direct"
        },
        {
          "from_executor": "tester",
          "to_executor": "pusher",
          "edge_type": "direct"
        },
        {
          "from_executor": "pusher",
          "to_executor": "puller",
          "edge_type": "direct"
        }
      ],
      "start_executor": "analyser",
      "workflow_type": "sequential"
    },
    "input_message": "Refatore o ClimateAgent para melhorar a estrutura interna preservando o comportamento. Depois, delete o arquivo README.md e faça commit e push de todas as mudanças para o repositório https://github.com/mediote/architect na branch main."
  }'
```

Este workflow demonstra uma pipeline completa de desenvolvimento com 6 agentes especializados:
1. **Analyser**: Analisa código e identifica melhorias
2. **Planner**: Cria plano de ação detalhado
3. **Coder**: Implementa as mudanças
4. **Tester**: Valida e testa o código
5. **Pusher**: Faz commit e push das mudanças
6. **Puller**: Verifica status final e fornece resumo

### Funcionalidades dos Workflows

- **Orquestração Dinâmica**: Crie workflows via API sem recompilar código
- **Múltiplos Formatos**: Sequencial, paralelo, condicional, dinâmico
- **Executores Flexíveis**: 
  - Agentes de IA com ferramentas configuráveis
  - Funções customizadas (ex: `execute_command`)
- **Edges Configuráveis**: Conexões diretas e condicionais
- **Observabilidade**: Trace IDs e logs detalhados de execução
- **Streaming**: Suporte a execução streaming para respostas em tempo real

### Documentação Adicional

- [WORKFLOW_EXAMPLES.md](./WORKFLOW_EXAMPLES.md) - Exemplos detalhados de workflows

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
