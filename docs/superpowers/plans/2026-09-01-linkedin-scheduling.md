# LinkedIn Scheduling Skill Implementation Plan

**Goal:** Tornar o agendamento e reagendamento do LinkedIn verificáveis, usando a rota compartilhada `MCP Chrome DevTools → Playwright (fallback) → screenshot + visão nativa → image-analyzer(native_failed) → stop`.

## Constraints

- Usar somente a sessão já autenticada; nunca ler ou armazenar credenciais.
- Validar `content/approved/` e converter Markdown antes de qualquer ação.
- Tentar MCP Chrome DevTools primeiro e registrar rota, resultado e razão.
- Usar Playwright somente como `playwright_fallback`, antes de qualquer mutação confirmada.
- Usar screenshot e visão nativa somente depois das duas rotas de controle; se a visão nativa falhar, usar `image-analyzer` com `reason: native_failed`.
- Nunca inferir estado sem evidência visual.
- Confirmar data, hora, resumo, prévia final e `Publicações agendadas` antes de registrar sucesso.
- Ao reagendar, usar `... → Alterar agenda`, selecionar novamente data e horário e nunca abrir novo composer.
- Se uma mutação ficar ambígua, aplicar fail-closed: não repetir nem avançar.

## Fluxo

1. Validar o arquivo aprovado e converter o conteúdo.
2. Tentar MCP Chrome DevTools sem mutação e registrar a evidência.
3. Se necessário, tentar Playwright com `playwright_fallback` e registrar a falha do MCP.
4. Capturar e validar evidência visual somente após as rotas de controle.
5. Selecionar explicitamente data e horário; após mudar a data, selecionar o horário novamente.
6. Confirmar o resumo antes de `Avançar`, a prévia antes de `Agendar` e o item em `Publicações agendadas`.
7. Registrar o timestamp somente após a confirmação final.

## Segurança

Publicar, agendar, reagendar e excluir são mutações de alto risco. Confirmar alvo e intenção antes do envio, verificar o estado resultante e registrar a rota efetiva. Timeout, desconexão ou erro após o envio é `ambiguous_mutation`; parar, não duplicar e não abrir novo composer.
