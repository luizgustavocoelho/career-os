# Deployment

## Estratégia

Uma VPS Linux com Docker Engine e Compose v2 mantém frontend, API, worker e PostgreSQL juntos. Caddy provê HTTPS. É uma arquitetura simples de operação: nenhum broker ou vector database pago. Escolha uma máquina de pelo menos 2 GB de RAM; o build do Next pode precisar de mais memória ou ser feito em CI. Não há preço fixo prometido: depende do provedor, região, backup e tráfego.

## Procedimento

1. Provisione a VPS, instale Docker Engine/Compose seguindo a documentação oficial da distribuição.
2. Configure DNS `A` para seu domínio e libere portas TCP 80/443. Restrinja SSH. Não exponha PostgreSQL.
3. Transfira o repositório (incluindo migrations e locks) e entre na raiz.
4. Copie `.env.example` para `.env` e configure:

```dotenv
POSTGRES_USER=careeros
POSTGRES_DB=careeros
POSTGRES_PASSWORD=<senha-aleatoria-alfanumerica-longa>
DOMAIN=carreira.seudominio.com
ACME_EMAIL=voce@seudominio.com
REGISTRATION_LIMIT=1
REGISTRATION_ENABLED=false
OPENAI_API_KEY=<sua-chave-se-quiser-ativar-IA>
AI_MODEL=gpt-4.1-mini
AI_DAILY_LIMIT=30
```

Não use os marcadores `<...>` literalmente. Senha alfanumérica evita a necessidade de URL-encoding na conexão montada pelo Compose. Mantenha `.env` legível somente por quem administra o servidor (`chmod 600 .env` no Linux).

5. Valide e suba:

```sh
docker compose -f compose.yaml -f compose.production.yaml config --quiet
docker compose -f compose.yaml -f compose.production.yaml up --build -d
docker compose -f compose.yaml -f compose.production.yaml ps
curl --fail https://carreira.seudominio.com/api/health
```

6. Prefira criar a conta localmente e migrá-la para PostgreSQL antes de abrir o domínio. Se optar por cadastro inicial em produção, restrinja acesso no firewall, abra temporariamente o cadastro e feche-o imediatamente depois.
7. Confira cadastro/login, upload, vaga manual, persistência após logout/login, worker, notificações e IA configurada.

O arquivo de produção força HTTPS/cookies Secure na API. O backend falha na inicialização em produção se banco não for PostgreSQL, origem não for HTTPS ou cookie Secure estiver desligado. O frontend só publica sua porta em loopback; o acesso externo passa por Caddy.

## Atualização

Faça backup. Atualize o código e execute novamente `up --build -d`. O serviço `migrate` roda antes de API/worker. Se estiver atualizando uma instalação já em execução, aplique explicitamente a migration da nova imagem:

```sh
docker compose build
docker compose run --rm migrate
docker compose -f compose.yaml -f compose.production.yaml up --build -d
```

Revise migrations incompatíveis antes de executá-las. Não use downgrade para tentar reverter código sem avaliar perda de dados. Restaure backup em ambiente separado para validar recuperação.

## Backup PostgreSQL

No Linux, na raiz do projeto, com o banco padrão:

```sh
mkdir -p backups
docker compose exec -T db pg_dump -U careeros -d careeros -Fc > backups/careeros-$(date +%Y%m%d-%H%M%S).dump
```

Armazene cópias criptografadas fora da VPS. O banco inclui PDFs, perfis, mensagens e histórico. Não publique a pasta de backup nem versione os arquivos.

Teste a restauração em **um banco novo**, preservando o original:

```sh
docker compose exec -T db createdb -U careeros careeros_restore_check
docker compose exec -T db pg_restore -U careeros -d careeros_restore_check < backups/ARQUIVO_ESCOLHIDO.dump
docker compose exec -T db psql -U careeros -d careeros_restore_check -c 'SELECT count(*) FROM users;'
```

Use o nome de um backup existente em `ARQUIVO_ESCOLHIDO.dump`. Planeje retenção e automatização no seu provedor. O aplicativo não cria um agendamento externo de backup por conta própria.

## Backup SQLite local

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.manage backup-sqlite ../data/backups/careeros-2026-09-16.db
```

A API de backup do SQLite gera uma cópia consistente mesmo com WAL. Para restaurar: encerre API e worker, preserve o banco atual e seus arquivos WAL/SHM em outro diretório, coloque a cópia em um novo caminho e configure `DATABASE_URL=sqlite:///./data/restaurado.db`; depois inicie novamente. Não misture arquivos WAL de bancos diferentes.

## Serviços separados

É possível usar PostgreSQL gerenciado e hospedar os dois containers em outra plataforma. Configure `DATABASE_URL` com TLS conforme o provedor, rode migrations como release command, mantenha worker e API com o mesmo banco e variáveis, e compile o frontend com `API_INTERNAL_URL` apontando à API. Cookies e CSRF dependem da origem pública correta. O caminho testável de referência é o Compose; configurações específicas de Vercel/Render/Neon não são alegadas como validadas nesta entrega.

## Preflight e validação

Antes de publicar: `scripts/check-production.ps1` (Windows) ou `sh scripts/check-production.sh` (Linux). O preflight consulta Compose sem imprimir configuração/segredos; valida domínio, senha, HTTPS, cookie Secure, cadastro fechado e portas privadas. Após subir a stack, use `-Live` / `--live` para verificar revisão Alembic no container e health HTTPS. O health da API exige a revisão atual, não apenas existência de uma tabela de versão.

Docker não está instalado nesta máquina; nenhum container ou certificado foi executado localmente. PostgreSQL 18 nativo isolado passou em migrations, smoke, worker, migração real e scheduler concorrente. CI inicial hospedada passou; resultado da branch de evolução consta em [VALIDATION.md](VALIDATION.md). Não há domínio/servidor contratado ou provisionado nesta entrega.

## Migrar SQLite para PostgreSQL

1. Pare API e worker em ambas as instalações. Faça backup SQLite e `pg_dump` do destino.
2. Aplique migrations até o mesmo head em ambos. Recomenda-se um PostgreSQL vazio, já migrado.
3. Defina `MIGRATION_TARGET_URL` no ambiente do processo com a conexão PostgreSQL (inclua TLS conforme o provedor). Não passe senha como argumento da linha de comando e não versione a variável.
4. Em `backend`, execute:

```powershell
..\.venv\Scripts\python.exe -m app.manage migrate-sqlite-to-postgres data/careeros.db --dry-run
..\.venv\Scripts\python.exe -m app.manage migrate-sqlite-to-postgres data/careeros.db --apply
```

O padrão sem flags é dry-run. As contagens por tabela são exibidas sem valores dos registros. Dry-run cria um snapshot consistente, valida schema/constraints, tenta a cópia numa transação e a reverte. `--apply` confirma tudo somente após verificação linha a linha; conflitos abortam a transação. Repetir imediatamente uma cópia idêntica não duplica registros. Uma instalação que já evoluiu separadamente pode gerar conflitos legítimos; não há sobrescrita/merge automático.

5. Aponte DATABASE_URL da instalação de destino para PostgreSQL, reinicie API/worker, faça login e confirme documentos, vagas e timeline. Preserve o SQLite original e seu backup até validar recuperação.

A ferramenta usa memória proporcional aos dados por tabela; foi projetada para instalação pessoal. Backups, snapshot temporário e banco de destino incluem autenticação e documentos; proteja o disco. O arquivo SQLite original é aberto em modo somente leitura.
