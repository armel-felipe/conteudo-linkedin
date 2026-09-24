# Contrato de Rota de Navegador

Este documento define a rota normativa para qualquer skill ou script que opere
um navegador no pipeline editorial. A cadeia de browser é sempre:

```text
browser_native → playwright_mcp → playwright → stop
```

O **modo de visão** é uma dimensão ortogonal à cadeia de browser: `native` (o
modelo lê o screenshot direto) ou `image-analyzer` (leitura delegada quando não
há visão nativa ou ela falha). O `image-analyzer` lê o screenshot de **qualquer**
rota de browser que tenha funcionado; ele não é um passo da cadeia.

Os nomes normativos das rotas de browser são:

- `browser_native`: rota primária e obrigatória em host com browser embutido
  (Desktop). Deve abrir ou selecionar a aba pelo CUA embedded browser, capturar
  screenshot e usar visão nativa para localizar, ler e confirmar elementos antes
  de qualquer mutação; ela também resume conteúdo, data, hora, botões, menus e
  prévia.
- `playwright_mcp`: rota primária em host sem browser embutido (CLI). Usa o
  Playwright MCP (`@playwright/mcp --cdp-endpoint http://127.0.0.1:9223`), que
  anexa à sessão já logada.
- `playwright`: script read-only via CDP (`scripts/linkedin_browser_check.js`),
  somente diagnóstico. Nunca é rota de mutação.
- `stop`: encerramento fail-closed quando nenhuma rota conclui a operação.

Os modos de visão normativos são:

- `native`: o modelo lê o screenshot direto.
- `image-analyzer`: leitura delegada, usada quando o modelo não tem visão nativa
  (`no_native_vision`) ou quando a visão nativa falha (`native_failed`). Recebe o
  screenshot e retorna a leitura da tela.

Termos de resultado:

- `ambiguous_mutation`: resultado em que uma operação de mutação pode ter sido
  aplicada, mas seu resultado não foi confirmado.
- `fail_closed` (também referido como **fail-closed**): comportamento
  obrigatório diante de uma mutação ambígua: interromper novas ações e não
  presumir sucesso.

## Ordem e limite do fallback

1. Registrar a intenção, abrir/selecionar a aba com o navegador embutido e
   capturar `screenshot+nativa`.
2. Se o host não tiver browser embutido, tentar `playwright_mcp`.
3. Se a rota visual não puder concluir a operação, registrar a falha e tentar
   `playwright` somente como diagnóstico read-only.
4. Se nenhuma rota concluir a operação, registrar a rota efetiva e parar. Não
   tentar uma rota adicional e não abrir uma nova composição de ação.
5. Depois que uma mutação for enviada, fallback não é permitido para repetir
   a ação. Primeiro é necessário verificar o estado resultante.

Fallback é permitido somente antes de uma mutação ser confirmada. Em especial,
uma resposta de timeout, desconexão ou erro após o envio de uma ação deve ser
tratada como `ambiguous_mutation`, não como autorização para repetir a ação.

Toda operação deve registrar, no artefato ou log persistente, pelo menos a rota
efetiva (`browser_native`, `playwright_mcp`, `playwright` ou `stop`), o modo de
visão (`native` ou `image-analyzer`), o tipo de operação, o motivo, o resultado
e, quando houver, a verificação do estado. A ausência de registro torna a
operação não auditável e impede sua aprovação.

## Leitura e inspeção

Para abrir, ler, localizar elementos, capturar estado ou inspecionar uma tela:

- usar `browser_native` primeiro;
- usar `playwright_mcp` quando o host não tiver browser embutido;
- permitir `playwright` somente como diagnóstico read-only, depois da tentativa visual;
- delegar ao `image-analyzer` se o modelo não tiver visão nativa ou ela falhar;
- registrar a rota efetiva mesmo quando a operação terminar sem dados;
- em caso de falha em todas as rotas, parar sem converter uma leitura incerta em
  uma decisão editorial.

Leituras não devem criar, enviar ou alterar conteúdo. Uma ação de inspeção que
possa alterar estado deve ser classificada como mutação antes de ser executada.

## Publicar, agendar, reagendar e excluir

Publicar, agendar, reagendar e excluir são mutações de alto risco. Para cada
uma delas:

- confirmar o alvo, o conteúdo e a intenção antes do envio;
- usar `browser_native` como rota primária e obrigatória;
- usar `playwright_mcp` quando o host não tiver browser embutido;
- usar `image-analyzer` quando não houver visão nativa ou ela falhar;
- usar `playwright` somente como diagnóstico read-only antes de qualquer mutação;
- após o envio, verificar o estado no navegador ou por uma leitura independente
  antes de registrar sucesso;
- se o estado não puder distinguir sucesso de não execução, classificar como
  `ambiguous_mutation` e aplicar `fail_closed`;
- em `fail_closed`, não repetir, não publicar novamente, não reagendar, não
  excluir, não criar uma duplicata e não avançar o item para o próximo estado do
  pipeline.

Em particular, diante de um resultado ambíguo, **nunca abrir novo composer**:
o composer existente pode conter uma mutação já enviada ou um rascunho cujo
estado ainda precisa ser verificado. A próxima ação permitida é somente a
verificação de estado e, se necessário, a intervenção humana definida pelo
pipeline.

## Registro mínimo

Cada execução deve preservar:

- operação solicitada e alvo identificado;
- rota tentada e rota efetiva;
- modo de visão e, quando houver, a razão do fallback de visão;
- ponto em que a mutação foi ou não confirmada;
- evidência da verificação de estado;
- classificação final (`success`, `failed`, `ambiguous_mutation` ou `stop`);
- qualquer aplicação de `fail_closed`.

`scheduled_list_confirmed` deve estar confirmado antes de registrar o
`timestamp_registered` e o `timestamp`, e ambos devem ser validados antes da
persistência local. Somente evidência `real_existing_post` pode liberar esse
registro; `real_non_destructive`, `simulated` e `not_run` são sempre dry-run ou
observação sem mutação e devem ser rejeitados pelo gate.

Skills e scripts que não conseguirem produzir esse registro devem parar antes
de executar uma mutação.

## Logs de execução JSONL

O logger compartilhado persiste um evento JSON por linha em `runs/`. O envelope
mínimo contém `run_id`, `timestamp`, `stage`, `event`, `route_attempted`,
`effective_route`, `state`, `duration_ms`, `receipt_ref` e `reason` quando
aplicáveis. O ciclo normal é `started` seguido por `completed`, `blocked` ou
`fallback`.

O logger é somente observabilidade: não controla o navegador e não executa
publicação, agendamento ou exclusão. Antes de serializar, ele sanitiza
recursivamente valores associados a `AUTH_TOKEN`, `CT0`, cookies, API keys,
authorization headers, senhas, identificadores de conta e conteúdo privado.
`runs/` é diretório local e não deve ser incluído em commits; somente fixtures
sanitizadas e testes são versionáveis.
