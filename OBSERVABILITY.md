# Observabilidade e Instrumentação

Este documento descreve a instrumentação OpenTelemetry e o sistema de logging implementado seguindo o padrão do Microsoft Agent Framework.

## Instrumentação OpenTelemetry

### Spans Criados

A instrumentação cria spans hierárquicos seguindo as convenções do MAF:

#### 1. Workflow Level
- **Span**: `workflow.{workflow_name}`
- **Kind**: `SERVER`
- **Atributos**:
  - `workflow.name`
  - `workflow.type`
  - `workflow.executor_count`
  - `workflow.edge_count`
  - `workflow.start_executor`
  - `workflow.status` (success/error)
  - `workflow.output_length`

#### 2. Build Phase
- **Span**: `workflow.build.executors`
- **Kind**: `INTERNAL`
- **Child Spans**:
  - `workflow.executor.create.{executor_name}` - Para cada executor criado
  - `workflow.build.graph` - Construção do grafo
  - `workflow.build.finalize` - Finalização

#### 3. Execution Phase
- **Span**: `workflow.execute`
- **Kind**: `INTERNAL`
- **Atributos**:
  - `workflow.streaming`
  - `workflow.input_length`
  - `workflow.events_count` (streaming)
  - `workflow.output_length`

#### 4. Executor Level
- **Span**: `executor.agent.{agent_name}`
- **Kind**: `INTERNAL`
- **Atributos**:
  - `executor.name`
  - `executor.id`
  - `executor.type`
  - `executor.input_length`
  - `executor.output_length`
  - `executor.status` (success/error)
  - `executor.error` (se houver erro)
  - `executor.error_type`

#### 5. Agent Invocation (GenAI)
- **Span**: `gen_ai.invoke_agent`
- **Kind**: `CLIENT`
- **Atributos** (seguindo convenções GenAI):
  - `gen_ai.operation.name`: "agent.run"
  - `gen_ai.agent.name`
  - `gen_ai.request.type`: "chat"
  - `gen_ai.response.finish_reason`: "stop"
  - `gen_ai.response.length`

#### 6. Rate Limiting
- **Span**: `rate_limit.wait`
- **Kind**: `INTERNAL`
- **Atributos**:
  - `rate_limit.min_interval`
  - `rate_limit.recent_errors`
  - `rate_limit.extra_delay`
  - `rate_limit.wait_time`
  - `rate_limit.elapsed_since_last`

- **Span**: `rate_limit.error`
- **Kind**: `INTERNAL`
- **Status**: `ERROR`
- **Atributos**:
  - `rate_limit.error_count`
  - `rate_limit.error_time`
  - `rate_limit.severe` (se > 10 erros)

## Sistema de Logging

### Formato de Logs

Todos os logs seguem um formato padronizado com prefixos para fácil filtragem:

#### Prefixos de Log

- `[WORKFLOW START]` - Início do workflow
- `[WORKFLOW BUILD]` - Fase de construção
- `[WORKFLOW EXECUTE]` - Fase de execução
- `[WORKFLOW SUCCESS]` - Workflow completado com sucesso
- `[WORKFLOW ERROR]` - Erro no workflow
- `[EXECUTOR CREATE]` - Criação de executor
- `[EXECUTOR CREATED]` - Executor criado
- `[EXECUTOR START]` - Início de execução do executor
- `[EXECUTOR SUCCESS]` - Executor completado
- `[EXECUTOR ERROR]` - Erro no executor
- `[AGENT RUN]` - Chamada à API OpenAI
- `[AGENT SUCCESS]` - Agente completado
- `[RATE LIMIT]` - Informações de rate limiting
- `[RATE LIMIT ERROR]` - Erro de rate limit
- `[WORKFLOW EVENT]` - Eventos durante streaming

### Exemplo de Logs

```
[WORKFLOW START] 'project-atlas-pipeline' | Trace ID: abc123... | Executors: 6 | Edges: 5
[EXECUTOR CREATE] 'puller' (type: agent)
[EXECUTOR CREATED] 'puller' ✓
[WORKFLOW BUILD] Building graph structure
[WORKFLOW BUILD] Start executor: puller
[WORKFLOW BUILD] Added 5 edges
[WORKFLOW BUILD] Workflow built successfully ✓
[WORKFLOW EXECUTE] Starting execution | Input length: 150 chars | Streaming: false
[EXECUTOR START] Agent 'architect_puller' | Input: 150 chars
[RATE LIMIT] Waiting 2.50s | Base: 3.0s, Extra: 0.50s | Elapsed: 0.50s
[AGENT RUN] 'architect_puller' calling OpenAI API
[AGENT SUCCESS] 'architect_puller' | Response: 450 chars
[EXECUTOR SUCCESS] Agent 'architect_puller' ✓
[WORKFLOW SUCCESS] 'project-atlas-pipeline' completed | Output: 34028 chars | Trace ID: abc123...
```

## Rastreamento de Erros

### Quando um Erro Ocorre

1. **Span marcado com erro**:
   - Status: `ERROR`
   - Atributo `executor.error` ou `workflow.error`
   - Atributo `executor.error_type` ou `workflow.error_type`

2. **Logs detalhados**:
   - `[EXECUTOR ERROR]` ou `[WORKFLOW ERROR]`
   - Stack trace completo (exc_info=True)
   - Trace ID incluído

3. **Execution Steps**:
   - Step `workflow_execution_failed` adicionado
   - Inclui `error`, `error_type`

### Exemplo de Erro

```
[EXECUTOR ERROR] Agent 'architect_coder' failed: Rate limit exceeded | Trace ID: abc123...
[WORKFLOW ERROR] 'project-atlas-pipeline' failed: Rate limit exceeded | Trace ID: abc123...
```

## Visualização no Azure Monitor / Aspire

### Hierarquia de Spans

```
workflow.project-atlas-pipeline (SERVER)
├── workflow.build.executors (INTERNAL)
│   ├── workflow.executor.create.puller (INTERNAL)
│   ├── workflow.executor.create.analyser (INTERNAL)
│   └── ...
├── workflow.build.graph (INTERNAL)
├── workflow.build.finalize (INTERNAL)
└── workflow.execute (INTERNAL)
    ├── executor.agent.architect_puller (INTERNAL)
    │   ├── executor.rate_limit (INTERNAL)
    │   └── gen_ai.invoke_agent (CLIENT)
    ├── executor.agent.architect_analyser (INTERNAL)
    │   ├── executor.rate_limit (INTERNAL)
    │   └── gen_ai.invoke_agent (CLIENT)
    └── ...
```

### Filtros Úteis

No Azure Monitor ou Aspire Dashboard, você pode filtrar por:

- **Trace ID**: Para ver todo o workflow
- **Span name**: `workflow.*`, `executor.*`, `gen_ai.*`
- **Atributos**: `workflow.name`, `executor.name`, `gen_ai.agent.name`
- **Status**: `ERROR` para ver apenas falhas

## Convenções Seguidas

### OpenTelemetry GenAI Semantic Conventions

Seguimos as convenções do MAF:
- `gen_ai.operation.name`: Nome da operação
- `gen_ai.agent.name`: Nome do agente
- `gen_ai.request.type`: Tipo de requisição
- `gen_ai.response.finish_reason`: Razão de término
- `gen_ai.response.length`: Tamanho da resposta

### Span Kinds

- **SERVER**: Workflow principal (entrada)
- **CLIENT**: Chamadas externas (OpenAI API)
- **INTERNAL**: Operações internas (executores, rate limiting)

## Melhorias Implementadas

1. ✅ **Logs estruturados** com prefixos para fácil filtragem
2. ✅ **Spans hierárquicos** seguindo padrão MAF
3. ✅ **Atributos semânticos** para rastreamento
4. ✅ **Rastreamento de rate limits** com spans dedicados
5. ✅ **Erros detalhados** com stack traces e contexto
6. ✅ **Trace IDs** em todos os logs para correlação

## Como Usar

### Ver Logs no Terminal

```bash
# Ver todos os logs do workflow
docker-compose logs agent | grep "\[WORKFLOW"

# Ver logs de um executor específico
docker-compose logs agent | grep "\[EXECUTOR.*puller"

# Ver erros
docker-compose logs agent | grep "\[.*ERROR\]"

# Ver rate limiting
docker-compose logs agent | grep "\[RATE LIMIT"
```

### Ver Traces no Aspire Dashboard

1. Acesse http://localhost:18888
2. Vá para a seção "Traces"
3. Filtre por:
   - Service: `custom-agent`
   - Operation: `workflow.*`
4. Clique em um trace para ver a hierarquia completa

### Ver Traces no Azure Monitor

1. Acesse o Application Insights
2. Vá para "Transaction search" ou "Application map"
3. Filtre por:
   - Operation name: `workflow.*`
   - Custom properties: `workflow.name`

## Troubleshooting

### Não vejo spans no Aspire

1. Verifique se `ASPIRE_OTLP_ENDPOINT` está configurado
2. Verifique se o Aspire Dashboard está rodando
3. Verifique os logs para erros de conexão OTLP

### Logs não aparecem

1. Verifique o nível de logging (INFO/DEBUG)
2. Verifique se os prefixos estão corretos
3. Use `docker-compose logs -f agent` para seguir logs em tempo real

### Erros de rate limit ainda ocorrem

1. Verifique os logs `[RATE LIMIT]` para ver se está aguardando
2. Aumente `RATE_LIMIT_INTERVAL_SECONDS` no `.env`
3. Verifique os spans `rate_limit.*` no Aspire para diagnóstico
