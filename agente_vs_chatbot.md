# Agente de IA vs chatbot vs software baseado em regras

## 1. Resposta direta à pergunta do gerente de produto

**O componente de análise de churn é "só um chatbot com acesso ao modelo de churn"?** Não. Um chatbot com acesso ao modelo apenas repassaria, em forma de texto, o número que o modelo devolve. O componente proposto no Exercício 1 decide por conta própria quais informações precisa reunir, interpreta o resultado à luz do contexto de negócio e entrega uma recomendação estruturada. Essa diferença altera o escopo do projeto: o que se constrói, como se valida e o que o time de produto pode esperar do componente.

## 2. Definições usadas neste documento

- **Chatbot tradicional:** interface conversacional que responde a cada mensagem a partir de fluxos e intenções predefinidos, ou apenas do conhecimento do modelo de linguagem. Não executa ações no ambiente nem decide quais passos tomar: dada uma mensagem, devolve uma resposta.
- **Software convencional baseado em regras:** programa cujas decisões são `if/else` escritos de antemão por pessoas. Todo caminho possível precisa ter sido previsto no código.
- **Agente de IA:** sistema que recebe um objetivo, decide por conta própria quais passos executar, usa ferramentas para agir e observar o ambiente e repete o ciclo perceber-raciocinar-agir (Exercício 1) até ter base para responder.

## 3. Características que diferenciam o agente

| # | Característica | Software baseado em regras | Chatbot tradicional | Agente de IA |
|---|---|---|---|---|
| 1 | **Autonomia na escolha dos passos** | Nenhuma: o fluxo é fixo e escrito pelo desenvolvedor. | Baixa: segue o fluxo de conversa ou apenas responde à última mensagem. | Alta: decide quais passos executar e em que ordem, conforme a pergunta. |
| 2 | **Uso de ferramentas e ação sobre o ambiente** | Chama funções, mas sempre as mesmas, nos mesmos pontos. | Em geral só produz texto. | Escolhe quando e qual ferramenta usar (consultar um modelo, buscar um dado) e age sobre o resultado. |
| 3 | **Raciocínio em vários passos com realimentação** | Passagem única, sem revisão do caminho. | Um turno de pergunta e resposta, sem laço interno de verificação. | Laço: o resultado de uma ação vira nova observação e pode mudar o próximo passo. |
| 4 | **Orientação a objetivo** | Executa um roteiro, não persegue um objetivo. | Responde ao que foi dito, sem perseguir um resultado. | Recebe um objetivo ("avaliar o risco deste assinante e recomendar uma ação") e organiza os passos para atingi-lo. |
| 5 | **Tratamento de entradas não previstas** | Falha ou cai num caso padrão quando a entrada foge das regras. | Tende a pedir reformulação ou a responder de forma genérica. | Interpreta linguagem natural livre e lida com lacunas, pedindo o dado que falta ou declarando a limitação. |

## 4. Aplicação ao cenário da NeoStream

A tabela abaixo aplica cada característica ao componente de análise de churn.

| Característica | Como aparece no caso da NeoStream |
|---|---|
| Autonomia na escolha dos passos | As perguntas do time de retenção variam (risco de um assinante, comparação entre perfis, pergunta sobre desconto). O componente decide o que precisa reunir em cada caso, em vez de seguir um roteiro único. |
| Ferramentas e ação | Na arquitetura completa, o modelo de churn do TP2 é uma ferramenta: o agente decide quando consultá-lo e usa o resultado na resposta. |
| Raciocínio com realimentação | A saída do modelo exige interpretação. Nos dados do TP2, o modelo quase não passa de 0,5 de probabilidade (máximo de 0,5376 no teste) e o limiar padrão captura só 1,2% dos cancelamentos. Uma probabilidade de 0,17 está acima da taxa de churn da base (cerca de 17,5%) e só vira alerta com limiares como 0,10. O agente precisa traduzir isso em categoria de risco, e não repetir o número. |
| Orientação a objetivo | O time quer saber o que fazer com o assinante, não apenas a probabilidade. O objetivo é uma recomendação de ação de retenção, com justificativa. |
| Entradas não previstas | O time pergunta em linguagem natural, com dados completos ou incompletos. Um sistema de regras teria de prever cada combinação de perfil e de formulação. |

### Por que projetar como agente e não como chatbot

1. **Um chatbot com acesso ao modelo entrega o número, não a decisão.** O valor para a retenção está em interpretar o resultado e recomendar uma ação, e isso exige raciocínio sobre o contexto, não só acesso à informação.
2. **A saída precisa ser integrável.** O painel do time (Exercício 5) espera categoria de risco, recomendação e confiança em formato validável por código. Um chatbot devolve texto conversacional que alguém precisaria interpretar manualmente.
3. **O modelo subjacente é fraco e exige cautela.** Com AUC-ROC de 0,664, a resposta precisa vir acompanhada de um grau de confiança honesto. Esse tipo de julgamento sobre a própria resposta é parte do raciocínio do agente, e não de um fluxo de conversa.
4. **Regras não cobrem a variedade de perguntas.** Um sistema de regras exigiria enumerar de antemão todas as combinações de perfil e de intenção, e a cobertura nunca seria completa.

### O que o componente pode e não pode fazer de forma autônoma

Para alinhar as expectativas do time de produto:

- **Pode:** interpretar a pergunta, decidir quais informações usar, consultar o modelo de churn (na arquitetura completa), classificar o risco, recomendar uma ação e informar o grau de confiança.
- **Não deve:** aplicar descontos, disparar campanhas ou alterar dados de assinantes por conta própria. O componente **recomenda**, e a decisão e a execução continuam com o time de retenção.
- **Não garante:** acerto. A resposta herda a limitação do modelo (AUC-ROC de 0,664) e deve ser tratada como apoio à decisão.

Nas versões construídas neste projeto (Exercícios 4 a 8), o agente não usa ferramentas externas, como o enunciado define, e as respostas se baseiam nas instruções e nas informações da própria pergunta. A consulta ao modelo de churn como ferramenta é a evolução natural da arquitetura.

## 5. Quando um chatbot simples seria suficiente

**Caso de uso: perguntas frequentes sobre a política de cancelamento.** Exemplos: "Como cancelo minha assinatura?" ou "Existe prazo mínimo de permanência?". As características desse caso são:

- as respostas são **estáticas**, com o conteúdo definido pela empresa e igual para todos os clientes;
- **não há dados do cliente a consultar** nem decisão a tomar;
- **não há ação a executar** além de responder;
- um erro de interpretação tem **custo baixo** e a pergunta tem um conjunto pequeno de variações.

Um chatbot de FAQ, com fluxos predefinidos ou um modelo de linguagem com o texto da política, resolve o problema. Montar um agente com planejamento de passos, ferramentas e saída estruturada acrescentaria custo, latência e complexidade de validação sem acrescentar valor.

Outro exemplo no mesmo nível é um glossário ("o que significa churn?"), em que a resposta independe de qualquer dado do assinante.

**Observação.** O agente do Exercício 4 responde exatamente a perguntas desse tipo (política de cancelamento, sem ferramentas). Ele é uma prova de conceito dos primitivos do SDK (`Agent` e `Runner`), e, do ponto de vista funcional, é equivalente a um chatbot. O que o distingue de um chatbot de FAQ é o uso das ferramentas e do ciclo completo, que é o que o componente de churn adicionaria.

## 6. Conclusão

O componente de análise de churn deve ser projetado como agente porque a tarefa exige decidir quais informações reunir, interpretar um resultado de modelo que não é autoexplicativo e entregar uma recomendação integrável ao painel do time. Um chatbot resolve bem perguntas estáticas, como as da política de cancelamento, e um sistema de regras resolve bem tarefas totalmente previsíveis. O agente se justifica onde a pergunta varia, o contexto importa e a resposta precisa de raciocínio.
