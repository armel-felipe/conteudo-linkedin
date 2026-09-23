# Content Backlog

> Backlog ranqueado após a leva de sinais de 2026-09-15. Temas elegíveis têm `status: ready_for_research` nos arquivos de topics.

## Fila operacional

**Fila vazia.** Não há temas `ready_for_research` no momento.

Os temas que estavam na fila do Bloco 2 foram descartados por decisão do autor em 2026-09-23 e marcados como `archived` nos arquivos de topics:

| topic_id | Tema | Score |
|---|---:|---:|
| `topic_20260915_07` | Governança de IA é uma cadeia operacional de prova | 91,0 |
| `topic_20260915_04` | A velocidade da entrega precisa caber na margem | 87,5 |
| `topic_20260915_01` | A IA só entrega valor quando atravessa o caminho entre insight e execução | 85,5 |
| `topic_20260915_08` | IA em segurança alimentar deve acelerar o risco sem apagar a responsabilidade | 82,0 |
| `topic_20260914_02` | Agent washing: o que se vende como agente autônomo é automação com passos extras | 78,0 |
| `topic_20260914_05` | O gargalo dos agentes não é mais inteligência — é infraestrutura e custo | 78,0 |
| `topic_20260914_06` | Avaliar agente em produção: a régua não é a demo | 78,0 |
| `topic_20260914_03` | Governança de IA se prova por evidência operacional, não por política | — |

Temas `archived` saem do fluxo de aprovação e não voltam a ser considerados.

## Como reabastecer a fila

A fila do Bloco 2 é reabastecida pelo Bloco 1:

```text
Rode discover-signals
Rode cluster-signals
Rode score-opportunities
```

O `score-opportunities` pontua os temas candidatos e grava os elegíveis como `ready_for_research` neste backlog.

## Como transformar temas em drafts

Use a skill `run-editorial-batch`, sempre com a opção `--topics`:

```text
Rode run-editorial-batch --topics 1
```

Isso seleciona o tema `ready_for_research` com maior score. Para escolher mais de um tema pela ordem do score:

```text
Rode run-editorial-batch --topics 3
```

Para escolher temas específicos, use os IDs separados por vírgula:

```text
Rode run-editorial-batch --topics topic_20260915_07,topic_20260915_04
```

O lote pesquisa, escreve, revisa e humaniza os temas selecionados. Ao final, os arquivos aparecem em `content/drafts/` para QA humano. Ele não aprova, agenda ou publica automaticamente.
