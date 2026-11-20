# Justificativa de design do agente de análise de churn

## 1. Contexto e requisitos do caso de uso

O time de retenção da NeoStream precisa de um componente que receba uma pergunta em linguagem natural sobre um assinante específico e devolva uma resposta fundamentada, em formato que o painel interno consiga consumir. Os enunciados dos exercícios anteriores estabelecem quatro requisitos, e cada decisão de design deste documento responde a pelo menos um deles:

| # | Requisito do caso de uso | Origem |
|---|---|---|
| R1 | Aceitar perguntas livres e decidir como respondê-las, em vez de devolver apenas 0 ou 1 | Exercícios 1 e 2 |
| R2 | Entregar categoria de risco, recomendação e confiança em formato previsível e validável por código | Exercício 5 |
| R3 | Atender várias solicitações simultâneas sem bloquear o painel | Exercício 6 |
| R4 | Manter a chave de API fora do código e do repositório | Exercício 3 |

## 2. Visão geral da solução

O arquivo `agente_churn_final.py` reúne, em um único script:

- um `Agent` com instruções que definem o papel de analista de risco de churn, usando o modelo `openai/gpt-oss-120b` por meio da API da Groq, compatível com a da OpenAI;
- o modelo Pydantic `RespostaAgente` (`categoria_risco`, `recomendacao`, `confianca`), declarado como `output_type` do agente;
- a execução assíncrona com `Runner.run(...)`, disparada por `asyncio.run(...)` e `asyncio.gather(...)`;
- a validação de cada objeto retornado, em duas camadas, e o tratamento das falhas intermitentes do provedor.

Esta versão não usa ferramentas externas: o agente responde com base nas instruções e nos dados descritos na própria pergunta.

## 3. Decisões de design e justificativas

### 3.1 Uso de `Agent` e `Runner`

**Decisão.** O componente é construído com o primitivo `Agent`, que reúne em um único objeto o papel (instruções), o modelo e o formato de saída, e é executado pelo `Runner`, que conduz a chamada ao modelo e devolve o resultado final.

**Por que é necessária para a NeoStream.**

- **A pergunta não tem formato fixo (R1).** O time pergunta, por exemplo, se um assinante deve entrar na campanha de desconto ou como abordar quem reduziu o uso. Um script como o do TP2 exige um vetor de features em ordem fixa e devolve só um número. Interpretar a intenção da pergunta e decidir o que responder é trabalho de um modelo de linguagem guiado por instruções, que é o que o `Agent` encapsula.
- **O papel e as regras ficam em um só lugar.** As instruções definem o escopo (risco de churn), a referência de negócio (mais reclamações aumentam o risco; mais tempo de casa e mais uso o reduzem), a proibição de inventar dados e o significado de cada campo de saída. Isso torna o comportamento auditável e alterável sem mexer na lógica de execução.
- **O `Runner` é o ponto de extensão para a arquitetura completa.** Ele já conduz o laço de execução do agente, o que permite, em uma próxima etapa, acrescentar ferramentas (como a consulta ao modelo de churn do TP2) sem reescrever a orquestração.
- **Diferença para um chatbot (Exercício 2).** Um chatbot com acesso ao modelo devolveria o número em texto. O agente é instruído a interpretar a evidência e a recomendar uma ação adequada ao perfil.

**O que se observou.** Para o assinante #1187 (62 meses, 15,8 h/semana, sem reclamações), o agente respondeu que ele **não** deve entrar na campanha de desconto, justificando com os três fatores de baixo risco. Essa decisão contextual, de não gastar benefício com quem tem risco baixo, não é obtida de um script de previsão.

### 3.2 Saída estruturada com Pydantic

**Decisão.** O agente é configurado com `output_type=RespostaAgente`, e o SDK exige que a resposta siga o esquema e a converta em um objeto Pydantic.

**Por que é necessária para a NeoStream.**

- **O consumidor é um painel, não uma pessoa (R2).** O painel exibe categoria de risco e recomendação de ação em campos próprios. Com texto livre, como no Exercício 4, alguém ou algum código precisaria interpretar a resposta, e um texto diferente a cada execução quebraria a integração.
- **O esquema é um contrato.** Os campos e os tipos (`str`, `str`, `float`) tornam a saída previsível e permitem usá-la diretamente em código: `resposta.categoria_risco`, `resposta.confianca`.
- **A validação explícita complementa o esquema.** O esquema só garante tipos. Por isso cada objeto passa por uma validação em duas camadas: (1) conformidade com o esquema (instância de `RespostaAgente`, sem campos ausentes, tipos corretos em modo estrito) e (2) regras de negócio (categoria entre `baixo`, `médio` e `alto`, recomendação preenchida, confiança entre 0 e 1). Um valor como `confianca = 1.5` seria válido para o Pydantic, mas inútil para o painel.
- **As restrições de domínio ficam no código de validação, não no esquema.** Optou-se por manter o esquema simples, com descrições dos campos, e verificar as faixas na função de validação, porque o modo estrito de saída estruturada da Groq podia recusar restrições adicionais e isso não foi testado.
- **O campo `confianca` torna a incerteza explícita.** O modelo de churn do TP2 tem poder de discriminação modesto (AUC-ROC de 0,664), então a resposta precisa sinalizar o quanto os dados sustentam a conclusão.

**O que se observou.** Os quatro objetos retornados foram instâncias de `RespostaAgente` e passaram nas duas camadas de validação (4 de 4).

### 3.3 Execução assíncrona

**Decisão.** O agente é executado com `Runner.run(...)` dentro de funções `async def`, e as perguntas são disparadas em paralelo com `asyncio.gather(...)`, a partir de `asyncio.run(...)`.

**Por que é necessária para a NeoStream.**

- **As solicitações chegam ao mesmo tempo (R3).** Cada chamada ao modelo passa a maior parte do tempo esperando a rede. Com `Runner.run_sync(...)`, o programa fica parado em cada espera e as solicitações simultâneas seriam atendidas uma após a outra, bloqueando o painel.
- **A espera é de entrada e saída, não de processamento.** Por isso a concorrência em um único laço de eventos resolve o problema sem threads nem processos adicionais: enquanto uma chamada espera a resposta, as outras seguem.
- **O ganho cresce com o número de solicitações.** O tempo total passa a ser o da chamada mais lenta, e não a soma de todas.

**O que se observou.** Com quatro perguntas em paralelo:

| Medida | Tempo |
|---|---|
| Tempo total com `asyncio.gather` (medido) | 2,14 s |
| Estimativa sequencial (soma das durações: 0,80 + 1,26 + 2,13 + 1,58 s) | 5,77 s |
| Redução | cerca de 63% (aproximadamente 2,7 vezes mais rápido) |

O tempo total (2,14 s) é praticamente igual ao da chamada mais longa (2,13 s), como esperado.

### 3.4 Decisões complementares

| Decisão | Por que é necessária |
|---|---|
| **Groq como provedor, por meio do `AsyncOpenAI` com `base_url`** | Foi o provedor recomendado pelo professor. Como a API é compatível com a da OpenAI, o `openai-agents` funciona sem alterações além do cliente e do modelo (`OpenAIChatCompletionsModel`). |
| **Chave e modelo lidos de variáveis de ambiente (`.env` com `python-dotenv`)** | Atende R4: a chave nunca aparece no código nem no ZIP, e o modelo pode ser trocado sem editar o script. Isso se mostrou necessário na prática, porque o modelo inicial foi desativado pela Groq e a troca exigiu mudar apenas o `.env`. |
| **Novas tentativas para `json_validate_failed` e para o limite de tokens por minuto (429)** | A Groq recusou de forma intermitente respostas do modelo no modo de saída estruturada e impõe limite de 8.000 tokens por minuto no plano usado. Sem o tratamento, uma falha isolada derrubaria o painel. Os demais erros (por exemplo, chave inválida) são propagados na hora para não serem mascarados. |
| **Falha isolada por pergunta (`return_exceptions=True`)** | Em produção, a falha de uma solicitação não pode impedir a resposta das outras. O script registra qual pergunta falhou e segue com as demais. |
| **Esforço de raciocínio baixo (`reasoning.effort="low"`)** | A tarefa é classificar o risco e redigir uma recomendação curta, o que não exige raciocínio longo, e um esforço menor reduz tokens e latência, que são os recursos limitados pelo provedor. |
| **Sem ferramentas externas** | O enunciado do projeto restringe esta etapa aos primitivos `Agent` e `Runner`. A consulta ao modelo de churn como ferramenta é a evolução natural, descrita na seção 6. |

## 4. Execução do agente final

O agente foi executado com quatro perguntas sobre assinantes específicos (fictícios) em 19/11/2026.

| Assinante | Perfil informado | `categoria_risco` | `confianca` | Tentativas | Duração |
|---|---|---|---|---|---|
| #3021 | 4 meses, 3,1 h/semana, 4 reclamações | alto | 0.75 | 1 | 0,80 s |
| #1187 | 62 meses, 15,8 h/semana, sem reclamações | baixo | 0.95 | 2 | 1,26 s |
| #2504 | 36 meses, 1 reclamação, uso caiu para 1,2 h/semana | médio | 0.7 | 3 | 2,13 s |
| #4410 | 2 meses, 2 reclamações, **sem dado de uso** | alto | 0.62 | 2 | 1,58 s |

Recomendações retornadas:

- **#3021:** "Entre em contato proativo com o assinante para entender e resolver as 4 reclamações, oferecendo suporte dedicado antes da renovação."
- **#1187:** "Não inclua o assinante na campanha de desconto; seu longo tempo de assinatura, alto uso semanal e ausência de reclamações indicam baixo risco de churn."
- **#2504:** "Entre em contato reconhecendo a reclamação e ofereça sugestões de conteúdo ou um plano de reativação para aumentar o uso semanal, já que o baixo engajamento é o principal sinal de risco."
- **#4410:** "Priorize um contato imediato, pois o assinante tem duas reclamações em apenas 2 meses de assinatura, indicando alto risco de churn."

Resultado da validação: **4 de 4 objetos válidos**, sem nenhum problema reportado nas duas camadas.

## 5. Limitações

- **Uma única execução bem-sucedida está documentada.** Latência, tentativas e textos variam entre execuções, porque o modelo não é determinístico e o provedor tem carga variável.
- **A estimativa sequencial é uma soma de durações medidas durante a execução concorrente,** e não uma execução sequencial real. As durações incluem novas tentativas.
- **Instabilidade do provedor.** Quatro das oito tentativas (soma das tentativas das quatro perguntas) falharam e foram refeitas. O contador não distingue falhas de validação de JSON de esperas por limite de tokens. Em uma execução anterior, com o esforço de raciocínio padrão, o script esgotou as tentativas e terminou em erro; depois de adotar o esforço baixo, as quatro perguntas foram concluídas. Não foi feita uma comparação controlada, então não é possível afirmar que o ajuste foi a causa.
- **A validação confere forma e regras de domínio, não a qualidade das recomendações.** Avaliar se a ação é a melhor exigiria comparar com decisões reais da equipe de retenção.
- **`confianca` é uma estimativa declarada pelo modelo de linguagem,** não uma probabilidade calibrada nem a taxa de acerto do modelo de churn do TP2.
- **As perguntas e os assinantes são fictícios,** e o agente não usa o dataset nem o modelo de churn do TP2.

## 6. Relação com o ciclo perceber-raciocinar-agir (Exercício 1)

O Exercício 1 descreveu a arquitetura-alvo do componente. A tabela mostra como cada etapa do ciclo aparece no comportamento observado do agente final.

| Etapa | O que o Exercício 1 previa | O que se observou no agente final |
|---|---|---|
| **Perceber** | A pergunta em linguagem natural, os dados do assinante citados nela, as instruções do sistema e o resultado de ações anteriores | O agente recebeu quatro perguntas de formato livre, cada uma com um assinante específico e dados diferentes, além das instruções. Ele percebeu também **o que não foi informado**: no assinante #4410 não havia dado de uso. Não houve resultados de ferramentas para perceber. |
| **Raciocinar** | Interpretar a intenção, verificar o que falta, interpretar a evidência à luz do negócio, identificar os fatores do risco e avaliar a própria certeza | **Intenção:** na pergunta sobre desconto (#1187), entendeu que a decisão era sobre custo-benefício e não apenas sobre risco. **Fatores:** citou os fatores decisivos de cada caso (as 4 reclamações em #3021, o baixo engajamento como principal sinal em #2504, as 2 reclamações em 2 meses em #4410). **Sinais contraditórios:** em #2504, longa permanência com uso em queda, resultou em risco médio e confiança 0.7. **Certeza:** a confiança ficou mais baixa onde faltavam dados (#4410, 0.62) e mais alta onde todos os sinais convergiam (#1187, 0.95). |
| **Agir** | Reunir informação com ferramentas, produzir a resposta fundamentada e repetir o ciclo se a observação mudar a conclusão | A ação foi **produzir a resposta estruturada**, com recomendação concreta e adequada ao perfil: contato proativo para #3021, **não** conceder desconto a #1187, reengajamento por conteúdo para #2504 e contato imediato para #4410. Cada recomendação cita o fator que a justifica. |

**Onde o comportamento observado fica aquém da arquitetura-alvo.**

- **Não houve coleta de informação.** O agente não consultou o modelo de churn nem pediu o dado de uso que faltava em #4410: lidou com a lacuna apenas reduzindo a confiança. Na arquitetura completa, perceber a lacuna levaria a uma ação para obter o dado.
- **O laço do ciclo não se manifestou.** Cada pergunta foi respondida em uma única passagem do agente, sem que o resultado de uma ação alimentasse um novo raciocínio. As novas tentativas observadas (1 a 3 por pergunta) foram feitas pelo código de execução para contornar falhas do provedor, e não por uma decisão do agente.

**Conclusão.** O agente final demonstra, em forma reduzida, as etapas de perceber e raciocinar (ele distingue perfis, pesa sinais, trata dado ausente e calibra a confiança) e uma ação de resposta estruturada. A diferença para um script de previsão é visível: a mesma entrada de dados recebe tratamentos diferentes conforme a pergunta e o contexto. O passo seguinte para completar o ciclo é transformar o modelo de churn do TP2 em uma ferramenta que o agente decida quando chamar, o que permitiria buscar o dado faltante e reavaliar a conclusão, ou seja, um ciclo completo de percepção, raciocínio e ação.
