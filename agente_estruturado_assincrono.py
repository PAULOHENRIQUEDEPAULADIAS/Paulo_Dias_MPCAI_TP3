import asyncio
import os
import sys

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI, BadRequestError
from pydantic import BaseModel, Field, ValidationError

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
TENTATIVAS_MAXIMAS = 8
CODIGO_ERRO_JSON = "json_validate_failed"
CATEGORIAS_VALIDAS = {"baixo", "médio", "alto"}

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

PERGUNTAS = [
    "Um assinante tem 7,7 meses de assinatura, usa a plataforma 4,9 horas por semana "
    "e abriu 3 reclamações. Qual é o risco de ele cancelar e o que o time de retenção deve fazer?",
    "Um assinante tem 48 meses de assinatura, usa a plataforma 14 horas por semana "
    "e não abriu reclamações. Qual é o risco de ele cancelar e o que o time de retenção deve fazer?",
    "Um assinante tem 3 meses de assinatura e abriu 2 reclamações, mas não temos o dado de uso semanal dele. "
    "Qual é o risco de ele cancelar e o que o time de retenção deve fazer?",
]


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


async def executar_pergunta(agente, pergunta):
    for tentativa in range(1, TENTATIVAS_MAXIMAS + 1):
        try:
            resultado = await Runner.run(agente, pergunta)
            return resultado.final_output, tentativa
        except BadRequestError as erro:
            if erro.code != CODIGO_ERRO_JSON or tentativa == TENTATIVAS_MAXIMAS:
                raise


async def executar_todas(agente):
    return await asyncio.gather(*(executar_pergunta(agente, pergunta) for pergunta in PERGUNTAS))


def validar_resposta(resposta):
    if not isinstance(resposta, RespostaAgente):
        return [f"tipo inesperado: {type(resposta).__name__}"]

    problemas = []
    dados = resposta.model_dump()

    campos_ausentes = set(RespostaAgente.model_fields) - set(dados)
    if campos_ausentes:
        problemas.append(f"campos ausentes: {sorted(campos_ausentes)}")

    try:
        RespostaAgente.model_validate(dados, strict=True)
    except ValidationError as erro:
        problemas.extend(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in erro.errors())

    if resposta.categoria_risco not in CATEGORIAS_VALIDAS:
        problemas.append(f"categoria_risco fora de {sorted(CATEGORIAS_VALIDAS)}: {resposta.categoria_risco!r}")
    if not resposta.recomendacao.strip():
        problemas.append("recomendacao vazia")
    if not 0.0 <= resposta.confianca <= 1.0:
        problemas.append(f"confianca fora do intervalo 0.0 a 1.0: {resposta.confianca}")

    return problemas


def main():
    set_tracing_disabled(True)
    agente = criar_agente()

    execucoes = asyncio.run(executar_todas(agente))

    objetos_invalidos = 0
    for numero, (pergunta, (resposta, tentativas)) in enumerate(zip(PERGUNTAS, execucoes), start=1):
        problemas = validar_resposta(resposta)
        objetos_invalidos += bool(problemas)

        print(f"Pergunta {numero}: {pergunta}")
        print(f"  tipo do retorno: {type(resposta).__name__}")
        print(f"  categoria_risco: {resposta.categoria_risco}")
        print(f"  recomendacao: {resposta.recomendacao}")
        print(f"  confianca: {resposta.confianca}")
        print(f"  tentativas: {tentativas}")
        print(f"  validação: {'OK' if not problemas else 'FALHOU'}")
        for problema in problemas:
            print(f"    - {problema}")
        print()

    validos = len(execucoes) - objetos_invalidos
    print(f"Objetos válidos: {validos} de {len(execucoes)}")
    if objetos_invalidos:
        sys.exit(1)


if __name__ == "__main__":
    main()
