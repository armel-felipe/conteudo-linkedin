# LinkedIn Scheduling Skill Implementation Plan

> **Status documental:** obsoleto; substituído pelo plano visual-first de 2026-09-15 e por `docs/browser-route-contract.md`.

**Goal:** Tornar o agendamento e reagendamento do LinkedIn verificáveis usando a
rota compartilhada `MCP Chrome DevTools → Playwright (fallback) → screenshot +
visão nativa → image-analyzer(native_failed) → stop`.

## Constraints

- Usar somente a sessão já autenticada; nunca ler ou armazenar credenciais.
- Validar `content/approved/` e converter Markdown antes de qualquer ação.
- Tentar MCP Chrome DevTools primeiro e registrar rota, resultado e razão.
- Usar Playwright somente como `playwright_fallback`, antes de qualquer mutação.
- Usar visão nativa e `image-analyzer` somente depois das rotas de controle.
- Confirmar data, hora, resumo, prévia final e `Publicações agendadas` antes do
  registro local.
- Ao reagendar, usar `... → Alterar agenda`, selecionar novamente data e horário
  e nunca abrir novo composer.
- Em mutação ambígua, aplicar fail-closed: não repetir nem avançar.

## Fluxo

1. Validar o arquivo aprovado e converter o conteúdo.
2. Tentar MCP Chrome DevTools sem mutação e registrar a evidência.
3. Se necessário, tentar Playwright como `playwright_fallback`, registrando a
   falha MCP antes de qualquer mutação.
4. Depois das duas rotas de controle, capturar e validar evidência visual; essa
   etapa não é uma rota de controle substituta.
5. Selecionar explicitamente data e horário; após mudar a data, selecionar o
   horário novamente.
6. Confirmar o resumo antes de `Avançar`, a prévia antes de `Agendar` e o item
   em `Publicações agendadas`.
7. Registrar o timestamp somente após a confirmação final.

## Segurança

Publicar, agendar, reagendar e excluir são mutações de alto risco. Timeout,
desconexão ou erro após o envio é `ambiguous_mutation`: parar, não duplicar e
 não abrir novo composer.

## Histórico do plano anterior

O plano original do checkpoint especificava as mesmas tarefas de validar arquivo,
converter Markdown, selecionar data/hora, confirmar resumo/prévia/lista e nunca
criar duplicata. Também previa checklist determinístico em
`docs/schemas/linkedin-scheduling-checklist.yaml`, matriz dos cinco cenários e
registro apenas de evidência não sensível. Essas tarefas continuam cobertas
pelos artefatos e testes do branch; a única alteração normativa é a precedência
MCP-first e o fail-closed explícito.
