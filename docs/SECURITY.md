# Segurança e privacidade

## Controles implementados

- Argon2id para senhas, mínimo de 12 caracteres; sem credenciais fixas.
- Sessões aleatórias opacas com hash no banco; cookie HttpOnly, SameSite=Lax, Secure obrigatório em produção, validade padrão de sete dias.
- CSRF por sessão em mutações e rejeição de origens não permitidas. CORS limitado a configurações explícitas.
- Limites persistentes de login por IP observado e e-mail; registro limitado e configurável. Na topologia com proxy sem headers confiáveis, IP observado é o proxy: o limite por e-mail continua individual e o limite por IP fica compartilhado.
- Limite de contas serializado por transação (advisory lock PostgreSQL / BEGIN IMMEDIATE SQLite), evitando ultrapassagem em cadastros concorrentes.
- Autorização por usuário para documentos, vagas, análises, conversas e todos os objetos privados; IDs alheios retornam 404.
- Validação Pydantic; statements parametrizados SQLAlchemy; React renderiza texto externo sem `dangerouslySetInnerHTML`.
- Links de interface aceitam somente http/https. Importação consulta apenas hosts fixos das APIs oficiais, sem redirects nem URLs arbitrárias.
- PDF validado por assinatura e parser, limite de bytes/páginas/texto; documentos baixados como attachment. Não executa scripts ou arquivos recebidos.
- Limites de corpo no proxy, aplicação e upload; erro global sem stack trace ao usuário, request ID e logs sem corpos de requisição ou segredos.
- `user_id` em todas as entidades privadas; backups contêm dados privados e precisam de proteção.
- Chave de IA somente no servidor; consentimento, minimização, cache e orçamento de chamadas.
- Containers executam API/worker/frontend como usuários sem root. PostgreSQL não expõe porta pública.

## Fronteiras

Single-user first não elimina isolamento; multiusuário está suportado no modelo e na autorização. Ainda não há MFA, recuperação de senha por e-mail, SSO, cobrança, papéis administrativos na UI ou tenant corporativo. O administrador local pode redefinir a senha com comando que exige acesso ao servidor. Antes de oferecer SaaS público, esses fluxos e monitoramento de abuso devem ser adicionados.

O limite da aplicação usa Content-Length e o upload limita a leitura; em produção Caddy limita o corpo recebido, inclusive transferências sem Content-Length. Não exponha diretamente a API à internet sem o proxy e seus limites. PDFs muito complexos ainda podem consumir CPU; a instalação inicial é pessoal. Adicione processamento isolado com quotas antes de aceitar uploads de usuários não confiáveis em escala.

A prevenção de prompt injection usa separação de instruções/contexto e ausência de ferramentas capazes de agir externamente. Isso reduz impacto, mas não garante que a IA nunca interprete conteúdo malicioso incorretamente. Citações são checadas; recomendações e rascunhos requerem revisão humana.

## Dados

Não há analytics de terceiros no código do produto nem envio automático do perfil ao provedor. O Next pode emitir telemetria da ferramenta durante desenvolvimento; os containers definem `NEXT_TELEMETRY_DISABLED=1`. O provedor de IA processa o contexto quando o usuário solicita uma operação com consentimento, conforme [AI.md](AI.md).

Dados no disco não recebem criptografia de aplicação. Use criptografia do dispositivo/volume, backup cifrado e TLS em produção. Restrinja acesso ao `.env`, banco e dumps. A exportação ZIP privada e exclusões por registro estão disponíveis. Exclusão integral de conta e políticas automatizadas de retenção permanecem no roadmap SaaS.

## Operação

Antes de publicar: HTTPS ativo, cadastros configurados, senha forte, segredo exclusivo no banco, backup testado, portas privadas, dependências verificadas e smoke do fluxo. Não registre `.env` ou dados pessoais no Git. `npm audit` e atualização de locks devem fazer parte da manutenção.


## Novas superfícies

Arquivamento, fontes, buscas, documentos e conversas mantêm ownership/CSRF. Jooble recebe somente os termos/localização da busca; sua chave regional permanece no backend, com URL omitida dos logs HTTP. ZIP usa nomes baseados em UUID e allowlist de tabelas, excluindo sessões, hashes de senha e configuração. Exports e backups contêm dados pessoais: mantenha-os fora do Git e proteja o dispositivo.

HTML exportado escapa conteúdo e não contém scripts. DOCX não contém macros, objetos ou relações externas. O túnel temporário exige autenticação normal, HTTPS/cookie Secure e cadastro fechado por padrão; expõe o servidor de desenvolvimento, não equivale a implantação de produção.
