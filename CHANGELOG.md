# Changelog

## 1.1.0 — Personal Ready v1 — 2026-09-25

- Corrigidos caminhos de configuração/SQLite independentes do diretório, URL temporária fixa no Next e fechamento de conexões no backup/migração Windows.
- Inicialização local com pré-requisitos, backup antes de migrations, readiness, logs e limpeza dos processos criados. Modo Share configura origem/cookies/cadastro sem editar .env.
- Arquivamento/restauração de vagas, exclusão explícita, fontes ativáveis/editáveis, proteção de documentos e gerenciamento de conversas.
- API regional Jooble, buscas salvas, scheduler persistente, quotas/backoff, recuperação e deduplicação/proveniência.
- Dashboard por visita, diagnóstico privado e health que detecta migrations pendentes.
- Seleção de fatos do DNA, prévia/versionamento de currículo e exportação DOCX/HTML; exportação privada ZIP.
- Migração SQLite→PostgreSQL com dry-run, rollback, conflitos, repetição idempotente e verificação dos registros.
- Smoke manual IA, preflight produção e testes adicionais de segurança, E2E, PostgreSQL e concorrência.

- Corrigida corrida de leitura após escrita: confirmação da transação antes da resposta HTTP, com erro/rollback em conflitos.

## 1.0.0 — 2026-09-16

- Estrutura inicial Next.js + FastAPI com PostgreSQL em Compose e modo local SQLite.
- Autenticação, sessão opaca, CSRF, rate limit e isolamento de dados.
- Career DNA, skills/evidências, documentos e extração revisável de currículo.
- Radar com adapters Greenhouse/Lever, filtros, deduplicação e interpretação de vaga.
- Opportunity Score com dez dimensões, snapshot e componentes persistidos.
- Candidaturas, timeline, kanban, mensagens, contatos, follow-ups e entrevistas.
- Career Coach e tarefas de IA por provider configurável, consentimento, schema, cache e limite de chamadas.
- Dashboard, gaps, analytics, notificações e consulta GitHub público.
- Worker persistente, migrations, testes de domínio/integração/E2E e configuração de CI.
- Scripts locais, containers, HTTPS, backup, recuperação administrativa de senha e documentação operacional.
