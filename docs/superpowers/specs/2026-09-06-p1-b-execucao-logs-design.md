# P1-B — Logs estruturados de execução

> **Status documental:** histórico; não é contrato operacional. Consulte `AGENTS.md` e os receipts em `runs/scheduling/`.

**Data:** 2026-09-06  
**Status:** aprovado pelo usuário

## Objetivo

Criar observabilidade persistente, reproduzível e sanitizada para as etapas do
pipeline, sem misturar logs operacionais com os receipts finais nem alterar o
comportamento editorial.

## Arquitetura

Um módulo central produzirá eventos JSONL, um evento por linha, armazenados em
`runs/`. Os consumidores informarão a etapa, o evento, a rota tentada, a rota
efetiva, o estado, a duração, a referência do receipt e o motivo de fallback ou
bloqueio.

Formato mínimo:

```json
{
  "run_id": "uuid",
  "timestamp": "ISO-8601",
  "stage": "browser|research|gauntlet|batch|scheduling",
  "event": "started|completed|blocked|fallback",
  "route_attempted": ["mcp_chrome_devtools"],
  "effective_route": "mcp_chrome_devtools",
  "state": "confirmed",
  "duration_ms": 1234,
  "receipt_ref": "receipt-id",
  "reason": "optional"
}
```

Campos opcionais não devem ser preenchidos com dados privados para “facilitar”
diagnóstico. O logger sanitiza recursivamente chaves e valores sensíveis antes
de serializar.

## Fluxo

1. Criar um `run_id` por execução.
2. Emitir `started` ao iniciar uma etapa.
3. Emitir `completed`, `blocked` ou `fallback` com estado final e duração.
4. Persistir JSONL de forma append-only e determinística.
5. Nunca registrar sucesso sem receipt ou estado correspondente quando a etapa
   exigir confirmação.

## Segurança

O sanitizador deve remover ou mascarar `AUTH_TOKEN`, `CT0`, cookies, API keys,
headers de autorização, senhas, identificadores de conta e conteúdo privado,
inclusive quando estiverem aninhados em listas ou objetos. Os arquivos em
`runs/` permanecem fora do Git; somente fixtures sanitizadas e testes podem ser
versionados.

## Integração inicial

A primeira integração cobrirá o fluxo de navegador e os contratos de receipt,
com MCP Chrome DevTools como primeira rota e Playwright apenas como fallback.
O logger será uma camada de observabilidade: não executará ações de navegador,
não publicará, não agendará e não criará novos posts.

## Testes e aceite

- Um teste simulado produz JSONL válido e reprodutível.
- Eventos preservam a ordem MCP → Playwright fallback → stop.
- Fallback registra motivo e rota anterior.
- Bloqueios registram estado sem alegar sucesso.
- Sanitização recursiva remove segredos e dados privados.
- `runs/` não é incluído em commits.
- Testes existentes continuam passando.
