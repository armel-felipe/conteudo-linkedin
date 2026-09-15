# Roadmap ativo do pipeline editorial

Última atualização: 2026-09-15.

Este arquivo lista somente trabalho **não concluído e atualmente ativo**.
Itens concluídos, adiados, bloqueados ou excluídos ficam fora do roadmap ativo.

## Pendências ativas

Nenhuma. O plano de retomada do agendamento foi executado e encerrado.
Plano executado: `docs/superpowers/plans/2026-09-15-scheduling-restart.md`.

## Trabalho concluído nesta atualização

- Contratos ativos alinhados: `approved` é marco editorial; o arquivo permanece em
  `content/drafts/` até o Bloco 3 confirmar a mutação no LinkedIn.
- Rota normativa consolidada como **CUA embedded browser → screenshot/AX +
  `browser_native` → `image-analyzer` se necessário → Playwright somente
  read-only → stop/fail-closed**.
- CLI e receipts verificados para `validate`, `prepare`, `receipt` e `reconcile`;
  a reconciliação atual terminou sem problemas.
- Documentos históricos com rota antiga foram identificados como não normativos;
  os contratos ativos passaram a ser a referência única.
- P1 corrigido: receipts que usam `image-analyzer` agora aceitam e exigem a
  evidência explícita `image_analyzer_failure`.
- Agendamento visual confirmado: `topic_20260914_04`, em **16/09/2026 às
  10:00 (America/Sao_Paulo)**, com verificação na lista do LinkedIn e arquivo
  movido para `content/published/` somente após a confirmação.

## Estado operacional

- O pipeline editorial está operacional do discovery ao agendamento/publicação.
- A rota de navegador vigente é:
  **CUA embedded browser → screenshot/AX + `browser_native` → `image-analyzer`
  se necessário → Playwright read-only → stop**.
- Execuções confirmadas: reagendamento de `topic_20260907_01` para `11/09/2026
  às 10:00` e agendamento de `topic_20260914_04` para `16/09/2026 às 10:00`.
- Verificação mais recente: **301 testes Python** e **26 testes Node** passaram;
  a checagem de consistência documental acrescentou **20 testes**.

## Referências

- Contrato de rota: `docs/browser-route-contract.md`
- Skill de publicação: `.agents/skills/publicar-linkedin/SKILL.md`
- Contrato geral: `AGENTS.md`
- Registro de agendamentos: `runs/scheduling-registry.yaml`
