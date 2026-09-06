# Task 3 Report: MCP-first browser automation

## Status atual

Corrigida a revisão sobre documentação e operação browser. A skill
`publicar-linkedin` começa por MCP Chrome DevTools; Playwright só aparece como
`playwright_fallback` após falha MCP registrada antes de mutação. O roadmap usa
somente `mcp_chrome_devtools`, `playwright_fallback` e `stop`, com motivo e
registro auditáveis.

## Alterações e verificação

- `.agents/skills/publicar-linkedin/SKILL.md`: rota MCP-first, fail-closed e
  registro de rota/fallback.
- `docs/roadmap.md`: rotas canônicas e motivo do `stop`.
- `tests/test_browser_route_documentation.py`: cobertura de ordem, fallback,
  motivo, registro, fail-closed e separação do lote editorial.
- `mapa.md` e a especificação editorial: alinhados ao contrato reforçado.
- A verificação focada e a verificação conjunta do branch foram registradas no
  histórico abaixo; a verificação final desta integração está no relatório de
  merge.

## Concerns

Os testes validam documentação e contrato textual; não executam mutações no
LinkedIn. O smoke test permanece documental/simulado e usa `stop` quando não há
falha MCP registrada que justifique fallback.

## Histórico preservado do checkpoint `fdce350`

O checkpoint continha o relatório oficial de memória do autor. Foram criados:

- `memory/professional_experience.md` com experiência profissional;
- `memory/opinions.md` com opiniões sobre automação, métricas e IA;
- `memory/writing_style.md` com formato, esqueleto obrigatório e critérios de
  revisão.

A verificação original confirmou os três arquivos e a presença de `ABERTURA`.
Commit original: `c4fb16c feat: memória do autor (experiência, opiniões, estilo
de escrita)`. Esse histórico não foi descartado.

## Histórico de tarefas anteriores

O relatório original também preservava os ciclos do protocolo de reviewers,
incluindo os commits `c1b2342`, `d3a937e`, `c795594` e a política de visão nativa
do commit `c50c857`. Esses registros continuam representados pelos artefatos
do checkpoint e não foram substituídos pela implementação MCP-first.
