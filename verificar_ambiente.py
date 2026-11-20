import os
import sys
from importlib.metadata import version

from agents import OpenAIChatCompletionsModel
from dotenv import load_dotenv
from openai import AsyncOpenAI

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
VARIAVEL_CHAVE = "GROQ_API_KEY"
VARIAVEL_MODELO = "GROQ_MODEL"


def falhar(mensagem):
    print(f"[ERRO] {mensagem}")
    sys.exit(1)


def main():
    load_dotenv()

    print(f"openai-agents: {version('openai-agents')}")
    print(f"python-dotenv: {version('python-dotenv')}")

    chave = os.environ.get(VARIAVEL_CHAVE, "").strip()
    modelo = os.environ.get(VARIAVEL_MODELO, "").strip()

    if not chave:
        falhar(f"{VARIAVEL_CHAVE} não está definida. Copie .env.example para .env e preencha a chave.")
    if not modelo:
        falhar(f"{VARIAVEL_MODELO} não está definida. Copie .env.example para .env e preencha o modelo.")

    print(f"{VARIAVEL_CHAVE}: definida ({len(chave)} caracteres, valor oculto)")
    print(f"{VARIAVEL_MODELO}: {modelo}")

    cliente = AsyncOpenAI(api_key=chave, base_url=GROQ_BASE_URL)
    if cliente.api_key != chave:
        falhar("O cliente do SDK não recebeu a chave da variável de ambiente.")

    OpenAIChatCompletionsModel(model=modelo, openai_client=cliente)

    print(f"Cliente do SDK configurado para {cliente.base_url} com a chave lida do ambiente.")
    print("Ambiente verificado com sucesso.")


if __name__ == "__main__":
    main()
