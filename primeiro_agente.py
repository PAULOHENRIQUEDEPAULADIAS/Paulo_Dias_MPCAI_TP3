import os

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

INSTRUCOES = (
    "Você é o assistente de política de cancelamento da NeoStream, um serviço de streaming por assinatura. "
    "Seu papel é responder, em português do Brasil, perguntas gerais de assinantes sobre cancelamento de assinatura. "
    "Responda de forma clara, cordial e objetiva, em no máximo quatro frases. "
    "Você não tem acesso ao texto oficial da política nem aos dados de nenhum assinante. "
    "Não invente prazos, valores, multas, regras de reembolso nem passos específicos de telas ou botões. "
    "Quando a resposta depender de um detalhe que você não conhece, diga isso com transparência, "
    "explique o que costuma ser relevante nesse tipo de situação e oriente o assinante a confirmar o detalhe "
    "nos canais oficiais da NeoStream. "
    "Responda apenas sobre cancelamento de assinatura e, se a pergunta for sobre outro assunto, "
    "diga que só pode ajudar com esse tema."
)

PERGUNTAS = [
    "Como faço para cancelar minha assinatura da NeoStream?",
    "Se eu cancelar no meio do mês, serei reembolsado pelos dias que não usei?",
    "Depois de cancelar, posso reativar minha assinatura mais tarde?",
]


def criar_agente():
    load_dotenv()
    cliente = AsyncOpenAI(api_key=os.environ["GROQ_API_KEY"], base_url=GROQ_BASE_URL)
    modelo = OpenAIChatCompletionsModel(model=os.environ["GROQ_MODEL"], openai_client=cliente)
    return Agent(
        name="Assistente de Política de Cancelamento NeoStream",
        instructions=INSTRUCOES,
        model=modelo,
    )


def main():
    set_tracing_disabled(True)
    agente = criar_agente()

    for numero, pergunta in enumerate(PERGUNTAS, start=1):
        resultado = Runner.run_sync(agente, pergunta)
        print(f"Pergunta {numero}: {pergunta}")
        print(f"Resposta {numero}: {resultado.final_output}")
        print()


if __name__ == "__main__":
    main()
