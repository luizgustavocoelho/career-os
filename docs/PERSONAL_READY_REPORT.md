# CareerOS Personal Ready v1 — relatório de entrega

25/09/2026. Branch: `astra/careeros-personal-ready`. Implementação local utilizável, com integrações externas dependentes das credenciais indicadas abaixo. Banco pessoal preservado.

## 1. Resumo das alterações

Evolução do projeto existente, mantendo Next.js, FastAPI, SQLAlchemy/Alembic, SQLite, PostgreSQL, Caddy e worker com fila persistida. Radar agendado, ciclo de vida dos registros, currículo factual, exportação e ferramentas de operação foram integrados à interface existente.

## 2. Bugs encontrados

Configuração dependente do diretório corrente; hostname temporário fixo no Next; ausência de controle de arquivamento/remoção; possibilidade de tarefas repetidas e de resultados duplicados entre fontes; perda de novidades na corrida entre leitura do dashboard e registro da visita; SQLite aberto durante limpeza de snapshot no Windows; health aceitando revisão de schema antiga; confirmação HTTP anterior ao commit.

## 3. Bugs corrigidos

Caminhos absolutos derivados da raiz, origens temporárias por ambiente, exclusões protegidas por propriedade/vínculos, chave ativa única/locks/lease e checkpoints de tarefas, deduplicação conservadora com proveniência, corte temporal do dashboard, fechamento explícito de conexões SQLite, comparação com Alembic head e commit antes de enviar resposta. Conflitos retornam erro em vez de falso sucesso.

## 4. Features implementadas

- Arquivar/restaurar vagas, exclusão permanente com confirmação; editar/desativar/remover fontes; remover documentos sem vínculos e renomear/remover conversas.
- Buscas salvas com termos, local, modalidades, senioridade, salário e providers; execução manual ou a cada 12/24/48/168 horas.
- Scheduler persistente, heartbeat, quotas, retry/backoff, retomada, importação/score e contagens reais de resultados.
- Dashboard de ações e diagnóstico privado de serviços/configuração.
- Seleção de experiências/projetos existentes, prévia e aprovação de currículo; exportação DOCX e HTML imprimível; ZIP dos dados pessoais.
- Backup consistente, migração transacional SQLite → PostgreSQL, smoke manual de IA e preflight de produção.

## 5. Migrations adicionadas

`c301_personal_lifecycle`: arquivamento, proveniência e fonte ativa. `c0c9f428dbf3`: buscas salvas, agendamento/identidade ativa de tarefas, heartbeat e visitas ao dashboard. Ambas aditivas, sem remoção de dados; downgrade destrutivo não é oferecido.

## 6. Novas variáveis de ambiente

`NEXT_ALLOWED_DEV_ORIGINS` (hostnames separados por vírgula), `JOOBLE_API_KEY`, `JOOBLE_REGION` (`br`, `us`, `pt`). A ferramenta de migração lê `MIGRATION_TARGET_URL` do ambiente do processo. Variáveis existentes de IA, origem, cookies, cadastro e PostgreSQL foram mantidas. Veja `.env.example`; nenhuma chave real foi versionada.

## 7. Providers implementados

Jooble para busca ampla oficial; Greenhouse e Lever mantidos para boards públicos cadastrados. Adzuna avaliado e documentado, sem implementação nesta versão. Não há scraping de portais restritos nem dados fictícios no produto.

## 8. Configuração de cada provider

Jooble: obtenha chave no portal regional, configure `JOOBLE_API_KEY` e `JOOBLE_REGION=br`, reinicie API/worker, crie busca no Radar. Greenhouse/Lever: cadastre o board da empresa em Configurações, habilite a fonte e selecione o provider na busca; não exigem chave para os boards públicos suportados. Requisitos, atribuição e limitações estão em [PROVIDERS.md](PROVIDERS.md).

## 9. Rodar localmente

Na raiz: `./scripts/start-local.ps1` (ou `-Install` para preparar dependências). Requisitos: Python 3.14, Node 24 e npm. Abra http://localhost:3000. O script verifica portas, faz backup, aplica migrations e inicia API/worker/frontend. Ctrl+C limpa seus processos; logs em `data/logs`. O banco existente continua em uso.

## 10. Compartilhar temporariamente

Instale `cloudflared`, depois execute `./scripts/start-share.ps1`. O script configura temporariamente a origem retornada, cookies Secure, hostname permitido e cadastro fechado. Preserve o terminal aberto. Não é deploy permanente. O `.env` original não é reescrito; configuração cloudflared existente não é apagada. Sem cloudflared, o script explica o pré-requisito.

## 11. Configurar IA

Defina `OPENAI_API_KEY`, confirme `AI_MODEL` disponível na sua conta e ajuste `AI_DAILY_LIMIT`. Em `backend`, execute `../.venv/Scripts/python.exe -m app.manage ai-smoke`. O smoke usa Structured Outputs sem dados pessoais, informa consumo e pode gerar custo da API. Nesta entrega nenhuma chamada paga foi feita: chave ausente. Career Coach requer essa credencial; operações determinísticas continuam funcionando.

## 12. Backup

Em `backend`: `../.venv/Scripts/python.exe -m app.manage backup-sqlite ../data/backups/meu-backup.db`. Escolha nome novo: backups existentes não são sobrescritos. Cópia consistente inclui WAL e passa por integridade/FKs. Backup pré-migração desta entrega: `data/backups/before-personal-ready-v1.db`. Procedimento PostgreSQL/restore em [DEPLOYMENT.md](DEPLOYMENT.md).

## 13. Migrar SQLite → PostgreSQL

Pare API/worker dos dois lados, faça backups e aplique migrations até o mesmo head. Defina `MIGRATION_TARGET_URL` no processo. Em `backend`, execute `../.venv/Scripts/python.exe -m app.manage migrate-sqlite-to-postgres data/careeros.db --dry-run`; revise contagens e repita com `--apply`. Dry-run é o padrão. IDs, datas, binários, vínculos e autenticação são preservados; conflito aborta tudo, sem sobrescrever. Depois configure DATABASE_URL do destino e valide login/documentos/histórico. Guia completo em [DEPLOYMENT.md](DEPLOYMENT.md).

## 14. Deploy

Prepare servidor com Docker/Compose e domínio apontado; configure senha PostgreSQL longa, domínio, e-mail ACME, origem HTTPS, cookies Secure e cadastro fechado. Execute `scripts/check-production.ps1` ou `sh scripts/check-production.sh`, siga os comandos de Compose/migrations em [DEPLOYMENT.md](DEPLOYMENT.md) e finalize com `-Live`/`--live`. API e banco permanecem privados. Não houve contratação ou publicação remota nesta entrega.

## 15. Testes executados

Pytest, Ruff, typecheck, ESLint, build Next, Playwright com frontend/API/worker reais, migrations e checks SQLite/PG, smoke e concorrência PG, portabilidade transacional, contratos Jooble, isolamento/CSRF, ZIP/DOCX/HTML, preflight por fixtures, inicialização Windows, preservação do SQLite pessoal e CI hospedada.

## 16. Resultados exatos

Backend: **56 passed, 2 warnings in 5.36s**. Ruff: **All checks passed**, **55 files already formatted**. TypeScript, ESLint e build: exit 0. E2E: **4 passed (48.5s)**, dois fluxos completos repetidos duas vezes. CI **success** em [36101889497](https://github.com/luizgustavocoelho/career-os/actions/runs/36101889497), commit `05252a7`, incluindo PostgreSQL 17 e Compose config. PostgreSQL 18: smoke/migrations/portabilidade/scheduler concorrente aprovados. SQLite pessoal: hashes/contagens preexistentes iguais; integridade aprovada. DOCX de QA: 22 parágrafos carregados por python-docx. Evidências e alcance em [VALIDATION.md](VALIDATION.md).

## 17. O que não foi possível testar

Jooble autenticado e OpenAI real: chaves ausentes. Túnel HTTPS: cloudflared ausente. Containers de aplicação/Caddy: Docker local ausente. DOCX paginado: LibreOffice ausente. Deploy real: sem infraestrutura/domínio. Esses itens não são classificados como execução real bem-sucedida.

## 18. Limitações restantes

Resultados Jooble podem ser trechos incompletos, sem salário estruturado/modalidade/senioridade; campos desconhecidos continuam para revisão. Busca limitada por páginas/quotas, sem garantia de cobertura integral. Scheduler depende do worker ligado. Deduplicação conservadora pode manter anúncios semelhantes separados. Migração/exportação usam memória proporcional ao volume pessoal. ZIP é exportação, não importador automático. Adzuna não implementado. Não há envio automático de candidaturas ou mensagens externas. DOCX/HTML exigem revisão humana antes de uso profissional.

## 19. Próximos passos recomendados

Configurar chaves Jooble/OpenAI no `.env` local (não no chat), conferir diagnóstico e executar uma busca/smoke reais; revisar currículo exportado em Word/LibreOffice. Para compartilhar, instalar cloudflared. Para produção, disponibilizar servidor/domínio, testar containers/HTTPS e restauração de backup. A revisão final é sua antes de enviar currículos ou mensagens.

## 20. Commits realizados

- `ff25084` — fix: stabilize local configuration and temporary sharing.
- `b08c67d` — feat: add archive and protected data lifecycle actions.
- `4a2afbf` — feat: add scheduled radar and portable personal workflows.
- `05252a7` — fix: commit database transactions before sending HTTP success.
- Commit de documentação: `docs: document Personal Ready validation and operating procedures` (contém este relatório).

## CAREEROS PERSONAL-READY

| Item | Estado | Evidência / ressalva |
|---|---|---|
| Local | OK | Inicialização e login disponíveis |
| Banco | OK | Backup e registros pessoais preservados |
| Migrations | OK | SQLite e PostgreSQL reais |
| Worker | OK | Execução, heartbeat e retomada testados |
| Radar | OK | Importação → score → arquivar/restaurar em E2E |
| Providers | OK | Contratos; Jooble real exige credencial |
| Scheduler | OK | Persistência e concorrência PG testadas |
| Score | OK | Regressões e fluxos reais locais |
| Pipeline | OK | Transições/timeline/persistência |
| Follow-ups | OK | Fluxo de candidatura validado |
| Interview Mission | OK | Roteiro/fluxo determinístico; IA real não exercitada |
| Career Coach | EXTERNAL CREDENTIAL REQUIRED | Contratos e gestão de conversas testados |
| Exportação | OK | ZIP/DOCX/HTML; paginação DOCX não validada visualmente |
| Migração SQLite → PostgreSQL | OK | Dry-run/apply/idempotência/conflitos em PG real |
| Frontend | OK | Typecheck/lint/build/E2E |
| Backend | OK | 56 testes, Ruff |
| PostgreSQL | OK | PostgreSQL 18 nativo isolado |
| Docker | NOT EXECUTED | Containers de aplicação não executados localmente |
| E2E | OK | 4 execuções aprovadas (2 fluxos × 2) |
| CI | OK | Workflow 36101889497 concluído com sucesso |
| Deploy | EXTERNAL INFRA REQUIRED | Procedimento e preflight entregues |
