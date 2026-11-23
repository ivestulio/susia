# susia

Sistema multiagente, construído com [LangGraph](https://langchain-ai.github.io/langgraph/), que recebe um prontuário médico e faz a triagem do atendimento.

> Projeto didático. Use apenas prontuários fictícios: ele não substitui avaliação clínica e não deve ser usado com dados reais de pacientes.

## Como funciona

O objetivo final é encaminhar cada prontuário para o agente certo:

- **cardiológico** → agente cardiologista
- **neurológico** → agente neurologista
- **urgente** → agente de emergência
- **não urgente** → agente clínico geral

### Etapa atual

```mermaid
graph LR
    START([START]) --> guardrail_entrada
    guardrail_entrada -. bloqueado .-> FIM([END])
    guardrail_entrada -. liberado .-> atendimento
    atendimento -. cardiologico .-> agente_cardiologista
    atendimento -. neurologico .-> agente_neurologista
    atendimento -. urgente .-> agente_urgencia
    atendimento -. nao_urgente .-> agente_clinicogeral
    agente_cardiologista --> aprovacao_humana
    agente_neurologista --> aprovacao_humana
    agente_urgencia --> aprovacao_humana
    agente_clinicogeral --> aprovacao_humana
    aprovacao_humana --> FIM
```

- **`guardrail_entrada`**: primeira etapa, antes de qualquer chamada ao modelo. Mascara segredos e dados pessoais e bloqueia tentativas de injeção de prompt (detalhes em [Guardrail de entrada](#guardrail-de-entrada)).
- **`atendimento`**: lê o prontuário e pede ao modelo uma resposta estruturada com `urgencia`, `especialidade` (`"cardiologia"`, `"neurologia"` ou `"geral"`) e `justificativa`. Na dúvida, o prompt orienta a classificar como urgente.
- **Roteamento** ([src/edges/roteamento.py](src/edges/roteamento.py)): casos de cardiologia e de neurologia vão para o especialista (`agente_cardiologista` ou `agente_neurologista`), mesmo quando urgentes; os demais urgentes vão para o `agente_urgencia`; os não urgentes vão para o `agente_clinicogeral`.
- **`agente_cardiologista`**: agente com tool calling que separa os sintomas, consulta o CID-10 com `buscar_cid10` e emite um `parecer_cardiologico` com hipótese diagnóstica, risco (`alto`, `moderado` ou `baixo`) e condutas iniciais. Recebe também a classificação de urgência da triagem.
- **`agente_neurologista`**: mesmo padrão do cardiologista, com prompt de neurologia (prioriza códigos G e I60 a I69 e pede termos médicos nas buscas, como "disartria" em vez de "fala arrastada"). Emite um `parecer_neurologico` com hipótese diagnóstica, risco e condutas iniciais.
- **`agente_clinicogeral`**: atende os prontuários não urgentes e sem especialidade. Mesmo padrão do cardiologista (tool calling com `buscar_cid10`), emitindo um `parecer_clinico` com hipótese diagnóstica, orientações, exames e retorno. Se o prontuário não tiver queixas (por exemplo, renovação de receita), não faz buscas e devolve sintomas e CIDs vazios.
- **`agente_urgencia`**: só roda para prontuários urgentes sem especialidade (nem cardiológicos nem neurológicos). É um agente com tool calling: separa os sintomas e sinais do prontuário, consulta o CID-10 com a ferramenta `buscar_cid10` (uma chamada por sintoma) e devolve `sintomas` e `cids_sugeridos`. O prompt proíbe sugerir código que a ferramenta não devolveu.
- **`aprovacao_humana`**: última etapa. Pausa o fluxo até um profissional aprovar ou rejeitar o resultado do agente (detalhes em [Aprovação humana](#aprovação-humana)).

### Guardrail de entrada

O nó `guardrail_entrada` ([src/services/guardrail.py](src/services/guardrail.py)) verifica o prontuário com expressões regulares, sem LLM: é instantâneo, não custa chamadas e não pode ser convencido por uma instrução escrita no próprio prontuário.

| Verificação | O que procura | Ação |
|---|---|---|
| Segredos | Chaves de API (OpenAI, LangSmith, AWS, Google, GitHub, Slack), JWT, chaves privadas, strings de conexão, `senha:` / `api_key=`, sequências longas de letras e dígitos | Substitui por `[SEGREDO]` e segue |
| PII | CPF e CNS (com dígito verificador), CNPJ, RG, e-mail, telefone, CEP, data de nascimento rotulada, nome rotulado (`Paciente: ...`) | Substitui por `[CPF]`, `[NOME]` etc. e segue |
| Injeção de prompt | Pedidos para ignorar instruções, troca de papel ("você agora é"), pedidos do prompt do sistema, marcadores de papel (`<\|im_start\|>`, `### system`), jailbreak e instruções dirigidas aos agentes ("classifique como não urgente", "não use a ferramenta") | Bloqueia: o grafo termina sem chamar o modelo |
| Tamanho | Prontuário vazio ou com mais de 20.000 caracteres | Bloqueia |

- O nó substitui o `prontuario` do state pela versão mascarada; os agentes nunca veem o texto original. Quando bloqueia, o `prontuario` fica vazio.
- O resultado fica em `guardrail`: `bloqueado`, `motivo` e `achados` (tipo, regra e quantidade). O valor encontrado nunca é copiado para o state.
- A injeção é verificada no texto sem acentos e em minúsculas, para que "Desconsidere as instruções" e "desconsidere as instrucoes" sejam tratados igual.

Limitações:

- Nomes só são reconhecidos quando rotulados (`Paciente:`, `Nome:`, `Mãe:`); um nome solto no texto passa.
- Regras fixas não pegam injeções reescritas de outro jeito; uma segunda camada com um classificador (LLM ou modelo dedicado) pode complementar.
- A entrada original ainda aparece no input da execução: no Studio, no checkpoint do servidor e no tracing do LangSmith, se estiver ligado. Para que dados reais nunca saiam da máquina, o mascaramento precisa acontecer antes de chamar o grafo.

### Aprovação humana

O nó `aprovacao_humana` ([src/nodes/aprovacao_humana.py](src/nodes/aprovacao_humana.py)) usa `interrupt()` do LangGraph: a execução para depois do agente e só termina quando um profissional responde.

- **O que o revisor vê**: triagem (`urgencia`, `especialidade`, `justificativa`), `sintomas`, `cids_sugeridos` e o parecer do agente.
- **O que ele responde**: `{"aprovado": true}` para aprovar ou `{"aprovado": false, "motivo": "..."}` para rejeitar. O motivo é obrigatório na rejeição; `"revisor": "nome"` é opcional.
- **Resposta inválida** (sem `aprovado`, ou rejeição sem motivo): o fluxo pausa de novo, com o campo `erro` explicando o problema.
- **Resultado**: a decisão fica em `revisao` no state. Aprovado ou rejeitado, o fluxo termina; o revisor não edita o parecer.
- Prontuários bloqueados pelo guardrail terminam antes e não passam pela aprovação.

A pausa precisa de um checkpointer, que guarda o estado até a resposta chegar:

- **No Studio / `langgraph dev`**: o servidor já tem o seu. Por isso `grafo` em [src/graph.py](src/graph.py) é compilado sem checkpointer.
- **No Python**: compile `builder` com um checkpointer e retome com `Command(resume=...)` na mesma `thread_id`, como faz o [exemplo.py](exemplo.py):

  ```python
  from langgraph.checkpoint.memory import InMemorySaver
  from langgraph.types import Command
  from src.graph import builder

  grafo = builder.compile(checkpointer=InMemorySaver())
  config = {"configurable": {"thread_id": "PAC-001"}}
  resultado = grafo.invoke({...}, config)           # para em aprovacao_humana
  print(resultado["__interrupt__"][0].value)        # o que o revisor vê
  grafo.invoke(Command(resume={"aprovado": True}), config)
  ```

No terminal do `langgraph dev` pode aparecer o aviso `Deserializing unregistered type src.state...` ao retomar. É só um aviso: a versão atual do servidor ainda não permite registrar os tipos do state. No `exemplo.py` os tipos são registrados e o aviso não aparece.

### RAG sobre o CID-10

A base de conhecimento é o arquivo `CID-10.pdf`, na raiz do projeto: a lista de categorias de 3 caracteres do CID-10 (versão 2008 do Ministério da Saúde), no formato `código + descrição`.

- Cada categoria vira um documento (2.045 no total); não há divisão por tamanho de texto.
- Na primeira busca, os embeddings são gerados e o índice é salvo em `.cache/cid10_index.json` (cerca de 80 MB, fora do git). Essa primeira vez pode levar alguns minutos, conforme o limite de requisições do deployment. Nas seguintes, o índice é só lido do disco. Para refazer o índice, apague esse arquivo.
- A busca é por similaridade semântica, com `InMemoryVectorStore`.

Limitação: o PDF traz só o nome de cada categoria, sem descrição de sintomas por doença. A busca casa o sintoma com nomes de categorias, e funciona melhor para os códigos do capítulo R (sintomas e sinais).

## State

Definido em [src/state.py](src/state.py):

| Campo | Origem | Descrição |
|---|---|---|
| `paciente_id` | entrada | ID do paciente |
| `prontuario` | entrada | Texto do prontuário médico |
| `data_atualizacao` | entrada | Data da última atualização do prontuário |
| `guardrail` | guardrail_entrada | `bloqueado`, `motivo` e `achados`; o `prontuario` passa a ser a versão mascarada |
| `urgencia` | atendimento | `"urgente"` ou `"nao_urgente"` |
| `especialidade` | atendimento | `"cardiologia"`, `"neurologia"` ou `"geral"` |
| `justificativa` | atendimento | Motivo da classificação |
| `sintomas` | agente que atendeu o caso | Sintomas e sinais separados do prontuário |
| `cids_sugeridos` | agente que atendeu o caso | Lista de `sintoma`, `codigo` e `descricao` do CID-10 |
| `parecer_cardiologico` | agente_cardiologista | `hipotese_diagnostica`, `risco` e `condutas` |
| `parecer_neurologico` | agente_neurologista | `hipotese_diagnostica`, `risco` e `condutas` |
| `parecer_clinico` | agente_clinicogeral | `hipotese_diagnostica`, `orientacoes`, `exames` e `retorno` |
| `revisao` | aprovacao_humana | `aprovado`, `motivo` (obrigatório na rejeição) e `revisor` |

## Estrutura

```
susia/
├── CID-10.pdf            # base de conhecimento do RAG
├── exemplo.py            # roda o grafo com um prontuário de exemplo
├── langgraph.json        # registra o grafo para o LangGraph Studio
├── requirements.txt
├── .env.example          # modelo das variáveis de ambiente
├── docs/
│   ├── INSTALACAO.md     # passo a passo de instalação (Mac e Windows)
│   └── RAG.md            # como o RAG sobre o CID-10 funciona
└── src/
    ├── state.py          # state compartilhado entre os nós
    ├── graph.py          # montagem do grafo (exporta `grafo`)
    ├── nodes/
    │   ├── guardrail_entrada.py  # verifica segredos, PII e injeção antes da triagem
    │   ├── atendimento.py      # agente de triagem
    │   ├── agente_urgencia.py       # agente que separa sintomas e consulta o CID-10
    │   ├── agente_cardiologista.py  # parecer cardiológico com consulta ao CID-10
    │   ├── agente_neurologista.py   # parecer neurológico com consulta ao CID-10
    │   ├── agente_clinicogeral.py   # parecer de clínica geral com consulta ao CID-10
    │   └── aprovacao_humana.py      # pausa para o profissional aprovar ou rejeitar
    ├── edges/
    │   └── roteamento.py       # arestas condicionais do guardrail e da triagem
    ├── tools/
    │   └── cid10.py            # ferramenta `buscar_cid10`
    └── services/
        ├── llm.py        # clientes do modelo de chat e de embeddings, configurações
        ├── cid10.py      # leitura do PDF, índice vetorial e busca
        └── guardrail.py  # regras do guardrail de entrada
```

`src/services/llm.py` é o único ponto do projeto que conhece o provedor do modelo; os nós só chamam `modelo()`.

## Instalação

> **Primeira vez?** Siga o [passo a passo para Mac e Windows](docs/INSTALACAO.md), que começa do zero (Git, uv, `.env`) e traz uma tabela de erros comuns.

Resumo, para quem já tem o Git e o [uv](https://docs.astral.sh/uv/) (o uv baixa o Python 3.12 se faltar):

```bash
uv venv --python 3.12
```

```bash
uv pip install -r requirements.txt
```

## Configuração

Copie o modelo e preencha os valores:

```bash
cp .env.example .env
```

Os modelos são acessados pela API v1 do Microsoft Foundry. São usadas quatro variáveis:

| Variável | Valor |
|---|---|
| `AZURE_OPENAI_ENDPOINT` | Endpoint v1 do recurso, terminando em `/openai/v1/`. Exemplo: `https://<recurso>.services.ai.azure.com/openai/v1/` |
| `AZURE_OPENAI_API_KEY` | Chave do recurso |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Nome do deployment do modelo de chat no Foundry (nem sempre igual ao nome do modelo) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Nome do deployment de embeddings. Se omitida, vale `text-embedding-3-small` |

Observações:

- O endpoint não deve incluir `/responses` nem `/chat/completions` no final.
- O cliente usa a Responses API, exigida pelos modelos da família gpt-5/codex.
- As demais variáveis do `.env.example` (`AZURE_OPENAI_API_VERSION`, OpenAI, Gemini, Azure AI Search, MLflow) ainda não são usadas pelo código.

## Como rodar

### Pelo Python

O script [exemplo.py](exemplo.py) roda o grafo com um prontuário de dor torácica e imprime a triagem, os CIDs e o parecer. Depois pergunta no terminal `Aprovar o parecer? (s/n)` e, se a resposta for não, pede o motivo (no Windows, use `.venv\Scripts\python`):

```bash
.venv/bin/python exemplo.py
```

Para outro prontuário, passe o texto entre aspas:

```bash
.venv/bin/python exemplo.py "Mulher, 34 anos. Renovacao de receita. Sem queixas."
```

O state final traz `urgencia`, `especialidade` e `justificativa`. Conforme o ramo, vêm também `sintomas` e `cids_sugeridos` e o parecer do agente: `parecer_cardiologico`, `parecer_neurologico` ou `parecer_clinico`. Por último, `revisao` guarda a decisão do revisor.

### Pelo LangGraph Studio

```bash
.venv/bin/langgraph dev
```

O comando sobe a API local em `http://127.0.0.1:2024` e abre o Studio no navegador (pede login em uma conta LangSmith). Selecione o grafo `atendimento`, preencha a entrada e clique em **Submit**.

A execução pausa em `aprovacao_humana` e o Studio mostra o pacote de revisão. Para continuar, responda o interrupt com `{"aprovado": true}` ou `{"aprovado": false, "motivo": "..."}` e clique em **Resume** (ou **Continue**, conforme a versão do Studio).

Exemplo de entrada:

```json
{
  "paciente_id": "PAC-004",
  "prontuario": "Mulher, 34 anos. Retorno para renovação de receita de anticoncepcional oral. Sem queixas. PA 110x70 mmHg, FC 72 bpm, afebril.",
  "data_atualizacao": "2026-11-15"
}
```

## Visualizar o grafo

```bash
.venv/bin/python -c "from src.graph import grafo; print(grafo.get_graph().draw_mermaid())"
```

O comando imprime o diagrama em Mermaid, que pode ser colado em qualquer visualizador Mermaid.
