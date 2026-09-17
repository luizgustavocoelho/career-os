# Roadmap

## Implementado no produto atual

Fundação persistente e integrada, autenticação, Career DNA editável, evidências, upload/extrator de PDF, importação manual/texto/ATS, score determinístico auditável, workspace, pipeline e timeline, mensagens e follow-ups, entrevistas e preparação, Coach com provider real configurável, documentos/versionamento, analytics, gaps, notificações internas, GitHub público sob consulta explícita, worker durável, migrations, containers, CI e testes.

## Configuração externa necessária

- Chave e faturamento da API para Career Coach e interpretação semântica. Não foi fornecida uma chave para testar chamadas reais nesta sessão.
- Docker para executar os containers neste computador. PostgreSQL 18 nativo e SQLite já foram validados; Compose ainda precisa de teste de execução.
- Servidor/domínio e acesso ao provedor para publicar online. Nenhuma conta externa foi criada ou configurada automaticamente.
- Publicação do repositório para executar CI hospedada. Não existe remote Git configurado por suposição.

## Limites conhecidos e evolução incremental

- Parser local de currículo é conservador: extrai texto, nome provável, e-mail e skills conhecidas. A organização semântica completa exige IA e revisão. Não há OCR de PDFs digitalizados.
- Currículo contextual é uma versão de texto fiel aos campos do DNA, com skills relevantes priorizadas. Exportação PDF/DOCX diagramada e editor visual de currículo são incrementos futuros.
- Importação automática somente Greenhouse/Lever; outras plataformas usam colagem/manual. Cada sincronização atual limita Greenhouse a 500 vagas e Lever a 100. Empresas com mais vagas exigem paginação incremental do adapter. Sem scraping autenticado.
- GitHub consulta metadados, linguagens e README de um repositório público indicado. A confirmação e associação como evidência são feitas pelo usuário. Repositórios privados/OAuth não estão implementados.
- Skill matching usa aliases explícitos, declaração, desenvolvimento e evidência. Análise semântica está disponível como explicação complementar; equivalências semânticas não são aceitas silenciosamente como prova.
- Etapas são centralizadas no domínio. Personalização da sequência/nomes pela UI é evolução futura; não exige reescrever o histórico de eventos.
- Agenda mostra próximas dez entrevistas. O workspace conserva entrevistas anteriores e seus feedbacks; calendário mensal e sincronização Google Calendar ficam para depois.
- Analytics calculam frequências e transições do histórico; testes A/B, causalidade, benchmarking e dados externos agregados não são produzidos.
- Agendamento periódico de coleta, notificações por e-mail e push, OAuth Gmail/LinkedIn e envio automático não estão implementados.
- PostgreSQL nativo passou em migrations, smoke e teste concorrente. CI hospedada e execução em containers ainda precisam ocorrer no ambiente de implantação.
- Antes de abrir como SaaS: MFA/recuperação de conta, exclusão/exportação, auditoria de dependências contínua, quotas por conta, agregações SQL de analytics, processamento PDF isolado e testes de concorrência maiores.

Nenhuma dessas evoluções usa telas falsas ou respostas externas simuladas. O código atual é a base mantida, sem camada de demonstração descartável.
