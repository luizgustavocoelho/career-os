# Arquitetura

## Decisões

**ADR-001 — monólito modular.** FastAPI possui routers finos, schemas Pydantic, serviços de aplicação e funções de domínio independentes. Um processo worker compartilha modelos e serviços; não há microserviços, Redis ou Celery sem necessidade.

**ADR-002 — stack solicitada.** Next.js App Router, TypeScript, Tailwind 4, React Hook Form/Zod para autenticação e componentes acessíveis próprios. A lógica crítica é validada no backend. Os formulários de domínio usam estado tipado e schemas de servidor; não há validação crítica exclusiva no navegador. Fetch nativo e hook comum são suficientes para o tamanho atual; TanStack Query não é dependência obrigatória.

**ADR-003 — PostgreSQL em produção, SQLite local.** PostgreSQL é o destino de implantação e CI. SQLite com WAL e foreign keys permite abrir o app nesta máquina sem Docker instalado. As entidades e migrations são as mesmas; em SQLite use apenas um worker. Não há troca automática entre bancos nem descarte de dados para alternar ambiente.

**ADR-004 — agregados e relações.** Skills, evidências, requisitos, candidaturas, componentes do score, eventos, documentos e interações possuem tabelas relacionais. Experiências, formação, certificações, projetos e preferências pertencem ao agregado versionado do DNA em JSON validado. Não precisam de tabelas artificiais enquanto não possuem consultas/vidas independentes. Empresas são atributos das vagas nesta versão; enriquecimento compartilhado entre empresas será uma migração incremental.

**ADR-005 — sessão opaca.** Token aleatório em cookie HttpOnly e seu hash no banco. Sessões podem ser revogadas. CSRF dedicado e origem permitida para mutações. Evita tokens de longa duração no localStorage.

**ADR-006 — IA desacoplada.** Provider com protocolo `structured()`, fachada com operações de domínio, schemas Pydantic e prompt em arquivo versionado. Único ponto de chamada externa. Cache por usuário/modelo/prompt/contexto, reserva de orçamento antes da chamada e `store=False`.

**ADR-007 — score determinístico.** A IA interpreta ou explica; a nota final é calculada pelo domínio, armazena snapshot e componentes. Desconhecidos são explícitos. Sem embeddings nesta versão: evidências estruturadas e normalização resolvem o caso inicial; uma busca vetorial só será adicionada quando houver avaliação demonstrando benefício.

**ADR-008 — mesma origem.** Browser chama `/api`; Next encaminha para FastAPI. Evita exposição de credenciais de servidor e problemas de cookies entre domínios. A reescrita usa `API_INTERNAL_URL` no build; rebuild necessário se alterar o destino em produção.

## Limites das camadas

```text
Browser → Next.js → /api → FastAPI
                            ├─ autorização → serviços → domínio → SQLAlchemy → PostgreSQL
                            ├─ provider de IA → Responses API
                            └─ fila tasks → worker → adapters oficiais
```

As entidades privadas carregam `user_id`; cada leitura e mutação recebe o usuário autenticado. O backend nunca usa um usuário fixo. O cadastro limitado é configuração de produto, não bypass de autenticação.

## Concorrência e jobs

Perfil e candidatura usam comparação de versão, retornando 409 em conflito. A timeline é append-only pela API. Mudar estado e criar os eventos acontece na mesma transação. A fila usa lease de dez minutos renovado entre registros, `FOR UPDATE SKIP LOCKED` no PostgreSQL e até três tentativas. Jobs idempotentes usam dedupe de vaga/cache de análise; interrupção permite retomar. Buscas salvas optam por execução manual ou cadências de 12/24/48/168 horas. O scheduler persistente usa next_run_at, advisory lock PostgreSQL e Task.active_key único; SQLite requer um worker. Falhas usam available_at e backoff, inclusive Retry-After/quotas do provider. Contadores e checkpoints sobrevivem a reinício.

O recálculo é enfileirado ao alterar DNA, skills ou evidências; scores antigos ficam nulos até recálculo. A análise histórica permanece disponível para auditoria. O botão Recalcular também executa imediatamente.

## Escala

Índices em usuário, datas, chaves externas, skills, score e status; radar com paginação e limite de página. Kanban mostra até 60 registros por página e informa isso. Analytics do usuário agregam sua amostra em memória nesta versão; migração para agregações SQL/materializadas é indicada antes de dezenas de milhares de vagas por usuário. Documentos têm limite de 8 MB/40 páginas e são armazenados no banco para garantir posse e backup simples.


## Personal Ready v1

JobProvider continua atendendo boards Greenhouse/Lever; SearchJobProvider oferece busca ampla Jooble normalizada em JobData. Hosts são fixos, redirects proibidos e respostas limitadas a 5 MB. A fila original permanece; não há Redis/Celery.

Ingestão é serializada por proprietário no PostgreSQL. Fingerprint, URL canônica e identidade externa resolvem duplicatas exatas; título/empresa/local e descrição substancialmente igual resolvem algumas duplicatas entre providers. Proveniência permanece em jobs.provenance. Isso é conservador: anúncios ambíguos podem continuar separados.

Exports ZIP usam allowlist explícita por usuário. DOCX é OOXML de uma coluna produzido pela biblioteca padrão; HTML escapado permite impressão/PDF no navegador. Não exige Word/LibreOffice em produção. A seleção de fatos usa índices do DNA e valida sua versão antes de produzir o currículo.

Migração offline usa snapshot SQLite e uma transação PostgreSQL com locks de escrita nas tabelas. Dry-run insere dentro da transação para validar constraints e depois faz rollback; não altera o destino permanentemente. Não é uma sincronização entre bancos ativos.
