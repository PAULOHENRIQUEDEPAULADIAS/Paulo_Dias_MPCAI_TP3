# Arquitetura do agente de análise de churn: ciclo perceber-raciocinar-agir

## 1. Contexto

O modelo de churn do TP2 (Pipeline com `LogisticRegression`, C = 0,1) recebe uma linha de features já formatada e devolve 0 ou 1. O time de retenção da NeoStream precisa de algo diferente: fazer uma pergunta em linguagem natural, como "qual o risco de cancelamento deste assinante e o que devemos fazer?", e receber uma resposta fundamentada. Esse componente é um **agente de IA**, cuja arquitetura se organiza no ciclo **perceber → raciocinar → agir**.

## 2. O ciclo aplicado ao time de retenção

### 2.1 Perceber

O que o componente recebe e observa:

- **A pergunta do analista de retenção**, em texto livre e sem formato fixo. Exemplos: "O assinante com 7,7 meses de casa, 4,9 h de uso semanal e 3 reclamações está em risco?" ou "Vale a pena oferecer desconto para quem tem 72 meses de assinatura?".
- **Os dados do assinante citados na pergunta**: tempo de assinatura, uso médio semanal, número de reclamações, plano, método de pagamento e dispositivo principal, que são as mesmas variáveis do modelo de churn.
- **As instruções do sistema**, que definem o papel do agente (analista de risco de churn da NeoStream) e as regras de resposta.
- **Os resultados de cada ação executada**. Na arquitetura completa, a saída de uma ferramenta, como a probabilidade devolvida pelo modelo de churn, volta ao agente como nova observação e alimenta o próximo passo do raciocínio.

### 2.2 Raciocinar

Sobre o que o componente raciocina, em ordem:

1. **Interpretar a intenção** da pergunta: se é um diagnóstico de risco, uma comparação entre assinantes ou um pedido de ação de retenção.
2. **Verificar o que falta**: se a pergunta traz dados suficientes ou se é preciso pedir ou consultar mais informações antes de concluir.
3. **Decidir qual informação reunir** e em que ordem, por exemplo se precisa consultar o modelo de churn ou se a pergunta pode ser respondida só com o contexto disponível.
4. **Interpretar a evidência à luz do negócio**. Um exemplo concreto do TP2: o modelo quase nunca passa de 0,5 de probabilidade (máximo de 0,5376 no teste), e com o limiar padrão o recall é de apenas 1,2%. Uma probabilidade de 0,17 (assinante 10935, que cancelou) não é "baixo risco" no sentido usual: ela fica acima da taxa de churn da base (cerca de 17,5%) e só vira alerta com limiares como 0,10. Um agente que raciocina precisa traduzir a probabilidade bruta em uma categoria de risco coerente com isso.
5. **Identificar os fatores do risco**, a partir do que o modelo aprendeu: mais reclamações aumentam o risco, e mais tempo de casa e mais uso o reduzem.
6. **Avaliar o próprio grau de certeza**, lembrando que o poder discriminativo do modelo é modesto (AUC-ROC de 0,664).

### 2.3 Agir

A ação é o que o componente efetivamente faz com esse raciocínio:

- **Reunir informação**: chamar uma ferramenta (por exemplo, o modelo de churn) quando concluir que precisa dela, ou pedir ao analista o dado que falta.
- **Produzir a resposta final**, composta por uma categoria de risco, a justificativa com base nos fatores observados, uma recomendação de ação para a equipe de retenção e o grau de confiança na resposta.
- **Repetir o ciclo** se a observação nova mudar a conclusão (por exemplo, a ferramenta devolve um resultado inesperado), até ter base suficiente para responder.

### 2.4 Fluxo do ciclo

```
 Pergunta em linguagem natural
            │
            ▼
   ┌──────────────────┐
   │     PERCEBER     │  pergunta, dados do assinante, instruções,
   │                  │  resultado de ações anteriores
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │    RACIOCINAR    │  intenção, o que falta, qual informação reunir,
   │                  │  interpretação do risco e da confiança
   └────────┬─────────┘
            ▼
   ┌──────────────────┐        faltou informação?
   │       AGIR       │ ───────────────────────────► volta a PERCEBER
   │                  │        (nova observação)
   └────────┬─────────┘
            ▼
 Resposta fundamentada (risco, recomendação, confiança)
```

## 3. Comparação com o fluxo linear de um script tradicional

O script tradicional segue `entrada fixa → função → saída fixa`: recebe um vetor com as seis features na ordem esperada, aplica `pipeline.predict(...)` e devolve 0 ou 1 (ou uma probabilidade). O agente, em vez disso, percorre o ciclo acima.

| Aspecto | Script tradicional | Agente (perceber-raciocinar-agir) |
|---|---|---|
| **Entrada** | Fixa e estruturada: colunas, tipos e ordem definidos de antemão. Qualquer desvio gera erro. | Pergunta em linguagem natural, de formato livre, que o agente interpreta. |
| **Controle de fluxo** | Determinado pelo desenvolvedor em tempo de escrita: sempre os mesmos passos, na mesma ordem. | Decidido em tempo de execução pelo agente: ele escolhe o que fazer em cada passo, e o número de passos varia conforme a pergunta. |
| **Uso de informação externa** | Nenhum além dos parâmetros da função. | Decide se precisa de mais informação e age para obtê-la, incorporando o resultado ao raciocínio seguinte. |
| **Estrutura do processamento** | Linear, de uma passagem, sem retorno. | Cíclica: o resultado de uma ação realimenta a percepção. |
| **Saída** | Fixa e sem explicação: 0/1 ou uma probabilidade. | Resposta fundamentada, com categoria de risco, justificativa, recomendação e confiança. |
| **Tratamento de lacunas e ambiguidade** | Não trata: dado ausente ou mal formatado interrompe a execução. | Percebe a lacuna e pode pedir o dado ou declarar a limitação na resposta. |
| **Previsibilidade** | Determinística e reproduzível: a mesma entrada gera sempre a mesma saída. | Não determinística: a mesma pergunta pode gerar redações diferentes, e por isso a saída precisa ser validada (daí o uso de saída estruturada em etapas posteriores). |

### Diferenças arquiteturais concretas

1. **Quem controla o fluxo.** No script, a sequência de passos está escrita no código. No agente, o próprio componente decide quais passos executar e quantos, de acordo com a pergunta e com o que já observou.
2. **Topologia do processamento.** O script é uma passagem única (entrada → função → saída). O agente é um laço: cada ação produz uma observação que volta ao início do ciclo, o que permite corrigir o rumo antes de responder.
3. **Natureza da entrada e da saída.** O script exige um contrato rígido de dados e devolve um número. O agente aceita linguagem natural e devolve uma resposta argumentada que o time de retenção pode usar diretamente.

### Contrapartida

A flexibilidade do agente tem custo: menor previsibilidade, mais latência e maior necessidade de validação da saída. Por isso o script continua sendo a melhor escolha quando a tarefa é sempre a mesma (por exemplo, pontuar toda a base em lote), e o agente se justifica quando a pergunta varia e a resposta precisa de contexto e explicação.

## 4. Observação sobre a implementação neste projeto

O ciclo descrito é a arquitetura-alvo do componente. Nas entregas seguintes ele é construído em etapas: o agente é criado com instruções e executado com o `Runner` (Exercícios 4 a 7) e, na versão final (Exercício 8), responde com saída estruturada e execução assíncrona. Como o enunciado do Exercício 4 estabelece "sem ferramentas externas ainda", nessas versões a etapa de ação se resume a produzir a resposta final, e a coleta de informação por ferramentas (como a consulta ao modelo de churn) fica como evolução natural da arquitetura.
