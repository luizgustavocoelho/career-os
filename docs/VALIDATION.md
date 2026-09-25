# Validação — Personal Ready v1

Executada em 25/09/2026, com dados de teste separados do SQLite pessoal.

## Resultados locais

| Verificação | Resultado |
|---|---|
| Backend `pytest -q` | **56 passed, 2 warnings in 5.36s** |
| Ruff lint | All checks passed |
| Ruff format | 55 arquivos formatados corretamente |
| TypeScript | `tsc --noEmit` aprovado |
| ESLint | aprovado |
| Next.js produção | build concluído e rotas geradas |
| Playwright | **4 passed (48.5s)**: dois fluxos, cada um repetido duas vezes |
| SQLite | quatro migrations aplicadas; `alembic check` sem divergência |
| PostgreSQL 18 nativo isolado | migrations, `alembic check`, smoke de API/worker e concorrência de cadastro aprovados |
| Portabilidade em PostgreSQL real | dry-run revertido, apply, repetição idempotente, conflito rejeitado, UUID/datetime/binários/linhagem/histórico preservados |
| Scheduler concorrente PostgreSQL | dois workers: uma única execução concluída |
| DOCX | ZIP/XML válidos; python-docx abriu 22 parágrafos do documento de QA |
| HTML e ZIP pessoal | respostas/downloads verificados em API e E2E; isolamento por usuário e exclusão de credenciais testados |
| Inicialização PowerShell | API, worker e frontend iniciados; backup automático e limpeza dos filhos verificados |

O E2E original cobre conta, DNA, evidência, PDF, revisão manual, vaga, score, currículo, candidatura, mensagens, entrevista, kanban, timeline e persistência. O segundo cobre busca salva, fila/worker, importação automática, arquivar/restaurar, follow-up, currículo seletivo, DOCX, HTML, ZIP e Radar mobile. O provider substituto existe exclusivamente no servidor de testes.

Screenshots desktop/mobile foram inspecionados. O Radar foi ajustado para separar opções do formulário em telas estreitas. Artefatos em `frontend/test-results` contêm somente fixtures e não são versionados.

Uma repetição revelou resposta HTTP de sucesso antes do commit: a atualização seguinte podia ler estado anterior. A sessão de banco passou a usar `Depends(get_db, scope="function")`, conforme a [documentação FastAPI](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/). Regressões verificam commit antes dos headers e erro 409/rollback quando a confirmação falha. Não foi mascarado o problema com espera no navegador.

## Preservação do banco pessoal

Backup consistente em `data/backups/before-personal-ready-v1.db`, antes das migrations aditivas. Todas as colunas preexistentes foram comparadas por contagem e hash dos registros ordenados: **sem alteração dos dados preexistentes**. `quick_check` e `foreign_key_check` aprovados. Nenhum seed, reset ou downgrade foi executado. Cada início pelo script Windows também criou backup separado.

## CI hospedada

A branch `astra/careeros-personal-ready` foi publicada sem alterar `main`. Execução da implementação: [36101889497](https://github.com/luizgustavocoelho/career-os/actions/runs/36101889497), SHA `05252a7`. **Concluída com sucesso**, incluindo PostgreSQL 17, Compose config e os dois E2E.

O workflow executa lint/formatação/Pytest, PostgreSQL 17 em serviço isolado, migrations e testes de portabilidade/concorrência, validação Compose, typecheck/lint/build e Playwright. Não usa APIs pagas. O sucesso da [CI inicial](https://github.com/luizgustavocoelho/career-os/actions/runs/35250649767) em `e47feb7` é histórico e não foi usado como evidência das alterações atuais.

## Dependências externas e limites da validação

- OpenAI: smoke manual executado, encerrou com mensagem de chave ausente. Nenhuma chamada paga real; contratos, cache, falhas e ausência de chave testados.
- Jooble: adapter e HTTP 429/quotas/paginação/normalização testados com fixtures. Busca autenticada real depende de chave regional.
- Docker: ausente nesta máquina. PostgreSQL nativo foi exercitado; Compose config passou na CI hospedada. Build/start dos containers de aplicação e Caddy/HTTPS não foram executados localmente.
- cloudflared: ausente. Verificação de pré-requisito funcionou; túnel público e login via HTTPS temporário não foram exercitados.
- LibreOffice: ausente. DOCX validado estruturalmente; tentativa de renderização não pôde produzir páginas para inspeção. Paginação em Word/LibreOffice e impressão/PDF pelo usuário permanecem sem validação visual.
- Deploy: sem servidor/domínio configurados. Nenhuma infraestrutura foi contratada, provisionada ou publicada.
- Warnings: duas depreciações Starlette/httpx/AnyIO no backend; avisos NO_COLOR/FORCE_COLOR nos processos do navegador. Não impedem as verificações.
