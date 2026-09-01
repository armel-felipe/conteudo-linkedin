---
name: run-editorial-batch
description: Use quando for necessário executar uma rodada editorial com um ou mais topics prontos para pesquisa, mantendo fila, checkpoints e falhas por topic persistentes.
---

# Rodada Editorial em Lote

## Objetivo

Executar uma fila editorial congelada de topics `ready_for_research`, um por vez, sem depender do contexto da conversa. A entrada é `content/backlog.md` e `research/topics/topics_*.yaml`; a saída é `runs/<run_id>/manifest.yaml` e o estado persistente de cada topic na fila.

## Seleção

Aceite exatamente uma forma de seleção:

```text
--topics 1
--topics N
--topics all
--topics topic_a,topic_b
```

- `1` seleciona o melhor topic elegível.
- `N` seleciona os N melhores topics elegíveis.
- `all` seleciona todos os topics elegíveis.
- A lista separada por vírgulas seleciona somente os ids informados, na ordem explícita.

Considere somente topics com status `ready_for_research`. Para seleção numérica ou `all`, ordene por score decrescente e use um desempate determinístico pelo `topic_id`. Para ids explícitos, valide que cada id existe e está `ready_for_research`; não substitua ids inválidos por outros topics.

Antes do primeiro processamento, congele a seleção no `manifest.yaml`, incluindo `run_id`, timestamp, argumento original, score e ordem da fila. Não reordene nem acrescente topics durante a rodada.

## Execução sequencial

Processe um topic por vez. Para cada item, chame as etapas nesta ordem:

```text
research-topic → brief review Gauntlet → write-post → critique-post
→ correction Gauntlet → escrita-humana 1 → review
→ escrita-humana 2 → review → approval humana
```

Cada transição só ocorre após o artefato e o resultado da etapa anterior serem persistidos. `critique-post` produz feedback; a correção acontece no Gauntlet seguinte. As duas passagens de `escrita-humana` são obrigatórias e cada uma precisa de seu próprio review.

Não publique nem agende posts nesta skill: nunca chame `publicar-linkedin`.

## Checkpoints, Retomada e Falhas

Depois de cada etapa, atualize o item da fila com status, `current_stage`, artefato, resultado da revisão e timestamp. Ao reiniciar uma rodada, leia o `manifest.yaml` e retome do último checkpoint válido; não repita etapas já concluídas nem recrie a fila congelada.

Se uma etapa falhar, registre o erro e o artefato mais recente, marque o topic como `blocked` e persista o checkpoint antes de continuar para o próximo item da fila. Uma falha individual não interrompe a rodada nem libera o topic para a etapa seguinte. Ao final, o manifest deve registrar o resultado de todos os itens, inclusive `blocked`, e a aprovação humana continua sendo necessária antes de qualquer publicação.

## Checklist Rápido

| Momento | Verificação |
|---|---|
| Seleção | somente `ready_for_research`; score e desempate determinísticos |
| Início | fila congelada em `runs/<run_id>/manifest.yaml` |
| Cada etapa | artefato e estado persistidos antes de avançar |
| Falha | `blocked` persistido; continuar para o próximo topic |
| Fim | aprovação humana registrada; nenhuma publicação automática |

## Erros Comuns

- Processar topics em paralelo ou alterar a fila depois do congelamento.
- Pesquisar um topic que não está `ready_for_research`.
- Pular qualquer review, uma das duas passagens de `escrita-humana` ou a aprovação humana.
- Recomeçar do início em vez de retomar do checkpoint válido.
- Chamar `publicar-linkedin` dentro da rodada.
