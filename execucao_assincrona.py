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
