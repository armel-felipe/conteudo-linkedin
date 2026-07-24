# Contrato operacional

- Nunca inclua credenciais, tokens ou chaves de API em chat, arquivos versionados,
  Markdown editorial, banco de dados ou commits. Use exclusivamente o `.env` local.
- Antes de agendar qualquer publicação, obtenha confirmação explícita do usuário.
- Antes de publicar qualquer conteúdo, obtenha confirmação explícita do usuário.
- Use `./contentctl` como interface operacional única.
- Pesquisa recente deve ser capturada somente pelo `LAST30DAYS_COMMAND` configurado;
  preserve seu stdout verbatim e não sintetize pesquisa internamente.
- Ideias e rascunhos só podem usar pilares explicitamente aprovados.
