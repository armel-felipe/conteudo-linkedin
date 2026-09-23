# Roadmap ativo do pipeline editorial

Última atualização: 2026-09-22.

Este arquivo lista somente trabalho **não concluído e atualmente ativo**.
Itens concluídos, adiados, bloqueados ou excluídos ficam fora do roadmap ativo.

## Pendências ativas

- **Reduzir e medir o consumo de tokens do pipeline editorial** — execução em
  três frentes: registrar uso de tokens por stage/modelo, reutilizar pesquisas
  idênticas por chave de tópico/janela/versão e compactar o contexto do
  `last30days` sem remover os gates editoriais obrigatórios. A meta operacional
  é reduzir o consumo total em 35–60% e tornar o ganho mensurável por rodada.
  Plano detalhado: `docs/superpowers/plans/2026-09-22-token-consumption.md`.
  Primeira fatia executável concluída: contrato de telemetria, relatório,
  chave de cache, política de reuso e modo compacto editorial documentados.
  Falta validar uma rodada A/B antes de mexer na quantidade de revisões.

- **Tornar os gates editoriais substantivos e fail-closed** — o executor deve
  rejeitar reviews genéricas, exigir evidência textual de contexto, coesão,
  batimentos narrativos, decisão e consequência, e rebaixar drafts que não
  tenham essa comprovação. Plano:
  `docs/superpowers/plans/2026-09-15-editorial-quality-gates.md`.

- **Reescrever e revalidar os drafts da rodada 2026-09-15** — os topics 09, 06
  e 02 estão bloqueados até receberem crítica baseada em trechos reais, contexto
  suficiente e uma linha narrativa coesa.

- **Estruturar a narrativa dos drafts e formalizar a seleção de estrutura** —
  criar uma regra de negócio que escolha o motor narrativo a partir da evidência
  dominante (caso, decisão, contraste, métrica, experiência ou movimento de
  mercado), sem transformar os posts em cópias. Regra registrada e aplicada ao
  `topic_20260914_07`; permanece pendente a reavaliação do
  `topic_20260914_01`.
  Plano: `docs/superpowers/plans/2026-09-15-narrative-structure-selection.md`.

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
- O plano `docs/superpowers/plans/2026-09-15-scheduling-restart.md` foi
  executado e encerrado; não há checklist operacional pendente dessa frente.
  Nenhuma ação adicional está aberta nesse plano.

## Referências

- Contrato de rota: `docs/browser-route-contract.md`
- Skill de publicação: `.agents/skills/publicar-linkedin/SKILL.md`
- Contrato geral: `AGENTS.md`
- Registro de agendamentos: `runs/scheduling-registry.yaml`
