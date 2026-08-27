# Contrato operacional

- Nunca inclua credenciais, tokens ou chaves de API em chat, arquivos versionados,
  Markdown editorial, banco de dados ou commits. Use exclusivamente o `.env` local.
- O conteúdo só chega a `content/approved/` após a aprovação explícita da pessoa (filtros do
  pipeline + revisão pessoal). Publicar/agendar a partir de `content/approved/` **não** exige
  nova confirmação textual.
- Use `./contentctl` como interface operacional única.
- Pesquisa recente deve ser capturada somente pelo `LAST30DAYS_COMMAND` configurado;
  preserve seu stdout verbatim e não sintetize pesquisa internamente.
- Ideias e rascunhos só podem usar pilares explicitamente aprovados.
- O fluxo de publicação corporativa via Zernio está **depreciado**: não haverá contas
  corporativas em rede social. Comandos que dependem de `ZERNIO_*` (history import, posts sync,
  schedule, report weekly) estão fora do uso.
- O pipeline de produção de conteúdo é **local** (pesquisa → ideia → draft → revisão → aprovação)
  e não depende de Zernio.
- O destino do conteúdo aprovado (`content/approved/`) é a **publicação assistida no LinkedIn**
  via skill de navegação (browser do OpenWork já logado, sem credenciais). Ver `docs/roadmap.md`.
- Na publicação via skill: o texto em `content/approved/` já passou pelos filtros do pipeline e
  **não precisa** de nova confirmação textual. O único ponto de espera é o envio "agora", para
  permitir anexar imagem manualmente antes do clique final; em agendamento (dia/horário) a
  validação ocorre no próprio LinkedIn antes do disparo.
- Anexar imagem automaticamente na postagem é um item de **roadmap futuro** (ver
  `docs/roadmap.md`); hoje o anexo é manual e só no envio "agora".
- Ao capturar pesquisa no LinkedIn (busca de conteúdo), registre o **link individual de cada
  postagem** (formato `/feed/update/urn:li:activity:...`), não apenas o link do perfil/empresa.
  O link do post é mais importante que qualquer outro link para citação e rastreio. Capture-o
  abrindo cada post individual (clicar no timestamp/abrir a atividade) e registrando a URL
  resultante na barra de endereço, já no momento da coleta — não deixe para depois, pois a
  resultante na barra de endereço, já no momento da coleta — não deixe para depois, pois a
  listagem de busca não expõe a URL do post no DOM. (Decisão de 26/08/2026.)
- Todo arquivo em `content/approved/` deve trazer uma seção **`## Fontes`** ao final, sempre abaixo
  do texto, com o link de cada postagem de origem. Se o artigo não tiver fontes (ex.: links
  perdidos na coleta), a seção permanece com uma nota explicando o motivo. (Decisão de 26/08/2026.)
