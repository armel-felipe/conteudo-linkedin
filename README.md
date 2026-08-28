# LinkedIn Content Ops

Operação local e pessoal para organizar conteúdo para o LinkedIn. O fluxo editorial
é mantido em Markdown e os comandos operacionais começam em `contentctl`.

## Uso

```sh
./contentctl --help
./contentctl history --help
./contentctl history import
./contentctl report weekly --week 2026-07-27
```

Copie `.env.example` para `.env` e preencha apenas as configurações necessárias.
Valores já definidos no ambiente têm precedência sobre `.env`.

`history import` é somente leitura no Zernio: busca as postagens externas da conta
configurada, guarda respostas brutas locais em `data/imports/` (ignoradas pelo Git)
e atualiza o índice SQLite de modo idempotente. Ele exige `ZERNIO_API_KEY` e
`ZERNIO_ACCOUNT_ID`; mensagens de erro mostram apenas os nomes das configurações.

## Fluxo editorial

Uma ideia usa somente pesquisa já capturada e um pilar aprovado. Repetir os
comandos com os mesmos dados reutiliza a ideia e o rascunho existentes:

```sh
./contentctl ideas create --research research/2026-07-24--ia.md \
  --pillar "IA aplicada" --angle "Um ângulo verificável"
./contentctl draft create 1
./contentctl review submit 1
./contentctl review approve 1
```

`review submit` move explicitamente o rascunho para revisão; somente depois dessa
etapa `review approve` pode registrar a decisão humana. SQLite e Markdown são
atualizados juntos ou restaurados em caso de falha.

## Agendamento e acompanhamento

Agende somente depois de uma confirmação explícita. O comando exige uma `.env` local
com credenciais reais, um post já aprovado, horário futuro e `--confirm`:

```sh
./contentctl schedule 12 --at 2026-08-03T10:00:00-03:00 --confirm
```

Após o horário, `./contentctl posts sync 12` consulta apenas por GET o post já
agendado no Zernio. Ele nunca publica: o estado local muda para `published` somente
quando a resposta remota confirmar esse estado. `report weekly` mostra os estados
dos posts agendados de segunda a domingo, no fuso `America/Sao_Paulo`, e a cadência
da semana (`N/2`). Quando disponíveis, URL publicada e métricas numéricas também
são salvas no SQLite e no Markdown editorial.

## Segurança

Não versione `.env` nem compartilhe credenciais em conversas, documentos ou
artefatos editoriais. Agendamentos e publicações exigem confirmação explícita do
usuário.

## Permissões do agente (workspace)

O arquivo `opencode.jsonc` na raiz define permissões locais de aprovação do agente:
`read`, `edit`, `glob`, `grep`, `task`, `skill`, `webfetch`, `websearch` e
`bash` estão em `allow`. `.env` continua protegido pelo default do OpenCode e não
é afetado por essa configuração. `external_directory` não foi liberado (acesso
fora desta pasta segue pedindo aprovação). Para reverter, apague ou edite o
arquivo `opencode.jsonc`.
