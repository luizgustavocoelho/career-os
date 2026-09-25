# Setup local

## Windows

Python 3.14, Node.js 24, Git. Instale dependências e inicie com `scripts/start-local.ps1 -Install`; use sem `-Install` depois. O script não usa senha fixa, não cria dados de demonstração e não precisa de API key para o fluxo determinístico.

Se preferir executar manualmente, use três terminais a partir da raiz:

```powershell
python -m venv .venv
python -m pip --python .venv install -r backend/requirements.lock
Copy-Item .env.example .env
cd frontend
npm ci
```

API:

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Worker:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.worker
```

Frontend:

```powershell
cd frontend
npm run dev
```

Abra http://localhost:3000. A API de desenvolvimento está em http://localhost:8000/api/docs e o health em http://localhost:8000/api/health. Use sempre o mesmo hostname no navegador para manter a mesma sessão de cookie.

## Variáveis e diretórios

A API lê `.env` da raiz quando executada em `backend`. Caminhos SQLite são relativos ao diretório do backend. Compose sobrescreve `DATABASE_URL` com a conexão PostgreSQL, preservando o `.env` local.

`REGISTRATION_LIMIT=1` é o padrão. Para permitir mais contas voluntariamente, use `0` e reinicie. `REGISTRATION_ENABLED=false` fecha todos os novos cadastros. Para ambiente acessível remotamente, configure HTTPS e cookies Secure conforme o deploy.

## Problemas frequentes

| Sintoma | Ação |
|---|---|
| Banco indisponível ou migrations pendentes | Rode `alembic upgrade head` em backend e confira `DATABASE_URL` |
| Score pendente após editar perfil | Inicie o worker ou use Recalcular na vaga |
| Tarefa na fila | Confira `python -m app.worker` e logs; a UI atualiza enquanto há tarefas |
| IA não configurada | Preencha `OPENAI_API_KEY` no `.env` da raiz e reinicie API/worker |
| IA retorna 403 do app | Salve o consentimento no Career DNA |
| Falha validando IA | Confira modelo, chave, saldo da API e limite diário; a resposta externa não é simulada |
| PDF sem texto | Use versão pesquisável ou cole o texto em novo documento; não há OCR |
| URL não suportada | Cole a descrição e mantenha a URL original. Somente Greenhouse/Lever têm importação automática de vaga. |
| Perfil alterado em outra janela | Recarregue para obter a versão atual antes de salvar |
| Sessão inválida | Atualize a página ou entre novamente; o CSRF é renovado por sessão |
| Porta ocupada | Feche a instância anterior antes de executar outra. Não inicie scripts duplicados. |
| Next.js `spawn EPERM` em ambiente restrito | Execute o terminal fora da restrição de subprocessos ou autorize o comando na ferramenta que o está executando |

## Recuperar senha local

Somente um administrador com acesso ao servidor/banco deve executar:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.manage reset-password seu-email@example.com
```

A senha é solicitada sem eco, ganha hash Argon2id e todas as sessões daquela conta são revogadas. Não existe endpoint de recuperação sem autenticação nem senha universal.

## Linux/macOS

O script `bash scripts/start-local.sh` prepara o venv, instala os locks, migra o banco e inicia os três processos. Ou substitua os executáveis Windows por `.venv/bin/python` nos comandos acima. Para E2E, rode `npx playwright install --with-deps chromium` dentro de frontend.

## Compartilhamento temporário

Instale `cloudflared` (`winget install --id Cloudflare.cloudflared`) e crie sua conta no modo local primeiro. Encerre a instância local e execute `scripts/start-share.ps1`. O script mostra uma URL HTTPS temporária, fecha cadastros, usa cookie Secure e configura o hostname exato do Next. As variáveis valem somente para os processos filhos; `.env` não é editado. Ctrl+C encerra os serviços/túnel. Depois use `scripts/start-local.ps1` para voltar a localhost.

Quick Tunnels não são produção: sem SLA, limite de 200 requisições simultâneas, sem SSE, URL muda a cada execução; exige ausência de `~/.cloudflared/config.yml`/`config.yaml`. Não publica banco nem porta da API. Referência: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/

A configuração Python localiza sempre o `.env` da raiz pelo caminho do código. Caminhos SQLite e DATA_DIR relativos são resolvidos a partir de `backend/`, inclusive ao iniciar de outro diretório. Variáveis de processo prevalecem. O script local aplica origem localhost e cookie sem Secure somente durante sua execução. `NEXT_ALLOWED_DEV_ORIGINS` recebe hostnames separados por vírgula, sem protocolo.

Cada inicialização Windows faz backup SQLite consistente antes de migrations; cópias ficam em `data/backups`. Logs de cada execução ficam em `data/logs/<data-hora>`. Portas ocupadas e pré-requisitos ausentes interrompem o script sem encerrar processos existentes.
