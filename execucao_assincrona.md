# Execução assíncrona do agente de churn

## 1. Objetivo

O painel do time de retenção recebe solicitações simultâneas de vários usuários. Com `Runner.run_sync(...)`, cada chamada bloqueia o programa até a resposta chegar, então duas solicitações simultâneas seriam atendidas uma depois da outra. Este documento registra a reescrita da execução do agente do Exercício 5 de forma assíncrona e a medição do ganho de tempo com duas chamadas concorrentes.

## 2. Implementação

O agente é o mesmo do Exercício 5 (`criar_agente()` de `agente_saida_estruturada.py`, com `output_type=RespostaAgente`). Só a execução foi reescrita:

- `executar_pergunta` é uma função `async def` que chama `await Runner.run(...)`, a versão assíncrona do `Runner`, e mede a duração da chamada;
- `executar_concorrente` dispara as duas perguntas ao mesmo tempo com `asyncio.gather(...)` e mede o tempo total;
- `asyncio.run(...)` é o ponto de entrada, a partir da função `main()` do script.

A Groq retornou, de forma intermitente, o erro 400 `json_validate_failed` (o modelo gera uma saída que não passa na validação do esquema, e o servidor a recusa). Por isso `executar_pergunta` refaz a chamada, até 5 tentativas, quando o erro tem exatamente esse código, e qualquer outro erro é propagado imediatamente. A duração de cada chamada inclui as tentativas extras.

Código utilizado (script `execucao_assincrona.py`):

```python
import asyncio
import time

import openai
from agents import Runner, set_tracing_disabled

from agente_saida_estruturada import PERGUNTA, criar_agente

PERGUNTAS = [
    PERGUNTA,
    "Um assinante tem 48 meses de assinatura, usa a plataforma 14 horas por semana "
    "e não abriu reclamações. Qual é o risco de ele cancelar e o que o time de retenção deve fazer?",
]

TENTATIVAS_MAXIMAS = 5
CODIGO_ERRO_JSON = "json_validate_failed"


async def executar_pergunta(agente, pergunta):
    inicio = time.perf_counter()
    for tentativa in range(1, TENTATIVAS_MAXIMAS + 1):
        try:
            resultado = await Runner.run(agente, pergunta)
            break
        except openai.BadRequestError as erro:
            if erro.code != CODIGO_ERRO_JSON or tentativa == TENTATIVAS_MAXIMAS:
                raise
    duracao = time.perf_counter() - inicio
    return resultado.final_output, duracao, tentativa


async def executar_concorrente(agente):
    inicio = time.perf_counter()
    execucoes = await asyncio.gather(*(executar_pergunta(agente, pergunta) for pergunta in PERGUNTAS))
    tempo_total = time.perf_counter() - inicio
    return execucoes, tempo_total


def main():
    set_tracing_disabled(True)
    agente = criar_agente()

    execucoes, tempo_total = asyncio.run(executar_concorrente(agente))

    for numero, (pergunta, (resposta, duracao, tentativas)) in enumerate(zip(PERGUNTAS, execucoes), start=1):
        print(f"Pergunta {numero}: {pergunta}")
        print(f"  categoria_risco: {resposta.categoria_risco}")
        print(f"  recomendacao: {resposta.recomendacao}")
        print(f"  confianca: {resposta.confianca}")
        print(f"  duração da chamada: {duracao:.2f} s")
        print(f"  tentativas: {tentativas}")
        print()

    estimativa_sequencial = sum(duracao for _, duracao, _ in execucoes)
    print(f"Tempo total com asyncio.gather: {tempo_total:.2f} s")
    print(f"Estimativa sequencial (soma das durações): {estimativa_sequencial:.2f} s")


if __name__ == "__main__":
    main()
```

## 3. Resultado da execução

As duas perguntas usadas foram:

1. Assinante com 7,7 meses de assinatura, 4,9 horas semanais de uso e 3 reclamações.
2. Assinante com 48 meses de assinatura, 14 horas semanais de uso e nenhuma reclamação.

| | Pergunta 1 | Pergunta 2 |
|---|---|---|
| `categoria_risco` | médio | baixo |
| `confianca` | 0.78 | 0.9 |
| Duração da chamada | 2,31 s | 2,93 s |
| Tentativas | 2 | 3 |

Recomendações retornadas:

- **Pergunta 1:** "Entrar em contato proativo, oferecer suporte dedicado e um benefício (ex.: desconto ou conteúdo exclusivo) para reduzir a insatisfação."
- **Pergunta 2:** "Enviar um e‑mail de agradecimento personalizado com um benefício de fidelidade (ex.: desconto ou conteúdo exclusivo) para reforçar o engajamento."

## 4. Comparação com o tempo sequencial

| Medida | Tempo |
|---|---|
| Tempo total com `asyncio.gather` (medido) | **2,93 s** |
| Estimativa sequencial (soma das durações das duas chamadas: 2,31 s + 2,93 s) | **5,25 s** |
| Redução | 2,32 s (cerca de 44%) |
| Fator de ganho (5,25 s ÷ 2,93 s) | cerca de 1,8 vez mais rápido |

O tempo total (2,93 s) é praticamente igual à duração da chamada mais longa (a pergunta 2, também 2,93 s). Esse é o comportamento esperado da execução concorrente: enquanto uma chamada espera a resposta da rede, a outra segue em andamento no mesmo laço de eventos, e o tempo total passa a ser o da mais demorada, e não a soma das duas. A execução sequencial levaria cerca de 5,25 s, porque cada chamada só começaria depois do fim da anterior.

Com duas chamadas, o ganho máximo teórico é de 2 vezes, e só seria atingido se as duas durassem o mesmo tempo. Aqui ele ficou em cerca de 1,8 vez porque a pergunta 1 terminou antes da 2 (uma tentativa a menos).

## 5. Limitações da medição

- **A estimativa sequencial é uma soma, não uma execução real.** Foi calculada a partir das durações medidas durante a execução concorrente. Em uma execução sequencial de verdade, os tempos poderiam variar um pouco.
- **Uma única execução está documentada.** A latência da API varia com a carga do provedor, então os números mudam de uma execução para outra, e o ganho observado é indicativo, não um valor garantido.
- **As durações incluem novas tentativas.** Cada tentativa levou algo em torno de 1 s (duração dividida pelas tentativas: 2,31 s ÷ 2 e 2,93 s ÷ 3). Sem as falhas do provedor, as duas chamadas terminariam em aproximadamente 1 s cada, e o tempo total seria menor. A comparação entre concorrente e sequencial continua válida, porque ambas sofreriam a mesma influência das tentativas extras.
- **Falhas intermitentes da Groq.** Em um teste separado com seis chamadas sequenciais, duas retornaram o erro 400 `json_validate_failed` com `failed_generation` vazio; nesta execução, três das cinco tentativas falharam. O tratamento por novas tentativas contorna o problema, mas não o elimina: o esperado é que, com cinco tentativas por pergunta, falhas totais sejam raras, não impossíveis.

## 6. Conclusão

A execução assíncrona com `Runner.run(...)`, `asyncio.run(...)` e `asyncio.gather(...)` funcionou com o agente de saída estruturada e atendeu duas solicitações em 2,93 s, contra uma estimativa de 5,25 s no modo sequencial. Para o painel do time de retenção, isso significa que solicitações simultâneas não ficam enfileiradas atrás umas das outras, e o ganho cresce com o número de solicitações concorrentes. O tratamento de `json_validate_failed` torna a execução mais confiável diante da instabilidade observada no provedor.
