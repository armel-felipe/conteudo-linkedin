# Task 7 — recuperação idempotente de agendamento

## Resultado

- Adicionado o estado `indeterminate`, suas transições e a migração SQLite para
  `idempotency_key`, `scheduled_for` e o payload serializado da solicitação.
- Antes de cada POST, o fluxo cria (ou reutiliza) um UUID, persiste em SQLite e
  no Markdown a chave, o horário e o payload exato; nenhum POST ocorre se essa
  persistência não completar.
- `ZernioClient.create_post` recebe a chave e a envia como `x-request-id`.
- Falhas confirmadas antes do envio tornam-se `failed`; falhas cujo resultado
  remoto é desconhecido tornam-se `indeterminate`, bloqueando outro agendamento
  normal.
- `contentctl schedule reconcile <post-id>` reenvia o payload persistido com a
  mesma chave e conclui o estado recuperado como `scheduled`.

## Evidência de teste

`PYTHONPATH=src python3 -m unittest discover -s tests -v` passou com 69 testes.
Os testes novos não usam rede real e cobrem UUID persistido antes da chamada,
header `x-request-id`, erro pré-envio, resultado incerto, bloqueio do novo POST,
reconciliação com a mesma chave e migração de banco existente.

`./contentctl schedule 1 --at 2026-08-01T10:00:00` recusou o comando com
`--confirm is required` antes de carregar configuração ou criar cliente HTTP.

## Revisão própria e ressalvas

O sidecar continua apenas como alarme de falha de escrita posterior ao POST; ele
não é a única evidência, pois a intenção (UUID e payload) é duravelmente gravada
em SQLite e Markdown antes da chamada. Em caso de indisponibilidade simultânea
dos dois stores após o POST, o sidecar bloqueia novo POST e a intenção prévia
permite reconciliação segura assim que ao menos um store voltar a aceitar escrita.
