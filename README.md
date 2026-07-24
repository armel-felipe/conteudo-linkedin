# LinkedIn Content Ops

Operação local e pessoal para organizar conteúdo para o LinkedIn. O fluxo editorial
é mantido em Markdown e os comandos operacionais começam em `contentctl`.

## Uso

```sh
./contentctl --help
./contentctl history --help
./contentctl history import
```

Copie `.env.example` para `.env` e preencha apenas as configurações necessárias.
Valores já definidos no ambiente têm precedência sobre `.env`.

`history import` é somente leitura no Zernio: busca as postagens externas da conta
configurada, guarda respostas brutas locais em `data/imports/` (ignoradas pelo Git)
e atualiza o índice SQLite de modo idempotente. Ele exige `ZERNIO_API_KEY` e
`ZERNIO_ACCOUNT_ID`; mensagens de erro mostram apenas os nomes das configurações.

## Segurança

Não versione `.env` nem compartilhe credenciais em conversas, documentos ou
artefatos editoriais. Agendamentos e publicações exigem confirmação explícita do
usuário.
