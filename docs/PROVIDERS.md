# Providers de oportunidades

Verificação documental: 25/09/2026. As consultas externas reais dependem de credencial do proprietário; não há chave Jooble configurada nesta instalação.

| Provider | Estado | Escopo |
|---|---|---|
| Greenhouse | Mantido | Boards públicos de empresas explicitamente cadastradas; até 500 vagas |
| Lever | Mantido | Boards públicos cadastrados; até 100 vagas |
| Jooble | Integrado | Busca oficial regional por termos/localização, duas páginas de 20 resultados por termo |
| Adzuna | Avaliado, não integrado nesta versão | API oficial disponível; alternativa futura com requisitos próprios de atribuição/licença |

## Jooble

Solicite a chave no [portal brasileiro](https://br.jooble.org/api/about), configure `JOOBLE_API_KEY` e `JOOBLE_REGION=br`. A chave é específica do domínio regional. Também há suporte aos hosts fixos de EUA (`us`) e Portugal (`pt`), com suas respectivas chaves. Reinicie API/worker e confira Configurações.

O adapter utiliza POST HTTPS, JSON, palavras-chave, localização e paginação. Não segue redirecionamentos, não busca páginas de terceiros e limita o corpo recebido. Há quotas persistentes por instalação e backoff para HTTP 429. Confirme os limites concedidos pelo provider à sua chave.

O retorno pode conter somente trecho da descrição. Salário em texto, tipo de contrato e data de atualização não viram automaticamente salário comparável, modalidade ou data de publicação. Requisitos são extraídos conservadoramente do trecho e precisam de revisão. Filtros de modalidade/senioridade/salário só excluem dados conhecidos incompatíveis; desconhecidos continuam para análise.

Referências oficiais: [conexão e chave regional](https://help.jooble.org/en/support/solutions/articles/60000922689-how-to-connect-to-the-jooble-rest-api), [campos e paginação](https://help.jooble.org/pt-PT/support/solutions/articles/60001448238-documenta%C3%A7%C3%A3o-da-jooble-rest-api). O uso depende da aprovação e dos termos do provider; o aplicativo não cria conta nem aceita contrato pelo proprietário.

## Adzuna

A [API oficial](https://developer.adzuna.com/overview) está disponível com app_id/app_key e busca paginada. Os [termos oficiais](https://developer.adzuna.com/docs/terms_of_service) admitem pesquisa pessoal e impõem atribuição, limites e condições para publicação/licenciamento. Priorizou-se Jooble nesta entrega para concentrar validação num adapter de busca ampla; isso não significa indisponibilidade técnica de Adzuna. Não foram adicionadas variáveis Adzuna sem implementação correspondente.

## Proveniência e limites

A vaga conserva provider/ID/URL e `provenance` quando unificada. Deduplicação combina fingerprint, URL canônica, identidade externa e comparação conservadora de título/empresa/local/descrição. Vagas parecidas sem evidência suficiente continuam distintas. Nenhum provider consulta LinkedIn, Indeed, Glassdoor ou Catho por scraping; para outras fontes, cole a descrição e guarde o link original.

Os testes utilizam respostas HTTP e providers de fixture somente em `backend/tests` e no servidor E2E isolado. O produto normal retorna falhas reais, sem fallback fictício.
