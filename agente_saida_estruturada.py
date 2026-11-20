import os
import time

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI, BadRequestError, RateLimitError
from pydantic import BaseModel, Field

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
TENTATIVAS_MAXIMAS = 10
CODIGO_ERRO_JSON = "json_validate_failed"
ESPERA_PADRAO_S = 10.0

INSTRUCOES = (
    "Você é um analista de risco de churn da NeoStream, um serviço de streaming por assinatura, "
    "e apoia o time de retenção. "
    "Receba a pergunta do time, que descreve um assinante, e devolva uma análise estruturada. "
    "Use somente os dados informados na pergunta: você não tem acesso ao modelo de churn nem a outras bases, "
    "então não invente dados do assinante. "
    "Como referência, o modelo de churn da NeoStream indica que mais reclamações aumentam o risco de cancelamento "
    "e que mais tempo de assinatura e mais horas de uso semanal o reduzem. "
    "Preencha os campos assim: categoria_risco deve ser exatamente 'baixo', 'médio' ou 'alto'; "
    "recomendacao deve ser uma ação concreta de retenção para o time, em uma ou duas frases; "
    "confianca deve ser um número entre 0.0 e 1.0 que reflita o quanto os dados informados sustentam a análise, "
    "com valores menores quando faltarem dados ou quando os sinais forem contraditórios."
)

PERGUNTA = (
    "Um assinante tem 7,7 meses de assinatura, usa a plataforma 4,9 horas por semana "
    "e abriu 3 reclamações. Qual é o risco de ele cancelar e o que o time de retenção deve fazer?"
)


class RespostaAgente(BaseModel):
    categoria_risco: str = Field(description="Categoria de risco de churn: baixo, médio ou alto.")
    recomendacao: str = Field(description="Ação recomendada ao time de retenção, em uma ou duas frases.")
    confianca: float = Field(description="Confiança na análise, de 0.0 a 1.0.")


def criar_agente():
    load_dotenv()
    cliente = AsyncOpenAI(api_key=os.environ["GROQ_API_KEY"], base_url=GROQ_BASE_URL)
    modelo = OpenAIChatCompletionsModel(model=os.environ["GROQ_MODEL"], openai_client=cliente)
    return Agent(
        name="Analista de Risco de Churn NeoStream",
        instructions=INSTRUCOES,
        model=modelo,
        output_type=RespostaAgente,
    )


def executar_com_tentativas(agente, pergunta):
    for tentativa in range(1, TENTATIVAS_MAXIMAS + 1):
        try:
            return Runner.run_sync(agente, pergunta).final_output
        except RateLimitError as erro:
            if tentativa == TENTATIVAS_MAXIMAS:
                raise
            time.sleep(float(erro.response.headers.get("retry-after", ESPERA_PADRAO_S)))
        except BadRequestError as erro:
            if erro.code != CODIGO_ERRO_JSON or tentativa == TENTATIVAS_MAXIMAS:
                raise


def main():
    set_tracing_disabled(True)
    agente = criar_agente()

    resposta = executar_com_tentativas(agente, PERGUNTA)

    print(f"Pergunta: {PERGUNTA}")
    print(f"Tipo do retorno: {type(resposta).__name__}")
    print(f"categoria_risco: {resposta.categoria_risco}")
    print(f"recomendacao: {resposta.recomendacao}")
    print(f"confianca: {resposta.confianca}")


if __name__ == "__main__":
    main()