# Dados Estruturados em Workflows

## Situação Atual

**❌ Atualmente, os agentes NÃO retornam dados estruturados tipados.**

Os agentes estão configurados para retornar apenas **texto (string)**, mesmo quando as instruções pedem JSON estruturado. Isso significa:

1. **Os agentes retornam JSON como texto**: As instruções pedem JSON, mas ele é retornado como uma string
2. **Parsing manual necessário**: Os agentes downstream precisam fazer parsing manual do JSON do texto
3. **Sem validação de tipos**: Não há validação automática de estrutura
4. **Sem type safety**: O framework não garante que os dados estão no formato correto

### Exemplo Atual

```python
# AgentExecutor atual
@handler
async def handle(self, message: str, ctx: WorkflowContext[str]) -> None:
    result = await agent.run(message)
    response_text = result.text  # ← Apenas texto
    await ctx.send_message(response_text)  # ← Envia como string
```

O agente pode retornar:
```
"{\"project_context\": {\"repository_url\": \"...\", ...}}"
```

Mas isso é tratado como uma **string**, não como um objeto estruturado.

## Como Melhorar: Dados Estruturados Tipados

Para suportar dados estruturados, precisamos:

### 1. Modelos Pydantic (Já Criados)

Criei modelos em `src/models/workflow_data.py`:
- `ProjectContext`
- `AnalysisSummary`
- `ArchitecturePlan`
- `RefactorResult`
- `TestReport`
- `PullRequestMetadata`
- `WorkflowData` (container)

### 2. Usar Structured Output do Agent Framework

O Microsoft Agent Framework suporta **structured output** usando modelos Pydantic:

```python
from src.models.workflow_data import ProjectContext

# Criar agente com structured output
agent = client.create_agent(
    name="puller",
    instructions="...",
    response_format=ProjectContext  # ← Especifica o formato de saída
)

# O agente retornará um objeto ProjectContext, não texto
result = await agent.run(message)
project_context: ProjectContext = result.data  # ← Objeto tipado
```

### 3. Atualizar WorkflowContext para Tipos Estruturados

```python
# Antes (texto)
@handler
async def handle(self, message: str, ctx: WorkflowContext[str]) -> None:
    await ctx.send_message(text)

# Depois (estruturado)
@handler
async def handle(self, message: str, ctx: WorkflowContext[WorkflowData]) -> None:
    workflow_data = WorkflowData(project_context=project_context, ...)
    await ctx.send_message(workflow_data)  # ← Objeto tipado
```

### 4. Benefícios

✅ **Type Safety**: Validação automática de tipos
✅ **Parsing Automático**: Não precisa fazer parsing manual
✅ **IntelliSense**: Autocomplete em IDEs
✅ **Validação**: Pydantic valida automaticamente
✅ **Documentação**: Schemas servem como documentação

## Implementação Recomendada

### Opção 1: Manter Texto (Atual - Mais Simples)

**Vantagens:**
- ✅ Funciona imediatamente
- ✅ Flexível (agentes podem retornar qualquer formato)
- ✅ Fácil de debugar (texto legível)

**Desvantagens:**
- ❌ Sem validação de tipos
- ❌ Parsing manual necessário
- ❌ Erros de formato só aparecem em runtime

### Opção 2: Dados Estruturados Tipados (Recomendado)

**Vantagens:**
- ✅ Type safety
- ✅ Validação automática
- ✅ Melhor experiência de desenvolvimento
- ✅ Menos erros

**Desvantagens:**
- ⚠️ Requer mudanças no código
- ⚠️ Agentes precisam retornar exatamente o formato esperado
- ⚠️ Menos flexível

## Como Implementar Dados Estruturados

### Passo 1: Atualizar AgentExecutor

```python
from src.models.workflow_data import WorkflowData

class AgentExecutor(Executor):
    def __init__(self, ..., response_format: Optional[Type[BaseModel]] = None):
        self.response_format = response_format
    
    @handler
    async def handle(self, message: str, ctx: WorkflowContext[WorkflowData]) -> None:
        agent = self._get_agent()
        
        # Se response_format especificado, usar structured output
        if self.response_format:
            result = await agent.run(message, response_format=self.response_format)
            structured_data = result.data
        else:
            result = await agent.run(message)
            # Tentar fazer parsing do JSON do texto
            structured_data = self._parse_text_to_structured(result.text)
        
        await ctx.send_message(structured_data)
```

### Passo 2: Configurar Response Format nos Schemas

```python
class AgentExecutorConfig(BaseModel):
    # ... campos existentes ...
    response_format: Optional[str] = Field(
        default=None,
        description="Response format: 'ProjectContext', 'AnalysisSummary', etc."
    )
```

### Passo 3: Atualizar Instruções dos Agentes

As instruções já pedem JSON estruturado, mas podemos melhorar:

```
OUTPUT (MANDATORY): Return a JSON object matching this schema:
{
  "repository_url": string,
  "local_path": string,
  "default_branch": string,
  "current_commit": string
}
```

## Recomendação

Para o workflow `project-atlas-pipeline`, recomendo:

1. **Manter texto por enquanto** (funciona)
2. **Melhorar as instruções** para garantir JSON válido
3. **Adicionar parsing opcional** no AgentExecutor para tentar extrair JSON do texto
4. **Migrar gradualmente** para structured output quando necessário

## Exemplo de Parsing de JSON do Texto

```python
import json
import re

def extract_json_from_text(text: str) -> Optional[Dict]:
    """Try to extract JSON from text."""
    # Try to find JSON blocks
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None
```

Isso permite que os agentes retornem texto com JSON embutido, e o sistema tenta extrair e validar automaticamente.
