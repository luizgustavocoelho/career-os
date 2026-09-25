# Registro de validação

Validações realizadas em 16–17/09/2026.

## Executado

- Duas migrations aplicadas em SQLite e PostgreSQL 18 reais; `alembic check` sem divergência em ambos.
- TypeScript validado com `tsc --noEmit`.
- Build otimizado Next.js concluído, com todas as rotas geradas.
- Testes Python de domínio/API/contratos/regressão em banco isolado: 29 aprovados.
- Verificação de isolamento entre duas contas, CSRF, origem, upload PDF real, cache/validação de IA, pipeline e worker.
- `npm audit` na instalação: zero vulnerabilidades reportadas.
- Smoke PostgreSQL 18 em cluster exclusivo na porta 55432: cadastro, vaga/score, pipeline, analytics e execução do worker aprovados.
- Concorrência PostgreSQL: duas tentativas de cadastro para uma única posição restante resultaram em 201 e 403, preservando o limite configurado.
- Sintaxe PowerShell e YAML de Compose/CI validadas.
- Lint do frontend sem erros ou warnings; Ruff sem erros e código formatado.

## Teste de navegador

Playwright com Chrome: **1 fluxo E2E aprovado**, usando frontend/backend reais e banco migrado isolado. Inclui criação de conta, edição do DNA, evidência, PDF real, extração e correção manual, importação por descrição, score, currículo vinculado, candidatura, mensagem editada/envio registrado, entrevista/roteiro, alteração no kanban, timeline, persistência após refresh, logout e novo login. Não houve erros JavaScript de página.

Screenshots desktop (1280 px) e mobile (390 px) foram inspecionados visualmente; dark mode e ausência de overflow horizontal em mobile foram verificados. Os arquivos locais ficam em `frontend/test-results/dashboard-desktop.png` e `dashboard-mobile.png` e mostram **somente fixtures do teste**, separadas do banco do usuário. Esses artefatos não são versionados.

## Não validado por dependência externa

- Chamada paga real da IA: não há credencial fornecida/configurada. O contrato usa provider substituído apenas em testes, e o caso sem chave é testado.
- Containers nesta máquina: Docker ausente. PostgreSQL nativo foi validado separadamente; execução dos containers e certificado Caddy ainda exigem ambiente com Docker e domínio. CI hospedada foi configurada, não executada remotamente.
- Publicação remota e certificado HTTPS: não há servidor/domínio configurado.

Warnings dos testes atuais: a versão instalada de Starlette informa depreciação do backend httpx de TestClient e do alias BlockingPortal de AnyIO. Não impedem os testes, mas devem ser acompanhados ao atualizar dependências.

## Continuação — 25/09/2026

Baseline antes da evolução: 29 testes backend, typecheck/lint frontend, build e 1 E2E aprovados. Build/E2E exigiram execução fora do sandbox devido a `spawn EPERM`. Após correção de configuração: 34 testes aprovados.

CI hospedada consultada na API oficial GitHub: workflow [35250649767](https://github.com/luizgustavocoelho/career-os/actions/runs/35250649767), commit `e47feb7`, concluído com sucesso em 17/09/2026. Esse resultado cobre o commit inicial, não as mudanças locais posteriores.
