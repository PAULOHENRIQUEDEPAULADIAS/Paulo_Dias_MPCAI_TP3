import openai
from agents import Runner, set_tracing_disabled

from agente_saida_estruturada import criar_agente
from execucao_assincrona import PERGUNTAS

TENTATIVAS = 3


def main():
    set_tracing_disabled(True)
    agente = criar_agente()

    for numero, pergunta in enumerate(PERGUNTAS, start=1):
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                resultado = Runner.run_sync(agente, pergunta)
                print(f"Pergunta {numero}, tentativa {tentativa}: OK -> {resultado.final_output!r}")
            except openai.BadRequestError as erro:
                print(f"Pergunta {numero}, tentativa {tentativa}: ERRO 400 -> {erro.body}")


if __name__ == "__main__":
    main()
