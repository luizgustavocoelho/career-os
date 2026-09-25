# IA: provider, fatos e custos

## Configuração

1. Crie uma chave em https://platform.openai.com/api-keys e configure faturamento/limites na sua conta de API.
2. No **`.env` da raiz**, defina `OPENAI_API_KEY`, `AI_MODEL` e `AI_DAILY_LIMIT`.
3. Reinicie API e worker. No Compose: `docker compose up -d --force-recreate api worker`.
4. No Career DNA, habilite consentimento e salve.
5. Em Configurações, confirme que o provedor está configurado. No Coach, envie uma pergunta simples sobre seus objetivos. Um 200 com texto e citações confirma a chamada; 401/403 do provedor, modelo inválido e outras falhas se tornam erro útil 502, sem exposição da chave.

O modelo padrão configurável é `gpt-4.1-mini`; não é uma promessa de disponibilidade para toda conta. Escolha um modelo com Responses/Structured Outputs habilitado para sua conta. Não há credencial padrão ou resposta de IA fictícia.

## Operações

`parse_resume`, `parse_job`, `analyze_match`, `generate_message`, `prepare_interview`, `career_coach` chamam uma fachada comum que verifica configuração, consentimento, cache e limite diário. O provider implementa `structured(instruction, context, schema)`; um novo provider deve implementar esse protocolo e satisfazer os mesmos contratos.

O SDK usa `client.responses.parse(..., text_format=Schema, store=False)`. Objetos retornados são validados por Pydantic com `extra=forbid`. Ausências são `null`, `unknown`, listas ou strings vazias. Prompts ficam em `app/ai/prompts/v1.txt`.

## Dados enviados

| Operação | Contexto enviado |
|---|---|
| Extração de currículo | Texto extraído do PDF, incluindo quaisquer dados pessoais contidos nele. Não envia o arquivo binário. |
| Parser de vaga | Descrição fornecida pelo usuário |
| Análise contextual | DNA profissional, skills/evidências, vaga, análise determinística e contexto relevante da candidatura |
| Mensagens e entrevista | Mesmo contexto da vaga, pedido/tipo de mensagem ou entrevista, histórico recente, notas e currículo vinculado |
| Coach | DNA/skills, pergunta, últimas 12 mensagens; quando vinculado a vaga, contexto daquela candidatura |

O contexto de coaching remove campos dedicados de telefone, e-mail e salário pessoal, mas **texto livre de currículo, notas, projetos ou evidências pode conter esses dados**. A pessoa deve revisar esses textos e consentir conscientemente. Nomes/funções dos contatos entram no contexto; e-mails/URLs de contato não são incluídos automaticamente. O limite de contexto serializado é 100 mil caracteres; há limites adicionais por seção. Nunca entram senhas, sessões ou chave da API.

`store=False` controla o armazenamento da resposta pela API; não promete ausência de processamento ou retenção operacional pelo provedor. Consulte as políticas e configurações da sua conta.

## Grounding

Fontes são rotuladas com IDs. Respostas de orientação precisam fornecer citações cujo `source_id` exista e cujo trecho esteja literalmente na fonte. Citação inventada é rejeitada antes da persistência como resposta concluída. Texto de vaga/currículo é dado não confiável, com instruções de prompt injection explicitamente ignoradas pelo sistema. Não são oferecidas ferramentas de envio ou execução ao modelo.

Essa validação impede referências fabricadas, **mas não constitui uma prova semântica de cada afirmação**. O modelo ainda pode interpretar mal uma fonte. A UI apresenta rascunhos revisáveis, nunca autoenvia nem autoaplica qualificações. Garantia matemática de “zero alucinação” não é alegada. Templates locais de mensagens e currículos copiam fatos cadastrados; preparação STAR local contém perguntas para preencher, não histórias inventadas.

## Custo e idempotência

Hash de tarefa + instrução + contexto + modelo + versão do prompt, sempre separado por usuário. Cache de chamadas concluídas, exclusão de duplicatas em andamento, reserva persistente antes da chamada, limite de 30 chamadas/dia por padrão. Falhas consomem tentativa do limite para evitar ciclos caros. Registro de tokens e chamadas dos últimos 30 dias na UI. Limite `max_output_tokens=6500` e timeout de 75 segundos, com uma repetição do SDK para falhas transitórias.

O limite diário é de chamadas, não de dinheiro. Configure também orçamento no provedor. O painel mostra tokens, não inventa valor monetário usando preços desatualizados. Cache e histórico contêm dados pessoais e entram na política de backup do usuário.

## Funcionamento sem IA

- PDF: texto real + detecção conservadora de nome, e-mail e vocabulário conhecido; formação/experiências são editáveis manualmente.
- Vaga: descrição real, detecção de termos conhecidos e identificação local de expressões como “desejável”; revisão obrigatória.
- Score: funções determinísticas em dez dimensões, sem cobrança de API.
- Mensagem: template preenchido por fatos cadastrados, identificado na timeline.
- Entrevista: roteiro por regras, perguntas e checklist específicos para os requisitos cadastrados.
- Coach e interpretação semântica: indisponibilidade explícita até configurar chave e consentimento.

## Referências da implementação

- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Responses API](https://developers.openai.com/api/reference/resources/responses/)
- [SDK Python oficial](https://github.com/openai/openai-python)


## Smoke manual

No diretório `backend`:

```powershell
..\.venv\Scripts\python.exe -m app.manage ai-smoke
```

Faz uma única chamada pequena com o modelo configurado, schema `{status: "ok"}`, `store=False`, timeout de 30 segundos e sem retries. Não envia DNA nem documentos, não imprime chave nem corpo de erro externo e não roda no CI. É uma operação administrativa com consumo separado das quotas de usuário do aplicativo. O teste desta entrega encontrou chave ausente; nenhuma chamada paga real foi validada. Contratos, citações e funcionamento sem IA foram testados.
