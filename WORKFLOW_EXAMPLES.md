# Exemplos de Workflows Dinâmicos

Este documento mostra como usar a camada de orquestração dinâmica do Microsoft Agent Framework.

## Índice

- [Exemplo 1: Workflow Sequencial Simples](#exemplo-1-workflow-sequencial-simples)
- [Exemplo 2: Workflow com Função Customizada](#exemplo-2-workflow-com-função-customizada)
- [Exemplo 3: Workflow com Múltiplos Agentes](#exemplo-3-workflow-com-múltiplos-agentes)
- [Exemplo 4: Workflow Condicional](#exemplo-4-workflow-condicional-futuro)
- [Exemplo 5: Agente de Desenvolvimento Completo](#exemplo-5-agente-de-desenvolvimento-completo)

## Endpoint

`POST /workflow`

## Estrutura Básica

Um workflow é composto por:
- **Executores**: Unidades de processamento (agentes ou funções)
- **Edges**: Conexões entre executores
- **Start Executor**: Executor inicial do workflow

## Exemplo 1: Workflow Sequencial Simples

Dois agentes em sequência - um analisa dados, outro formata o resultado.

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
        "instructions": "Você é um analista de dados. Analise os dados fornecidos e forneça insights.",
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
  "input_message": "Analise estes dados: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]",
  "streaming": false
}
```

## Exemplo 2: Workflow com Função Customizada

Agente processa uma mensagem e depois executa um comando CLI.

```json
{
  "workflow": {
    "name": "agent-then-command",
    "description": "Agente processa e depois executa comando",
    "executors": [
      {
        "type": "agent",
        "name": "processor",
        "agent_name": "command-generator",
        "instructions": "Gere um comando CLI apropriado baseado na solicitação do usuário."
      },
      {
        "type": "function",
        "name": "command_executor",
        "function_name": "execute_command",
        "parameters": {
          "working_directory": "."
        }
      }
    ],
    "edges": [
      {
        "from_executor": "processor",
        "to_executor": "command_executor",
        "edge_type": "direct"
      }
    ],
    "start_executor": "processor",
    "workflow_type": "sequential"
  },
  "input_message": "Liste os arquivos no diretório atual",
  "streaming": false
}
```

## Exemplo 3: Workflow com Múltiplos Agentes

Pipeline com três estágios: análise, validação e formatação.

```json
{
  "workflow": {
    "name": "three-stage-pipeline",
    "description": "Pipeline de três estágios",
    "executors": [
      {
        "type": "agent",
        "name": "analyzer",
        "agent_name": "stage1-analyzer",
        "instructions": "Analise o conteúdo fornecido.",
        "tools": ["code_interpreter"]
      },
      {
        "type": "agent",
        "name": "validator",
        "agent_name": "stage2-validator",
        "instructions": "Valide a análise anterior e verifique se está correta."
      },
      {
        "type": "agent",
        "name": "formatter",
        "agent_name": "stage3-formatter",
        "instructions": "Formate o resultado final de forma clara."
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
    "start_executor": "analyzer",
    "workflow_type": "sequential"
  },
  "input_message": "Analise este código Python: def hello(): print('Hello World')",
  "streaming": false
}
```

## Exemplo 4: Workflow Condicional (Futuro)

Workflow com roteamento condicional baseado no conteúdo da mensagem.

## Exemplo 5: Agente de Desenvolvimento Completo

Workflow completo para um agente de desenvolvimento que executa uma pipeline de desenvolvimento: análise → planejamento → codificação → testes → commit → push.

### ⚠️ Nota Importante: Push de Branches

Quando um executor cria uma branch e faz commits, **é crítico fazer push da branch para o remoto** antes de passar para os próximos estágios. Caso contrário, os executores downstream (como `tester` e `pusher`) não conseguirão acessar a branch.

**Exemplo correto no executor `coder`:**
```
TASK:
1) Create feature branch: refactor/project-atlas-architecture
2) Make changes and commit
3) **CRITICAL**: Push branch to origin: git push -u origin refactor/project-atlas-architecture
   - This MUST be done so downstream stages can access the branch
   - Use -u to set upstream tracking
   - Do NOT force push
```

Este exemplo demonstra como orquestrar múltiplos agentes especializados em uma pipeline de desenvolvimento automatizada.

```json
{
  "workflow": {
    "name": "development-pipeline",
    "description": "Pipeline completa de desenvolvimento: análise, planejamento, codificação, testes e deploy",
    "executors": [
      {
        "type": "agent",
        "name": "analyser",
        "agent_name": "architect_analyser",
        "instructions": "Você é um analista de código especializado. Analise o código fornecido, identifique problemas, oportunidades de melhoria, padrões de código e possíveis refatorações. Forneça uma análise detalhada e estruturada.",
        "tools": ["code_interpreter"]
      },
      {
        "type": "agent",
        "name": "planner",
        "agent_name": "architect_planner",
        "instructions": "Você é um planejador de desenvolvimento. Com base na análise fornecida, crie um plano detalhado de ação. Liste as tarefas necessárias, priorize-as e forneça instruções claras para a implementação. Seja específico sobre o que precisa ser feito.",
        "tools": []
      },
      {
        "type": "agent",
        "name": "coder",
        "agent_name": "architect_coder",
        "instructions": "Você é um desenvolvedor experiente. Implemente as mudanças conforme o plano fornecido. Escreva código limpo, bem estruturado e seguindo as melhores práticas. Use as ferramentas disponíveis para executar comandos git e manipular arquivos quando necessário.",
        "tools": ["code_interpreter", "execute_command"]
      },
      {
        "type": "agent",
        "name": "tester",
        "agent_name": "architect_tester",
        "instructions": "Você é um especialista em testes. Valide o código implementado, execute testes quando possível e verifique se as mudanças estão funcionando corretamente. Forneça feedback sobre a qualidade do código e sugestões de melhorias.",
        "tools": ["code_interpreter", "execute_command"]
      },
      {
        "type": "agent",
        "name": "pusher",
        "agent_name": "architect_pusher",
        "instructions": "Você é responsável por fazer commit e push das mudanças. Verifique o status do git, faça commit das mudanças com mensagens claras e descritivas, e faça push para o repositório remoto. Sempre trabalhe na branch main e nunca force push. Certifique-se de que o working tree está limpo antes de fazer push.",
        "tools": ["execute_command"]
      },
      {
        "type": "agent",
        "name": "puller",
        "agent_name": "architect_puller",
        "instructions": "Você é responsável por verificar o status final do repositório. Confirme que todas as mudanças foram aplicadas corretamente, que o repositório está sincronizado e que não há pendências. Forneça um resumo final do que foi realizado.",
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
  "input_message": "Refatore o ClimateAgent para melhorar a estrutura interna preservando o comportamento. Depois, delete o arquivo README.md e faça commit e push de todas as mudanças para o repositório https://github.com/mediote/architect na branch main.",
  "streaming": false
}
```

### Fluxo do Workflow

1. **Analyser**: Analisa o código atual e identifica oportunidades de melhoria
2. **Planner**: Cria um plano detalhado de ação baseado na análise
3. **Coder**: Implementa as mudanças conforme o plano
4. **Tester**: Valida e testa as mudanças implementadas
5. **Pusher**: Faz commit e push das mudanças para o repositório
6. **Puller**: Verifica o status final e fornece resumo

### Exemplo de Uso com cURL

```bash
curl -X POST http://localhost:8000/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {
      "name": "development-pipeline",
      "description": "Pipeline completa de desenvolvimento",
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
          "instructions": "Você é um desenvolvedor experiente. Implemente as mudanças conforme o plano fornecido. **CRÍTICO**: Após criar a branch e fazer commits, faça push da branch para o remoto usando 'git push -u origin <branch-name>' para que os estágios downstream possam acessá-la.",
          "tools": ["code_interpreter", "execute_command"]
        },
        {
          "type": "agent",
          "name": "tester",
          "agent_name": "architect_tester",
          "instructions": "Você é um especialista em testes. Valide o código implementado e forneça feedback.",
          "tools": ["code_interpreter", "execute_command"]
        },
        {
          "type": "agent",
          "name": "pusher",
          "agent_name": "architect_pusher",
          "instructions": "Você é responsável por fazer commit e push das mudanças. Faça commit com mensagens claras e faça push para o repositório remoto.",
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

### Resposta Esperada

```json
{
  "output": "✅ **Task Completed Successfully**\n\nThe repository **https://github.com/mediote/architect** has been updated as requested. All steps were executed on the `main` branch in a clean and reproducible manner.\n\n### ✅ Actions Performed\n- **Refactored the ClimateAgent** to improve internal structure while preserving behavior.\n- **Deleted the `README.md` file** from the repository.\n- **Committed all changes directly to the `main` branch** with a clear commit message.\n- **Pushed the commit to the remote repository** without force-pushing.\n\n### ✅ Repository Status\n- Working tree is clean.\n- Local `main` branch is fully synchronized with `origin/main`.\n- No uncommitted or unpushed changes remain.\n\nIf you need further refactoring, additional features, or a follow-up task, feel free to proceed.",
  "trace_id": "e3c04aed08b87df0caeca2eafbf1dc18",
  "execution_steps": [
    {
      "step": "executor_created",
      "executor": "analyser",
      "type": "agent"
    },
    {
      "step": "executor_created",
      "executor": "planner",
      "type": "agent"
    },
    {
      "step": "executor_created",
      "executor": "coder",
      "type": "agent"
    },
    {
      "step": "executor_created",
      "executor": "tester",
      "type": "agent"
    },
    {
      "step": "executor_created",
      "executor": "pusher",
      "type": "agent"
    },
    {
      "step": "executor_created",
      "executor": "puller",
      "type": "agent"
    },
    {
      "step": "edge_added",
      "from": "analyser",
      "to": "planner",
      "type": "direct"
    },
    {
      "step": "edge_added",
      "from": "planner",
      "to": "coder",
      "type": "direct"
    },
    {
      "step": "edge_added",
      "from": "coder",
      "to": "tester",
      "type": "direct"
    },
    {
      "step": "edge_added",
      "from": "tester",
      "to": "pusher",
      "type": "direct"
    },
    {
      "step": "edge_added",
      "from": "pusher",
      "to": "puller",
      "type": "direct"
    },
    {
      "step": "workflow_built",
      "status": "success"
    },
    {
      "step": "workflow_execution_started"
    },
    {
      "step": "workflow_execution_completed",
      "status": "success",
      "output_length": 450
    }
  ],
  "workflow_id": "development-pipeline"
}
```

### Variações do Workflow

#### Workflow Simplificado (Sem Testes)

Para workflows mais rápidos, você pode pular a etapa de testes:

```json
{
  "workflow": {
    "name": "development-pipeline-simple",
    "executors": [
      {
        "type": "agent",
        "name": "analyser",
        "instructions": "Analise o código e identifique melhorias.",
        "tools": ["code_interpreter"]
      },
      {
        "type": "agent",
        "name": "coder",
        "instructions": "Implemente as mudanças necessárias.",
        "tools": ["code_interpreter", "execute_command"]
      },
      {
        "type": "agent",
        "name": "pusher",
        "instructions": "Faça commit e push das mudanças.",
        "tools": ["execute_command"]
      }
    ],
    "edges": [
      {
        "from_executor": "analyser",
        "to_executor": "coder",
        "edge_type": "direct"
      },
      {
        "from_executor": "coder",
        "to_executor": "pusher",
        "edge_type": "direct"
      }
    ],
    "start_executor": "analyser"
  },
  "input_message": "Sua tarefa aqui..."
}
```

#### Workflow com Validação Condicional

Você pode adicionar um executor de validação que decide se deve prosseguir ou não:

```json
{
  "executors": [
    // ... outros executores ...
    {
      "type": "agent",
      "name": "validator",
      "instructions": "Valide se as mudanças estão prontas para commit. Se houver problemas críticos, indique que não deve prosseguir.",
      "tools": ["code_interpreter"]
    }
  ],
  "edges": [
    {
      "from_executor": "tester",
      "to_executor": "validator",
      "edge_type": "direct"
    },
    {
      "from_executor": "validator",
      "to_executor": "pusher",
      "edge_type": "conditional",
      "condition": {
        "field": "status",
        "operator": "equals",
        "value": "ready"
      }
    }
  ]
}
```

```json
{
  "workflow": {
    "name": "conditional-workflow",
    "description": "Workflow com roteamento condicional",
    "executors": [
      {
        "type": "agent",
        "name": "classifier",
        "agent_name": "message-classifier",
        "instructions": "Classifique a mensagem como 'urgente' ou 'normal'."
      },
      {
        "type": "agent",
        "name": "urgent_handler",
        "agent_name": "urgent-processor",
        "instructions": "Processe mensagens urgentes com prioridade."
      },
      {
        "type": "agent",
        "name": "normal_handler",
        "agent_name": "normal-processor",
        "instructions": "Processe mensagens normais."
      }
    ],
    "edges": [
      {
        "from_executor": "classifier",
        "to_executor": "urgent_handler",
        "edge_type": "conditional",
        "condition": {
          "field": "classification",
          "operator": "equals",
          "value": "urgent"
        }
      },
      {
        "from_executor": "classifier",
        "to_executor": "normal_handler",
        "edge_type": "conditional",
        "condition": {
          "field": "classification",
          "operator": "equals",
          "value": "normal"
        }
      }
    ],
    "start_executor": "classifier",
    "workflow_type": "conditional"
  },
  "input_message": "Esta é uma mensagem urgente que precisa de atenção imediata",
  "streaming": false
}
```

## Tipos de Executores

### Agent Executor

```json
{
  "type": "agent",
  "name": "my_agent",
  "agent_name": "custom-agent-name",
  "agent_id": "agent-id",
  "instructions": "Instruções para o agente",
  "tools": ["code_interpreter", "execute_command"]
}
```

**Campos:**
- `type`: Sempre `"agent"`
- `name`: Nome único do executor no workflow
- `agent_name`: Nome do agente (opcional, usa `name` se não fornecido)
- `agent_id`: ID do agente (opcional, usa `name` se não fornecido)
- `instructions`: Instruções para o agente
- `tools`: Lista de ferramentas habilitadas (opcional, todas habilitadas se não fornecido)

### Function Executor

```json
{
  "type": "function",
  "name": "my_function",
  "function_name": "execute_command",
  "parameters": {
    "working_directory": ".",
    "command": "ls -la"
  }
}
```

**Campos:**
- `type`: Sempre `"function"`
- `name`: Nome único do executor no workflow
- `function_name`: Nome da função a executar (ex: `"execute_command"`)
- `parameters`: Parâmetros para a função

**Funções Disponíveis:**
- `execute_command`: Executa comandos CLI

## Tipos de Edges

### Direct Edge

Conexão direta entre dois executores.

```json
{
  "from_executor": "executor1",
  "to_executor": "executor2",
  "edge_type": "direct"
}
```

### Conditional Edge

Roteamento baseado em condições (suporte futuro).

```json
{
  "from_executor": "classifier",
  "to_executor": "handler",
  "edge_type": "conditional",
  "condition": {
    "field": "status",
    "operator": "equals",
    "value": "success"
  }
}
```

**Operadores disponíveis:**
- `equals`: Igualdade exata
- `contains`: Contém substring
- `starts_with`: Começa com
- `ends_with`: Termina com
- `greater_than`: Maior que (numérico)
- `less_than`: Menor que (numérico)

## Tipos de Workflow

- `sequential`: Execução sequencial (padrão)
- `parallel`: Execução paralela (fan-out/fan-in)
- `conditional`: Roteamento condicional
- `dynamic`: Workflow que se adapta dinamicamente

## Resposta da API

```json
{
  "output": "Resultado final do workflow",
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
      "step": "workflow_execution_started"
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

## Streaming

Para receber eventos em tempo real durante a execução:

```json
{
  "workflow": { ... },
  "input_message": "...",
  "streaming": true
}
```

Quando `streaming: true`, os eventos são retornados incrementalmente.

## Notas

- Todos os executores devem ter nomes únicos dentro do workflow
- O `start_executor` deve existir na lista de executores
- As edges devem referenciar executores existentes
- Agentes podem compartilhar ferramentas ou ter ferramentas específicas
- Workflows são construídos dinamicamente a cada requisição
