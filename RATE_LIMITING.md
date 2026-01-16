# Rate Limiting - Prevenção de Rate Limits da OpenAI

Este documento explica como configurar e usar o sistema de rate limiting para evitar erros de rate limit da OpenAI.

## Problema

Quando você faz muitas chamadas à API da OpenAI em um curto período, pode receber erros como:
- `429 Too Many Requests`
- `RateLimitError`
- `Quota exceeded`

## Solução

O sistema implementa um **rate limiter** que garante um intervalo mínimo entre chamadas à API OpenAI.

## Configuração

### Variável de Ambiente

Configure o intervalo mínimo através da variável `RATE_LIMIT_INTERVAL_SECONDS` no arquivo `.env`:

```bash
# Intervalo mínimo em segundos entre chamadas à API OpenAI
RATE_LIMIT_INTERVAL_SECONDS=2.0
```

### Valores Recomendados

| Cenário | Valor Recomendado | Descrição |
|---------|-------------------|-----------|
| Uso normal | `1.0` (padrão) | Para uso ocasional |
| Uso intenso | `2.0` | Para evitar rate limits em workflows complexos |
| Contas restritivas | `3.0` ou mais | Para contas com limites mais baixos |
| Múltiplos workflows | `2.5` | Quando executando vários workflows simultaneamente |

## Como Funciona

### Mecanismo

1. **Antes de cada chamada à API OpenAI**, o sistema verifica quando foi a última chamada
2. Se o intervalo desde a última chamada for **menor** que `RATE_LIMIT_INTERVAL_SECONDS`, o sistema **aguarda** o tempo necessário
3. Após o intervalo, a chamada é executada normalmente

### Exemplo Prático

Com `RATE_LIMIT_INTERVAL_SECONDS=2.0`:

```
Tempo 0.0s: Chamada 1 → Executa imediatamente
Tempo 0.5s: Chamada 2 → Aguarda 1.5s → Executa em 2.0s
Tempo 1.0s: Chamada 3 → Aguarda 1.0s → Executa em 2.0s
Tempo 2.5s: Chamada 4 → Aguarda 0.5s → Executa em 3.0s
```

### Thread-Safe

O rate limiter é **thread-safe** e funciona corretamente mesmo com:
- ✅ Múltiplas requisições simultâneas
- ✅ Workflows com múltiplos agentes executando em paralelo
- ✅ Execuções concorrentes de diferentes endpoints

## Onde é Aplicado

O rate limiting é aplicado automaticamente em:

1. **Endpoint `/agent`**: Todas as chamadas de agentes individuais
2. **Endpoint `/workflow`**: Cada executor de agente dentro de workflows
3. **AgentExecutor**: Todos os agentes em workflows

## Logs

Quando o rate limiter está aguardando, logs são gerados no nível DEBUG:

```
DEBUG: Rate limiting: waiting 1.50s before next API call
```

Para ver esses logs, configure o nível de logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Monitoramento

### Verificar se está funcionando

1. Configure um intervalo maior (ex: `5.0`)
2. Faça múltiplas requisições rapidamente
3. Observe que há um atraso entre as execuções

### Métricas

O rate limiter não expõe métricas diretamente, mas você pode:
- Monitorar os logs para ver quando está aguardando
- Verificar os tempos de resposta das requisições
- Usar Azure Monitor para rastrear latência

## Troubleshooting

### Ainda recebendo rate limits?

1. **Aumente o intervalo**: Tente `3.0` ou `5.0` segundos
2. **Verifique múltiplas instâncias**: Se você tem múltiplas instâncias do serviço rodando, cada uma tem seu próprio rate limiter
3. **Verifique outros serviços**: Outros serviços podem estar usando a mesma conta OpenAI

### Performance lenta?

1. **Reduza o intervalo**: Se não está recebendo rate limits, pode reduzir para `0.5` ou `1.0`
2. **Otimize workflows**: Reduza o número de agentes em workflows quando possível

## Exemplo de Configuração Completa

```bash
# .env
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# Rate limiting - 2 segundos entre chamadas
RATE_LIMIT_INTERVAL_SECONDS=2.0
```

## Implementação Técnica

O rate limiter é implementado em `src/utils/rate_limiter.py`:

- **Classe `RateLimiter`**: Gerencia o intervalo entre chamadas
- **Função `get_rate_limiter()`**: Retorna instância singleton global
- **Decorator `@rate_limited`**: Pode ser usado para decorar funções (futuro)

## Referências

- [OpenAI Rate Limits](https://platform.openai.com/docs/guides/rate-limits)
- [Azure OpenAI Rate Limits](https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-limits)
