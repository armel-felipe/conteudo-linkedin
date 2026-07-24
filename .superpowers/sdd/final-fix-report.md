# Relatório final de correções High e Medium

## Status

Todos os achados High e Medium da revisão ampla foram corrigidos. Os gates de
aprovação e agendamento foram preservados, e nenhum teste realizou chamada real
ao Last30days ou ao Zernio.

## Correções

- O dispatcher da CLI usa apenas o atributo do subcomando ativo. Testes ponta a
  ponta percorrem `ideas create`, `draft create`, `review submit` e
  `review approve` pelo parser, SQLite e Markdown.
- `review submit <post-id>` implementa explicitamente `draft -> in_review`.
  SQLite e Markdown são atualizados na mesma operação compensatória; uma falha
  na escrita restaura o estado anterior.
- `posts sync <post-id>` agora localiza o registro editorial e aplica o resultado
  do GET ao SQLite e ao Markdown. Status remoto, URL publicada, instante do sync
  e métricas numéricas são persistidos. Falha de Markdown reverte SQLite; falha
  de commit restaura o Markdown; uma falha rara também na restauração deixa um
  sidecar não sensível para recuperação.
- Ideias usam uma chave SHA-256 determinística sobre ângulo, pilar e pesquisa.
  Um índice único evita duplicação. A ideia também recebe seu Markdown em
  `content/ideas/`.
- Cada ideia possui no máximo um `draft_post_id`. Repetir a criação reutiliza o
  post/arquivo e preserva edições humanas. Conflitos de caminho são recusados,
  sem sobrescrita silenciosa.
- Criação de ideia/draft mantém a transação SQLite aberta até a publicação
  atômica do Markdown. Falhas antes ou depois do `replace` removem o novo arquivo
  e revertem SQLite, evitando órfãos.
- A escrita genérica de registros Markdown usa arquivo temporário, `fsync`,
  `os.replace` e `fsync` do diretório.
- Metadados de draft incluem `suggested_time`, `sources`, `published_url`,
  `metrics` e `publication_result`. SQLite armazena horário sugerido, fontes,
  URL, métricas e resultado do sync.
- O schema agora usa `PRAGMA user_version`, com migrações sequenciais até a
  versão 4. A migração legada cobre o schema histórico mínimo de posts
  (`id`, `title`, `status`) e adiciona colunas/índices necessários sem perder os
  registros existentes.

## Escolhas para ambiguidades

- Horário sugerido nasce como `null`: o sistema não inventa um horário editorial
  sem decisão humana. O horário efetivo continua sendo persistido separadamente
  no agendamento.
- `sources` começa com a pesquisa capturada que originou a ideia. A estrutura é
  uma lista de objetos para permitir novas fontes sem alterar o formato.
- O sync guarda somente um resultado selecionado e não sensível, em vez da
  resposta remota inteira. Métricas são limitadas a agregados numéricos de
  `metrics` ou `analytics`.
- Bancos legados com identificadores declarados como únicos mas já duplicados
  não são deduplicados silenciosamente; exigem correção manual antes da criação
  do índice. Essa é a opção menor e mais segura para não apagar dados.

## Evidência TDD e verificação

- RED inicial: 11 erros e 1 falha reproduziram dispatcher inválido, ausência do
  fluxo de revisão, órfão de draft, metadados ausentes, sync sem Markdown e
  schema sem versão.
- GREEN focado: 30 testes passaram.
- RED adicional: fontes/horário ausentes no SQLite; 1 erro e 1 falha.
- GREEN adicional: 3 testes passaram.
- RED de auto-revisão: 2 falhas reproduziram órfãos após publicação do arquivo e
  falha posterior de durabilidade.
- GREEN de auto-revisão: 2 testes passaram.
- Suíte final: `PYTHONPATH=src python3 -m unittest discover -s tests -v` —
  88 testes passaram.
- `python3 -m compileall -q src tests` — passou.
- `git diff --check` — passou.
- `./contentctl --help` e `./contentctl review --help` — passaram; a ajuda lista
  `submit` e `approve`.

## Preocupações remanescentes

- A acessibilidade remota de `image_url` continua fora deste escopo; o gate
  atual valida esquema e host, conforme classificado como Low na revisão.
- Métricas aninhadas ou textuais não são armazenadas. Se o contrato real do
  Zernio usar outro formato, deve-se adicionar um mapeamento explícito testado.
