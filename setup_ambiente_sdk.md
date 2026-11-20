# Configuração do ambiente do SDK (openai-agents com Groq)

Este documento descreve o passo a passo para preparar o ambiente de desenvolvimento do agente de análise de churn da NeoStream, seguindo a regra de segurança de que a chave de API nunca pode aparecer versionada no repositório Git.

## 0. Decisão de provedor: Groq em vez de OpenAI

O enunciado cita uma chave da OpenAI, mas neste projeto o provedor de modelos é a **Groq**. O pacote `openai-agents` continua sendo o SDK usado, pois a Groq oferece uma API compatível com a da OpenAI. Basta apontar o cliente do SDK para o endereço da Groq (`https://api.groq.com/openai/v1`) e usar a chave da Groq. O restante do projeto (`Agent`, `Runner`, saída estruturada e execução assíncrona) permanece igual.

## 1. Criar e ativar o ambiente virtual

```bash
python -m venv .venv
```

Ativação:

| Sistema | Comando |
|---|---|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| macOS / Linux | `source .venv/bin/activate` |

O SDK exige Python 3.10 ou superior (`python --version`).

## 2. Proteger a chave antes de criá-la: `.gitignore`

Antes de criar o arquivo `.env`, crie o `.gitignore` na raiz do projeto com o conteúdo abaixo e faça o commit dele. Assim o Git ignora o `.env` desde o início.

```
.env
.venv/
__pycache__/
```

## 3. Instalar o SDK e o python-dotenv

Com o ambiente virtual ativo:

```bash
pip install openai-agents python-dotenv
```

- `openai-agents`: SDK com os primitivos `Agent` e `Runner`. Ele já instala o pacote `openai`, que fornece o cliente `AsyncOpenAI`.
- `python-dotenv`: carrega as variáveis do arquivo `.env` para o ambiente do processo.

## 4. Registrar a versão instalada em `requirements.txt`

Para registrar exatamente as versões que ficaram instaladas na sua máquina:

```bash
pip freeze
```

Copie para o `requirements.txt` as linhas de `openai-agents` e `python-dotenv`, que são as dependências diretas do projeto. Exemplo do formato (as versões devem ser as da sua instalação):

```
openai-agents==0.25.0
python-dotenv==1.2.4
```

Em um novo ambiente, as mesmas versões são restauradas com `pip install -r requirements.txt`.

## 5. Obter a chave da Groq

1. Acesse `https://console.groq.com/keys` e entre com a sua conta.
2. Crie uma chave de API (**Create API Key**) e copie o valor, que só é exibido uma vez.

## 6. Configurar a chave via `.env` e python-dotenv

1. O arquivo `.env.example` é versionado e contém só os nomes das variáveis, sem valores reais:

   ```
   GROQ_API_KEY=
   GROQ_MODEL=openai/gpt-oss-120b
   ```

2. Crie o seu `.env` a partir dele (copie o arquivo e renomeie para `.env`) e preencha `GROQ_API_KEY` com a chave real. O `.env` fica só na sua máquina e é ignorado pelo Git.
3. Nos scripts, a chave é lida do ambiente depois de `load_dotenv()`, sem nenhum valor escrito no código:

   ```python
   load_dotenv()
   chave = os.environ.get("GROQ_API_KEY", "")
   ```

O nome do modelo fica em `GROQ_MODEL` para poder ser trocado sem editar o código. O valor sugerido, `openai/gpt-oss-120b`, consta entre os modelos de produção da Groq. A lista atual está em `https://console.groq.com/docs/models`.

## 7. Verificar o ambiente: `verificar_ambiente.py`

```bash
python verificar_ambiente.py
```

O script:

1. carrega o `.env` com `load_dotenv()`;
2. mostra as versões instaladas de `openai-agents` e `python-dotenv`;
3. confirma que `GROQ_API_KEY` e `GROQ_MODEL` estão definidas, informando apenas que a chave existe e quantos caracteres tem, **sem imprimir o valor**;
4. cria o cliente `AsyncOpenAI` do SDK apontando para a Groq e confirma que ele recebeu a chave lida do ambiente;
5. instancia o `OpenAIChatCompletionsModel` com esse cliente, que é o objeto usado para ligar um `Agent` à Groq nos exercícios seguintes.

Saída esperada (a quantidade de caracteres varia conforme a chave):

```
openai-agents: 0.25.0
python-dotenv: 1.2.4
GROQ_API_KEY: definida (56 caracteres, valor oculto)
GROQ_MODEL: openai/gpt-oss-120b
Cliente do SDK configurado para https://api.groq.com/openai/v1/ com a chave lida do ambiente.
Ambiente verificado com sucesso.
```

Se uma variável estiver ausente ou vazia, o script mostra uma mensagem de erro e encerra com código 1. O script não faz chamada de rede: ele valida a leitura da variável e a configuração do SDK, mas não testa se a chave é aceita pela Groq. Essa confirmação acontece na primeira execução de um agente (Exercício 4).

## 8. Boas práticas de segurança aplicadas

- **Nenhum hardcode:** a chave não aparece em nenhum `.py` nem `.md`.
- **`.env` fora do Git:** listado no `.gitignore`. Para conferir antes de cada commit, `git status` não deve listar o `.env`, e `git ls-files .env` deve voltar vazio.
- **`.env.example` sem valores reais:** documenta quais variáveis o projeto precisa sem expor segredo.
- **Saída sem a chave:** o script de verificação nunca imprime o valor da variável.
- **Se a chave vazar** (por exemplo, em um commit ou em um print): revogue-a imediatamente em `https://console.groq.com/keys` e gere outra. Apagar o commit depois não basta, porque o histórico do Git guarda o conteúdo.

## 9. Rastreamento (tracing) do SDK

Por padrão, o `openai-agents` tenta enviar rastros de execução para a plataforma da OpenAI, o que exigiria uma chave da OpenAI e emitiria avisos ao usar a Groq. Nos scripts de agente dos exercícios seguintes, esse envio é desativado com `set_tracing_disabled(True)`.

## 10. Problemas comuns

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `GROQ_API_KEY não está definida` | `.env` não existe, está fora da pasta do script ou a chave está vazia | Crie o `.env` na pasta do projeto e preencha a chave |
| `ModuleNotFoundError: agents` | Ambiente virtual não ativado ou pacote não instalado | Ative o `.venv` e rode `pip install -r requirements.txt` |
| Erro `401` ao rodar um agente | Chave incorreta ou revogada | Gere outra chave no console da Groq |
| Erro de modelo descontinuado | O modelo em `GROQ_MODEL` saiu do catálogo | Consulte `https://console.groq.com/docs/models` e atualize o `.env` |
| Erro `404` ao rodar o agente | O modelo escolhido originalmente `llama-3.3-70b-versatile` está desativado para contas gratuitas | Consulte `https://console.groq.com/docs/models` e atualize o `.env` |
