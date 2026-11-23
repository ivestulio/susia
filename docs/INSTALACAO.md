# Instalação passo a passo (Mac e Windows)

Este guia começa do zero: um computador sem Python, sem Git e sem o projeto. Siga os passos na ordem. Cada passo tem uma parte para **Mac** e outra para **Windows**; faça só a do seu sistema.

Ao final você terá rodado o grafo no terminal e no LangGraph Studio.

## O que você vai precisar

- Conexão com a internet.
- Os dados de acesso ao modelo no Microsoft Foundry: **endpoint**, **chave** e **nomes dos deployments** de chat e de embeddings. Eles são fornecidos pelo professor ou vêm do seu próprio recurso no Foundry.
- Para o Studio: uma conta gratuita no [LangSmith](https://smith.langchain.com).

Você **não** precisa instalar o Python à parte: o `uv` (passo 3) baixa a versão certa sozinho.

---

## Passo 1: abrir o terminal

Todos os comandos deste guia são digitados no terminal.

**Mac**: abra o app **Terminal** (Cmd + Espaço, digite `Terminal`, Enter).

**Windows**: abra o **PowerShell** (tecla Windows, digite `PowerShell`, Enter). Não use o "Prompt de Comando" (cmd): os comandos deste guia são para o PowerShell.

> Copie e cole um comando por vez e espere ele terminar antes do próximo.

## Passo 2: instalar o Git

O Git baixa o projeto do GitHub.

**Mac**:

```bash
xcode-select --install
```

Uma janela vai pedir para instalar as "ferramentas de linha de comando". Clique em **Instalar** e espere. Se aparecer a mensagem `command line tools are already installed`, o Git já está instalado.

**Windows**:

```powershell
winget install --id Git.Git -e
```

Se o `winget` não existir no seu Windows, baixe o instalador em [git-scm.com/download/win](https://git-scm.com/download/win) e clique em "Next" até o fim.

**Feche o terminal e abra de novo** depois de instalar. Confira:

```bash
git --version
```

Deve aparecer algo como `git version 2.x`.

## Passo 3: instalar o uv

O [uv](https://docs.astral.sh/uv/) instala o Python e as bibliotecas do projeto.

**Mac**:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows**:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Feche o terminal e abra de novo.** Confira:

```bash
uv --version
```

Deve aparecer algo como `uv 0.x`.

## Passo 4: baixar o projeto

Escolha uma pasta para guardar o projeto (por exemplo, a pasta Documentos) e baixe o repositório.

**Mac**:

```bash
cd ~/Documents
```

**Windows**:

```powershell
cd $HOME\Documents
```

**Mac e Windows**:

```bash
git clone https://github.com/ivestulio/susia.git
```

```bash
cd susia
```

A partir daqui, **todos os comandos devem ser rodados dentro da pasta `susia`**. Se fechar o terminal, volte para ela com `cd ~/Documents/susia` (Mac) ou `cd $HOME\Documents\susia` (Windows).

## Passo 5: criar o ambiente virtual

O ambiente virtual é uma pasta `.venv` dentro do projeto, com um Python 3.12 só dele. Se você não tiver o Python 3.12, o `uv` baixa.

**Mac e Windows**:

```bash
uv venv --python 3.12
```

Deve aparecer `Creating virtual environment at: .venv`.

## Passo 6: instalar as dependências

**Mac e Windows**:

```bash
uv pip install -r requirements.txt
```

Leva alguns segundos e termina com uma lista de pacotes instalados (`+ langgraph==...` etc.).

> Não precisa "ativar" o ambiente virtual. Nos próximos passos chamamos o Python de dentro da `.venv` direto, o que evita o erro de permissão de scripts do PowerShell no Windows.

## Passo 7: configurar o arquivo `.env`

O `.env` guarda o endereço e a chave do modelo. Ele fica só no seu computador e nunca vai para o GitHub.

Crie o arquivo a partir do modelo:

**Mac**:

```bash
cp .env.example .env
```

```bash
open -e .env
```

**Windows**:

```powershell
Copy-Item .env.example .env
```

```powershell
notepad .env
```

O arquivo abre no editor de texto. Preencha estas quatro linhas, sem aspas e sem espaços em volta do `=`:

```
AZURE_OPENAI_ENDPOINT=https://<recurso>.services.ai.azure.com/openai/v1/
AZURE_OPENAI_API_KEY=<sua chave>
AZURE_OPENAI_CHAT_DEPLOYMENT=<nome do deployment de chat>
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=<nome do deployment de embeddings>
```

Cuidados:

- O endpoint termina em `/openai/v1/`. Não acrescente `/responses` nem `/chat/completions`.
- Use o **nome do deployment** como está no Foundry, que nem sempre é igual ao nome do modelo.
- As outras linhas (OpenAI, Gemini, Azure AI Search, MLflow) podem ficar em branco.

Salve e feche o editor.

## Passo 8: rodar o projeto no terminal

**Mac**:

```bash
.venv/bin/python exemplo.py
```

**Windows**:

```powershell
.venv\Scripts\python exemplo.py
```

A primeira execução demora mais: o projeto lê o `CID-10.pdf`, gera os embeddings e salva o índice em `.cache/` (pode levar alguns minutos). Nas próximas execuções o índice é só lido do disco, e cada prontuário leva cerca de 30 segundos.

Resultado esperado (o texto exato varia):

```
Urgencia:      urgente
Especialidade: cardiologia
Justificativa: Dor torácica típica com irradiação e sudorese ...

  R07 - Dor de garganta e no peito  (Dor torácica ...)
  I95 - Hipotensão  (Hipotensão (PA 90x60 mmHg))

parecer_cardiologico:
  hipotese_diagnostica: Síndrome coronariana aguda ...
  risco: alto

Aprovar o parecer? (s/n):
```

O fluxo pausa e pede a **aprovação humana** do parecer. Digite `s` e Enter para aprovar, ou `n` e Enter para rejeitar; na rejeição, o script pede o motivo. No fim aparece `Parecer aprovado.` ou `Parecer rejeitado: <motivo>`.

Para testar outro prontuário, passe o texto entre aspas:

**Mac**:

```bash
.venv/bin/python exemplo.py "Mulher, 34 anos. Renovacao de receita de anticoncepcional. Sem queixas."
```

**Windows**:

```powershell
.venv\Scripts\python exemplo.py "Mulher, 34 anos. Renovacao de receita de anticoncepcional. Sem queixas."
```

## Passo 9: rodar no LangGraph Studio

O Studio mostra o grafo e cada etapa da execução no navegador.

**Mac**:

```bash
.venv/bin/langgraph dev
```

**Windows**:

```powershell
.venv\Scripts\langgraph dev
```

O comando sobe um servidor local em `http://127.0.0.1:2024` e abre o Studio no navegador. Faça login no LangSmith se for pedido.

No Studio:

1. Selecione o grafo **atendimento**.
2. Preencha a entrada, por exemplo:

   ```json
   {
     "paciente_id": "PAC-004",
     "prontuario": "Mulher, 34 anos. Retorno para renovação de receita de anticoncepcional oral. Sem queixas. PA 110x70 mmHg, FC 72 bpm, afebril.",
     "data_atualizacao": "2026-11-15"
   }
   ```

3. Clique em **Submit**.
4. A execução pausa no nó **aprovacao_humana** e o Studio mostra o parecer para revisão. Responda o interrupt com um destes JSON e clique em **Resume** (ou **Continue**, conforme a versão do Studio):

   ```json
   {"aprovado": true}
   ```

   ```json
   {"aprovado": false, "motivo": "Falta exame de controle"}
   ```

   Se a resposta vier sem `aprovado`, ou for uma rejeição sem motivo, a execução pausa de novo explicando o erro.

O terminal fica ocupado enquanto o servidor roda. Para parar, volte ao terminal e aperte **Ctrl + C**.

---

## Problemas comuns

| Mensagem ou sintoma | Causa | Solução |
|---|---|---|
| `git`, `uv` ou `winget` "não é reconhecido" / `command not found` | O terminal foi aberto antes da instalação | Feche e abra o terminal. No Windows, se continuar, reinicie o computador |
| `No such file or directory: requirements.txt` ou `can't open file 'exemplo.py'` | O terminal não está na pasta do projeto | `cd ~/Documents/susia` (Mac) ou `cd $HOME\Documents\susia` (Windows) |
| `ModuleNotFoundError: No module named 'src'` | Comando rodado fora da pasta do projeto | Mesmo caso acima: rode de dentro da pasta `susia` |
| `ModuleNotFoundError: No module named 'langgraph'` (ou outro pacote) | Dependências não instaladas, ou foi usado o Python do sistema | Refaça o passo 6 e rode com `.venv/bin/python` (Mac) ou `.venv\Scripts\python` (Windows), não só `python` |
| `ValidationError ... azure_openai_endpoint Field required` | O `.env` não existe ou está vazio | Refaça o passo 7. Confira que o arquivo se chama `.env` e está na pasta `susia` |
| No Windows, o arquivo virou `.env.txt` | O Bloco de Notas acrescentou `.txt` ao salvar | `Rename-Item .env.txt .env` |
| `401` / `Access denied` / `invalid subscription key` | Chave errada | Confira `AZURE_OPENAI_API_KEY` no `.env` (sem aspas nem espaços) |
| `404 Resource not found` / `DeploymentNotFound` | Endpoint ou nome do deployment errado | O endpoint termina em `/openai/v1/`; o deployment é o nome que aparece no Foundry |
| `429` / `RateLimitError` | Limite de requisições do deployment, comum na primeira execução, que gera os embeddings | Espere um minuto e rode de novo. O índice só é salvo quando termina; se der erro no meio, ele recomeça na próxima execução |
| A primeira execução "trava" por minutos | O índice do CID-10 está sendo gerado | Normal; espere. Só acontece uma vez (fica em `.cache/`) |
| `running scripts is disabled on this system` (Windows) | Tentou ativar a `.venv` com `Activate.ps1` | Não é preciso ativar: use `.venv\Scripts\python` e `.venv\Scripts\langgraph` como no guia |
| O Studio não carrega no **Safari** | O Safari bloqueia a conexão da página do Studio com o servidor local (`http://127.0.0.1`) | Use Chrome, Edge ou Firefox, ou rode `langgraph dev --tunnel` |
| `Address already in use` / porta 2024 ocupada | Outro `langgraph dev` ainda está rodando | Feche o outro terminal ou aperte Ctrl + C nele; ou use `langgraph dev --port 2025` |
| O Studio parou em `aprovacao_humana` e não termina | É a pausa da aprovação humana, não um erro | Responda o interrupt com `{"aprovado": true}` e clique em Resume (passo 9) |
| Aviso `Deserializing unregistered type src.state...` no terminal do `langgraph dev` | Aviso do LangGraph ao retomar a execução pausada | Pode ignorar: não afeta o resultado |
| `uv venv` diz que a `.venv` já existe | Você já criou o ambiente antes | Tudo bem, siga para o passo 6. Para recomeçar do zero, apague a pasta `.venv` e refaça o passo 5 |

Se o erro não estiver na tabela, copie a **última linha** da mensagem (geralmente começa com o nome do erro, como `ValueError:` ou `OpenAIError:`) e envie junto com o comando que você rodou.

## Atualizar o projeto depois

Quando houver mudanças no repositório:

```bash
git pull
```

```bash
uv pip install -r requirements.txt
```
