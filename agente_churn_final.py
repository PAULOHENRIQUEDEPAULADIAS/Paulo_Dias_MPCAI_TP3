import asyncio
import os
import sys
import time

from agents import Agent, ModelSettings, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from dotenv import load_dotenv
from openai import AsyncOpenAI, BadRequestError, RateLimitError
from openai.types.shared import Reasoning
from pydantic import BaseModel, Field, ValidationError

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
TENTATIVAS_MAXIMAS = 10
CODIGO_ERRO_JSON = "json_validate_failed"
ESPERA_PADRAO_S = 10.0
CATEGORIAS_VALIDAS = {"baixo", "médio", "alto"}
ESFORCO_RACIOCINIO = "low"

INSTRUCOES = (
    "Você é um analista de risco de churn da NeoStream, um serviço de streaming por assinatura, "
    "e apoia o time de retenção. "
    "Receba a pergunta do time, que descreve um assinante específico, e devolva uma análise estruturada. "
    "Use somente os dados informados na pergunta: você não tem acesso ao modelo de churn nem a outras bases, "
    "então não invente dados do assinante. "
    "Como referência, o modelo de churn da NeoStream indica que mais reclamações aumentam o risco de cancelamento "
    "e que mais tempo de assinatura e mais horas de uso semanal o reduzem. "
    "Preencha os campos assim: categoria_risco deve ser exatamente 'baixo', 'médio' ou 'alto'; "
    "recomendacao deve ser uma ação concreta para o time de retenção, em uma ou duas frases "
    "que citem o principal fator dos dados que justifica a ação, "
    "e deve ser a mais adequada ao perfil, inclusive não gastar benefícios com quem tem risco baixo; "
    "confianca deve ser um número entre 0.0 e 1.0 que reflita o quanto os dados informados sustentam a análise, "
    "com valores menores quando faltarem dados ou quando os sinais forem contraditórios."
)

PERGUNTAS = [
    "O assinante #3021 está há 4 meses na NeoStream, usa a plataforma 3,1 horas por semana "
    "e abriu 4 reclamações no período. Ele está em risco de cancelar? O que devemos fazer antes da próxima renovação?",
    "O assinante #1187 tem 62 meses de assinatura, usa a plataforma 15,8 horas por semana "
    "e nunca abriu reclamações. Vale a pena incluí-lo na campanha de desconto de retenção?",
    "O assinante #2504 tem 36 meses de assinatura e uma reclamação, mas o uso caiu para 1,2 hora por semana. "
    "Qual é o risco de ele cancelar e como devemos abordá-lo?",
    "O assinante #4410 assinou há 2 meses e já abriu 2 reclamações, mas ainda não temos o dado de uso semanal dele. "
    "Qual é a prioridade de contato para a equipe de retenção?",
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
        model_settings=ModelSettings(reasoning=Reasoning(effort=ESFORCO_RACIOCINIO)),
        output_type=RespostaAgente,
    )


async def executar_pergunta(agente, pergunta):
    inicio = time.perf_counter()
    for tentativa in range(1, TENTATIVAS_MAXIMAS + 1):
        try:
            resultado = await Runner.run(agente, pergunta)
            return resultado.final_output, tentativa, time.perf_counter() - inicio
        except RateLimitError as erro:
            if tentativa == TENTATIVAS_MAXIMAS:
                raise
            await asyncio.sleep(float(erro.response.headers.get("retry-after", ESPERA_PADRAO_S)))
        except BadRequestError as erro:
            if erro.code != CODIGO_ERRO_JSON or tentativa == TENTATIVAS_MAXIMAS:
                raise


async def executar_todas(agente):
    inicio = time.perf_counter()
    execucoes = await asyncio.gather(
        *(executar_pergunta(agente, pergunta) for pergunta in PERGUNTAS), return_exceptions=True
    )
    return execucoes, time.perf_counter() - inicio


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


def registrar_execucao(numero, pergunta, execucao):
    print(f"Pergunta {numero}: {pergunta}")

    if isinstance(execucao, Exception):
        print(f"  FALHOU: {type(execucao).__name__}: {execucao}")
        print()
        return False, None

    resposta, tentativas, duracao = execucao
    problemas = validar_resposta(resposta)

    print(f"  categoria_risco: {resposta.categoria_risco}")
    print(f"  recomendacao: {resposta.recomendacao}")
    print(f"  confianca: {resposta.confianca}")
    print(f"  tentativas: {tentativas}")
    print(f"  duração da chamada: {duracao:.2f} s")
    print(f"  validação: {'OK' if not problemas else 'FALHOU'}")
    for problema in problemas:
        print(f"    - {problema}")
    print()
    return not problemas, duracao


def main():
    set_tracing_disabled(True)
    agente = criar_agente()

    execucoes, tempo_total = asyncio.run(executar_todas(agente))

    resultados = [
        registrar_execucao(numero, pergunta, execucao)
        for numero, (pergunta, execucao) in enumerate(zip(PERGUNTAS, execucoes), start=1)
    ]

    validos = sum(ok for ok, _ in resultados)
    estimativa_sequencial = sum(duracao for _, duracao in resultados if duracao is not None)
    print(f"Objetos válidos: {validos} de {len(PERGUNTAS)}")
    print(f"Tempo total com asyncio.gather: {tempo_total:.2f} s")
    print(f"Estimativa sequencial (soma das durações): {estimativa_sequencial:.2f} s")

    if validos < len(PERGUNTAS):
        sys.exit(1)


if __name__ == "__main__":
    main()
