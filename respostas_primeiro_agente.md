# Respostas do primeiro agente (política de cancelamento da NeoStream)

## 1. Configuração da execução

| Item | Valor |
|---|---|
| Script | `primeiro_agente.py` |
| Primitivos do SDK | `Agent` (com `instructions`) e `Runner.run_sync(...)` |
| Ferramentas externas | Nenhuma |
| Provedor | Groq, por meio da API compatível com a da OpenAI (`https://api.groq.com/openai/v1`) |
| Modelo | `openai/gpt-oss-120b` |
| Data da execução | 19/11/2026 |

O modelo inicialmente previsto, `llama-3.3-70b-versatile`, retornou erro 404 porque a Groq o desativou em 16/08/2026 para contas gratuitas e developer. Ele foi substituído pelo `openai/gpt-oss-120b`, o substituto indicado pela própria Groq. A troca exigiu apenas alterar a variável `GROQ_MODEL` no `.env`, sem mudança no código.

## 2. Papel definido nas instruções do agente

As instruções do `Agent` estabelecem que ele:

- é o **assistente de política de cancelamento da NeoStream**, um serviço de streaming por assinatura, e responde em português do Brasil a perguntas gerais de assinantes sobre cancelamento;
- responde de forma clara, cordial e objetiva, em **no máximo quatro frases**;
- **não tem acesso** ao texto oficial da política nem aos dados de assinantes, e por isso **não inventa** prazos, valores, multas, regras de reembolso nem passos específicos de telas ou botões;
- quando falta um detalhe, **diz isso com transparência**, explica o que costuma ser relevante e orienta o assinante a confirmar nos canais oficiais;
- responde **apenas** sobre cancelamento de assinatura.

## 3. Perguntas e respostas obtidas

As três perguntas foram executadas em sequência com `Runner.run_sync(...)`.

### Pergunta 1

> Como faço para cancelar minha assinatura da NeoStream?

**Resposta:**

> Para cancelar a assinatura, normalmente você precisa acessar a sua conta e procurar a seção de “Assinatura” ou “Planos”. Lá costuma haver a opção de encerrar ou solicitar o cancelamento. Como não tenho acesso ao procedimento exato da NeoStream, recomendo confirmar o passo a passo no site ou app oficial ou entrar em contato com o suporte ao cliente. Eles poderão orientá‑lo(a) detalhadamente e garantir que o cancelamento seja concluído corretamente.

### Pergunta 2

> Se eu cancelar no meio do mês, serei reembolsado pelos dias que não usei?

**Resposta:**

> Não tenho acesso ao texto oficial da política de reembolso da NeoStream, portanto não posso confirmar se há devolução pelos dias não utilizados. Normalmente, esse tipo de detalhe depende do plano contratado, da data exata do cancelamento e das condições específicas da assinatura. Recomendo que você verifique essa informação nos canais oficiais da NeoStream, como o site, o app ou o atendimento ao cliente. Assim você terá a confirmação precisa sobre eventuais valores a serem devolvidos.

### Pergunta 3

> Depois de cancelar, posso reativar minha assinatura mais tarde?

**Resposta:**

> Sim, geralmente é possível reativar a assinatura depois de cancelá‑la, porém os detalhes (como prazo para reativação sem perda de benefícios ou necessidade de um novo plano) podem variar. Normalmente basta acessar sua conta e escolher a opção de retomar o plano, mas pode haver restrições dependendo do momento do cancelamento. Como não tenho acesso à política específica da NeoStream, recomendo confirmar essas condições nos nossos canais oficiais de suporte ou no site. Estou à disposição para esclarecer outras dúvidas sobre cancelamento.

## 4. Análise das respostas

### O que o agente cumpriu

- **Papel e escopo:** as três respostas tratam apenas de cancelamento de assinatura, em tom cordial e em português do Brasil, como definido nas instruções.
- **Limite de tamanho:** cada resposta tem exatamente quatro frases, dentro do máximo estabelecido.
- **Transparência sobre o que não sabe:** nas três respostas o agente declara que não tem acesso ao procedimento ou à política oficial da NeoStream e orienta a confirmar nos canais oficiais. Na pergunta 2, a mais sensível por envolver dinheiro, ele se recusa a confirmar o reembolso e lista de que fatores a resposta costuma depender.
- **Sem dados inventados:** nenhuma resposta apresenta prazo, valor, multa ou condição específica como se fosse regra da NeoStream.

### Pontos de atenção

- **Pergunta 1:** o agente cita as seções “Assinatura” ou “Planos” como lugar provável do cancelamento. Embora a frase venha com “normalmente” e seja seguida do aviso de que ele não conhece o procedimento exato, é uma descrição de tela que o agente não tem como saber. A instrução proíbe passos específicos de telas, e esta resposta chega perto desse limite.
- **Pergunta 3:** a resposta abre com “Sim”, o que pode ser lido como confirmação de uma regra. O restante do texto qualifica a afirmação (“geralmente”, “podem variar”, “pode haver restrições”) e remete aos canais oficiais, mas a abertura é mais categórica do que o agente poderia sustentar sem a política em mãos. Esta resposta também usa “nossos canais”, falando como se fosse a própria empresa.
- **Causa dos pontos de atenção:** o agente não tem acesso à política real nem a ferramentas, então responde com conhecimento genérico sobre serviços de assinatura. Isso é esperado nesta prova de conceito.

### Conclusão

O fluxo mínimo de criação e execução de um agente foi validado: o `Agent` com instruções definiu o papel e as regras de comportamento, e o `Runner.run_sync(...)` executou três perguntas diferentes e devolveu respostas coerentes com essas regras. A limitação principal é a ausência de uma fonte confiável de informação, que só seria resolvida com a política oficial no contexto do agente ou com ferramentas de consulta, o que está fora do escopo deste exercício. A saída em texto livre também motiva o próximo passo, a saída estruturada do Exercício 5.
