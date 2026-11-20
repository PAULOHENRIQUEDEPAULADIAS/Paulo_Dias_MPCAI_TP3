# Validação da saída estruturada do agente de churn

## 1. Objetivo

O painel do time de retenção depende de um formato previsível: `categoria_risco` (texto), `recomendacao` (texto) e `confianca` (número). Este documento registra a execução assíncrona do agente para três perguntas sobre risco de churn (`agente_estruturado_assincrono.py`) e a validação programática de que os três objetos `RespostaAgente` retornados respeitam o esquema.

## 2. Execução

O script usa o `Agent` com `output_type=RespostaAgente` (Exercício 5) e executa as três perguntas ao mesmo tempo com `Runner.run(...)`, `asyncio.run(...)` e `asyncio.gather(...)` (Exercício 6). Em caso de erro 400 `json_validate_failed` (intermitente na Groq) ou de limite de tokens por minuto (erro 429), a chamada é refeita, até 8 tentativas.

- **Modelo:** `openai/gpt-oss-120b`, via Groq.
- **Data da execução:** 19/11/2026.

## 3. Método de validação

Cada objeto retornado passa pela função `validar_resposta`, que devolve a lista de problemas encontrados (vazia quando está tudo certo):

```python
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
```

As verificações estão em duas camadas:

**Camada 1: conformidade com o esquema Pydantic**

| # | Verificação | Como é feita |
|---|---|---|
| 1 | O retorno é uma instância de `RespostaAgente` | `isinstance(resposta, RespostaAgente)` |
| 2 | Não há campos ausentes | Comparação entre os campos de `RespostaAgente.model_fields` e as chaves de `model_dump()` |
| 3 | Todos os campos têm o tipo correto | `RespostaAgente.model_validate(dados, strict=True)`, no modo estrito, que não aceita conversões implícitas (por exemplo, um texto `"0.8"` no lugar de um número) |

**Camada 2: regras de negócio que o esquema não expressa**

O esquema declara apenas tipos (texto, texto e número), então um valor como `confianca = 1.5` ou `categoria_risco = "medio"` seria válido para o Pydantic, mas inútil para o painel. Por isso há três verificações adicionais:

| # | Verificação | Critério |
|---|---|---|
| 4 | Categoria reconhecida | `categoria_risco` ∈ {`baixo`, `médio`, `alto`} |
| 5 | Recomendação preenchida | `recomendacao` não vazia |
| 6 | Confiança em escala válida | 0,0 ≤ `confianca` ≤ 1,0 |

## 4. Resultados

### 4.1 Objetos retornados

| | Pergunta 1 | Pergunta 2 | Pergunta 3 |
|---|---|---|---|
| **Assinante** | 7,7 meses, 4,9 h/semana, 3 reclamações | 48 meses, 14 h/semana, 0 reclamações | 3 meses, 2 reclamações, **sem dado de uso semanal** |
| Tipo do retorno | `RespostaAgente` | `RespostaAgente` | `RespostaAgente` |
| `categoria_risco` | médio | baixo | alto |
| `confianca` | 0.85 | 0.9 | 0.62 |
| Tentativas necessárias | 1 | 2 | 8 |

Recomendações:

- **Pergunta 1:** "Entre em contato rapidamente para entender as reclamações e ofereça um benefício (ex.: desconto ou conteúdo exclusivo) para melhorar a experiência."
- **Pergunta 2:** "Envie um e‑mail de agradecimento destacando o tempo de assinatura e ofereça conteúdo exclusivo ou uma oferta de upgrade para reforçar o engajamento."
- **Pergunta 3:** "Envie um contato personalizado oferecendo um benefício (ex.: um mês gratuito ou desconto) e investigue os motivos das reclamações para melhorar a experiência."

### 4.2 Resultado da validação

| Verificação | Pergunta 1 | Pergunta 2 | Pergunta 3 |
|---|---|---|---|
| 1. Instância de `RespostaAgente` | OK | OK | OK |
| 2. Sem campos ausentes | OK | OK | OK |
| 3. Tipos corretos (modo estrito) | OK | OK | OK |
| 4. Categoria reconhecida | OK | OK | OK |
| 5. Recomendação preenchida | OK | OK | OK |
| 6. Confiança entre 0 e 1 | OK | OK | OK |

O script registrou **"Objetos válidos: 3 de 3"**: nenhuma das validações retornou problema para nenhum dos objetos.

## 5. Análise

- **Esquema respeitado:** os três objetos têm os três campos, com os tipos `str`, `str` e `float`, e passam também nas regras de negócio.
- **Coerência com os dados de entrada:** o risco acompanha o perfil descrito. O assinante com 3 reclamações e pouco uso recebeu risco médio, o de longa permanência, alto uso e nenhuma reclamação recebeu risco baixo, e o recém-chegado com reclamações recebeu risco alto. Essa leitura é consistente com a referência dada nas instruções (mais reclamações aumentam o risco; mais tempo de casa e mais uso o reduzem).
- **Confiança menor com dado faltante:** na pergunta 3, em que o uso semanal não foi informado, a confiança (0.62) ficou abaixo das outras duas (0.85 e 0.9), como as instruções pedem.

## 6. Limitações e pontos de atenção

- **A validação confere a forma, não a qualidade.** Ela garante que o painel receberá os campos certos, mas não que a recomendação seja a melhor ação nem que a categoria esteja correta para aquele assinante. Isso exigiria comparar com decisões reais da equipe de retenção.
- **`confianca` é uma estimativa declarada pelo modelo de linguagem**, e não uma probabilidade calibrada. Ela reflete o quanto o modelo considera que os dados da pergunta sustentam a análise, e não a taxa de acerto do modelo de churn do TP2 (AUC-ROC de 0,664).
- **Instabilidade do provedor.** A pergunta 3 precisou de 8 tentativas, o limite configurado, e foi bem-sucedida na última. O script não distingue, no contador, falhas de validação de JSON (400) de esperas por limite de tokens por minuto (429), então não é possível dizer quantas de cada tipo ocorreram. Esse resultado mostra que o tratamento de novas tentativas é necessário para a Groq, e também que a margem foi pequena. Não foi investigado se a ausência do dado de uso na pergunta 3 contribui para as falhas.
- **Uma única execução** está documentada, com três perguntas. Os valores de categoria, confiança e texto podem variar de uma execução para outra, já que o modelo não é determinístico.
- **O resultado da validação depende do modelo e do provedor.** Em outros cenários, o mesmo código poderia sinalizar problemas, por exemplo uma categoria sem acento ou uma confiança fora da escala. A função está preparada para reportar esses casos.

## 7. Conclusão

A combinação de saída estruturada e execução assíncrona funcionou: três perguntas sobre risco de churn foram processadas em paralelo e geraram três objetos `RespostaAgente`, todos validados nas duas camadas. Para o painel, isso significa que a resposta do agente pode ser consumida por código sem interpretação manual de texto livre, com a ressalva de que a conformidade da forma não substitui a avaliação da qualidade das recomendações.
