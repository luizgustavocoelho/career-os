# Banco de dados

## Modelo

| Tabela | Papel |
|---|---|
| users | Identidade e hash Argon2id |
| sessions | Hash do token opaco, CSRF, validade e proprietário |
| rate_limits | Contadores de autenticação, chave hash e janela |
| profiles | Career DNA JSON validado e versão de concorrência |
| profile_skills | Skill canônica única por usuário, categoria, nível e recência |
| evidence | Fonte, descrição, URL e confiança associadas à skill |
| documents | PDF original ou texto, extração e vínculo à versão anterior |
| job_sources | Provider/board do usuário e última sincronização |
| jobs | Vaga, fonte, URL canônica, fingerprint, campos filtráveis e interpretação estruturada |
| job_requirements | Skills da vaga, obrigatoriedade e trecho de origem |
| match_analyses | Snapshots imutáveis, score, versão do algoritmo e resultado |
| match_components | Dimensão, peso, valor e explicação de cada análise |
| applications | Uma candidatura por usuário/vaga, status, versão e currículo |
| application_events | Eventos de descoberta, análise, estados, mensagens, entrevistas e acompanhamento |
| notes / contacts | Anotações e recrutadores associados à candidatura |
| message_drafts | Rascunhos editáveis até registro manual do envio |
| follow_ups | Data, estado, conclusão e candidatura |
| interviews | Agenda, notas, feedback, preparação e checklist |
| ai_conversations / ai_messages | Histórico isolado por usuário e contexto |
| ai_usage | Modelo, prompt, timestamp, cache, estado e tokens |
| tasks | Payload, lease, tentativas, resultado e falha da execução assíncrona |
| notifications | Notificações internas deduplicadas e confirmação de leitura |

IDs UUID, datas UTC (serializadas com `Z`), relações por foreign keys e índices. Salário inclui moeda e período no JSON validado; valores numéricos da faixa também ficam em colunas para filtros. Não há conversão monetária implícita.

## Migrations

Execute no diretório `backend`, com ambiente Python ativo:

```sh
alembic upgrade head
alembic check
```

Nova mudança de schema:

```sh
alembic revision --autogenerate -m descricao_da_mudanca
# Revise a migration gerada antes de executá-la.
alembic upgrade head
```

A migration inicial contém DDL explícito versionado, sem `create_all()` na inicialização de produção. `create_all()` só aparece nas fixtures isoladas de testes. Reversões removem dados das tabelas afetadas: restaure um backup em outro banco e valide antes de qualquer rollback destrutivo.

## Histórico e consistência

Alterações de status guardam `from`, `to` e motivo informado. O score mantém inputs e hash, permitindo comparar versões sem sobrescrever o passado. Edição de vaga produz novo evento e nova análise quando inputs mudam. Resultados iguais à análise atual são reutilizados; restaurar inputs históricos cria uma nova posição na timeline, preservando a análise correta como atual.

Deduplicação usa usuário + fingerprint de empresa/título/local/descrição normalizados; também consulta URL sem parâmetros de rastreamento e fonte/ID externo. URLs e IDs externos são índices lógicos na camada de serviço; importações de uma mesma fonte são serializadas pelo worker. Republicações com mudanças substanciais podem ser consideradas novas vagas.

## Backups e ambientes

SQLite local: `backend/data/careeros.db`. PostgreSQL do Compose: volume `postgres_data`. Testes de navegador: bancos `backend/data/e2e-<uuid>.db` independentes. Testes unitários: SQLite em memória. CI de integração: PostgreSQL `careeros_test` descartável.

Não reutilize o `.env` de produção em testes. Veja o procedimento de backup e restauração em [DEPLOYMENT.md](DEPLOYMENT.md).


## Migrations Personal Ready v1

- `c301_personal_lifecycle`: `jobs.archived_at`, `jobs.provenance`, `job_sources.enabled` com valores iniciais compatíveis. Nenhuma linha existente é removida.
- `c0c9f428dbf3`: `saved_job_searches`, `worker_heartbeats`, `dashboard_visits`; `tasks.available_at` e índice único anulável `active_key`.

As novas migrations recusam downgrade destrutivo. Restaure um backup em outro banco para avaliar reversão. Foram verificadas em SQLite e PostgreSQL 18; a cópia pessoal local recebeu backup antes de atualização e todos os valores das colunas preexistentes foram comparados por hash e contagem.

Arquivar registra evento e preserva analytics/timeline. Excluir uma vaga exige arquivamento anterior e confirmação do ID; remove sua candidatura e dependências. Documentos usados em candidatura ou com descendentes não podem ser excluídos. Remover uma busca/fonte preserva as vagas já coletadas.

`migrate-sqlite-to-postgres` preserva UUIDs, datas, JSON, bytes e FKs, incluindo hashes de senha necessários ao login. Isso difere da exportação do usuário, que exclui material de autenticação. A repetição aceita linhas idênticas e rejeita diferenças ou colisões únicas sem sobrescrever dados. Pare as aplicações/worker de origem e destino; não use para mesclar instalações divergentes.
