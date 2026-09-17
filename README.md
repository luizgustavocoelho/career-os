# CareerOS

Um sistema pessoal de busca profissional: Career DNA, evidências, radar de oportunidades, score auditável, candidaturas, follow-ups, entrevistas, documentos e Career Coach. A aplicação inicia vazia e persiste dados reais. Não há seed na execução normal.

## Executar no Windows

Requisitos: Python 3.14, Node.js 24 e npm. Na raiz:

```powershell
.\scripts\start-local.ps1 -Install
```

Nos próximos acessos:

```powershell
.\scripts\start-local.ps1
```

Abra **http://localhost:3000**. A primeira pessoa cria sua própria conta; não há senha padrão. Por padrão, novos cadastros fecham após a primeira conta. `Ctrl+C` encerra os serviços iniciados pelo script. O banco local fica em `backend/data/careeros.db` e sobrevive ao fechamento do navegador e reinícios.

No Linux/macOS: `bash scripts/start-local.sh`.

## Executar com PostgreSQL e Docker

```powershell
Copy-Item .env.example .env
```

Defina uma senha alfanumérica longa em `POSTGRES_PASSWORD` no `.env`, então:

```sh
docker compose up --build -d
```

Abra http://localhost:3000. O Compose inicia PostgreSQL, aplica migrations, inicia API, worker e frontend. O volume `postgres_data` preserva o banco. Não execute `down -v` se quiser manter seus dados.

## Primeiro uso

1. Crie a conta e preencha o Career DNA, objetivos, experiências e projetos.
2. Envie seu currículo em **Documentos**. Revise a extração antes de aplicá-la ao DNA. A extração local encontra nome/e-mail e termos conhecidos; a extração semântica usa a IA configurada.
3. Cadastre skills e associe evidências reais a elas.
4. Adicione uma vaga por texto, cadastro manual ou URL pública Greenhouse/Lever. Revise os requisitos e salve.
5. Consulte score, cobertura dos dados, requisitos, gaps e fontes de evidência.
6. Prepare uma mensagem e uma versão textual do currículo. Registre quando tiver enviado a candidatura.
7. Acompanhe o pipeline e follow-ups. Agende entrevistas, prepare o roteiro e registre feedback.
8. Use Career Gap e Analytics para observar sua própria amostra de oportunidades.

## Ativar IA

O gerenciamento de vagas, score, documentos, mensagens por template e roteiro de entrevistas funcionam sem API paga. **Career Coach e interpretação semântica dependem de uma chave real.**

Crie uma chave em [OpenAI API Keys](https://platform.openai.com/api-keys). Preencha `OPENAI_API_KEY` no `.env` **da raiz** e escolha um `AI_MODEL` compatível com Responses e Structured Outputs. Reinicie API e worker. No Career DNA, autorize o envio de contexto. Em Configurações, confira o status; no Coach, faça uma pergunta. A assinatura do ChatGPT não é uma chave de API para este aplicativo.

Sem chave, o backend retorna 503 nas operações de IA. Não inventa respostas externas. Veja [contexto enviado, limites e validação](docs/AI.md).

## Estrutura

```text
frontend/             Next.js, TypeScript, Tailwind, componentes e E2E
backend/app/api/      HTTP e autorização
backend/app/domain/   score, skills, parsers, pipeline
backend/app/services/ casos de uso, contexto e analytics
backend/app/ai/       provider, schemas e prompts versionados
backend/app/integrations/ APIs públicas de vagas e GitHub
backend/app/worker.py fila persistente de tarefas
backend/migrations/  migrations Alembic versionadas
backend/tests/       domínio, API, contratos, regressões
docs/                produto, arquitetura, operação e limites
infra/               HTTPS com Caddy
scripts/             inicialização local
```

## Verificar

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m ruff check app tests
..\.venv\Scripts\python.exe -m ruff format --check app tests migrations
..\.venv\Scripts\python.exe -m alembic check
cd ../frontend
npm run typecheck
npm run lint
npm run build
npm run test:e2e
```

O E2E usa banco descartável separado e portas 3011/8011. No Windows usa Chrome instalado; no Linux instale o navegador com `npx playwright install --with-deps chromium`. As chamadas de IA são substituídas **apenas nos testes de contrato**, nunca no aplicativo.

## Documentação e estado

- [Produto e critérios](docs/PRODUCT.md)
- [Arquitetura e decisões](docs/ARCHITECTURE.md)
- [Banco e migrations](docs/DATABASE.md)
- [IA e privacidade](docs/AI.md)
- [Setup e solução de problemas](docs/SETUP.md)
- [Deploy, backup e restauração](docs/DEPLOYMENT.md)
- [Segurança](docs/SECURITY.md)
- [Roadmap e limitações explícitas](docs/ROADMAP.md)
- [Validação realizada](docs/VALIDATION.md)

Não há implantação em conta externa nem integração OAuth configurada por padrão. O caminho de produção usa PostgreSQL e HTTPS. Os dados SQLite locais não migram automaticamente para o banco do Compose.
