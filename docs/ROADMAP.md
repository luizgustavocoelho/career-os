# Roadmap

## Implementado em Personal Ready v1

Base funcional preservada: autenticação, Career DNA/evidências, documentos, score auditável, pipeline/timeline, mensagens/follow-ups, entrevistas, Coach opcional, gaps e analytics.

Evoluções: configuração absoluta, scripts locais com backup/diagnóstico, compartilhamento temporário, archive/restore/delete explícito, fontes e conversas gerenciáveis, documentos protegidos por referências, buscas salvas Jooble/ATS, scheduler persistente e backoff, dedupe/proveniência, dashboard por visita, diagnóstico, currículo selecionável DOCX/HTML, exportação ZIP, migração SQLite→PostgreSQL transacional e preflight.

## Dependências externas

- IA real requer OPENAI_API_KEY e acesso ao AI_MODEL escolhido. Smoke manual disponível; nenhuma chave configurada durante a validação.
- Busca Jooble real requer chave regional. Adapter/contratos e pipeline foram testados com fixtures; não se alega coleta externa autenticada.
- Docker é necessário para executar Compose; ausente nesta máquina. PostgreSQL nativo isolado foi validado.
- cloudflared é necessário para testar túnel HTTPS real; ausente nesta máquina. Fluxo de ausência e configuração por ambiente foram verificados.
- Servidor, domínio e DNS são necessários para produção. Nenhuma infraestrutura externa foi contratada.
- LibreOffice não está instalado para renderizar DOCX em QA. Estrutura OOXML/conteúdo são testados; diagramação em Word/LibreOffice ainda precisa de conferência. HTML para impressão não requer dependência no servidor.

## Evoluções futuras

- Adzuna com atribuição/licença conforme uso, paginação incremental maior dos ATS e outras APIs autorizadas.
- OCR, editor visual de currículo e PDF direto no servidor, caso uma dependência operacional robusta seja escolhida.
- Calendário mensal e integração opcional Google Calendar; notificações externas opt-in.
- Deduplicação assistida para anúncios ambíguos, sem unir oportunidades silenciosamente por título apenas.
- Agregações SQL e exportação streaming antes de volumes muito maiores. Hoje analytics/export/migração priorizam simplicidade para uso pessoal.
- MFA, recuperação de conta por e-mail, exclusão integral de conta e requisitos SaaS permanecem fora do escopo.

Não há candidatura, contato externo ou mensagem enviados automaticamente.
