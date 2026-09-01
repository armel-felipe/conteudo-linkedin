---
name: gauntlet-loop
description: Use para executar uma tarefa nova em ciclos isolados de executor e revisor, com gates determinísticos, feedback persistente e bloqueio fail-closed.
---

# Loop Gauntlet

## Objetivo

Validar um artefato produzido por uma tarefa nova sem confiar no contexto ou no resultado do ciclo anterior. O Gauntlet consome um contrato de executor, um contrato de revisor, o caminho do artefato e o feedback disponível; produz um review por ciclo e um resultado terminal `approved` ou `blocked`.

O caller decide se deve continuar a fila depois de um `blocked`. O Gauntlet nunca libera uma tarefa bloqueada por conta propria.

## Interfaces Python

O procedimento executavel esta em `gauntlet_loop.py` e expoe somente estas interfaces:

```python
validate_review(review) -> dict
run_gauntlet(executor, reviewer, max_cycles=5, *, artifact_path, persistence_dir=None, run_id="run", workspace_root=None) -> dict
```

`executor(feedback) -> artifact` e `reviewer(artifact, feedback) -> review` sao callbacks separados. Cada chamada recebe uma copia profunda de contexto novo e isolado; nenhum callback pode compartilhar ou mutar o estado interno de outro ciclo. `validate_review` faz a validacao estrutural estrita e identifica criterios abaixo do gate; `run_gauntlet` transforma falhas de qualidade em `feedback`, repete ate cinco rodadas e reserva `blocked` para falhas terminais ou esgotamento.

## Contratos de entrada

Antes de iniciar, confirme que existem:

- contrato do executor, incluindo objetivo, entradas, saida esperada e caminho do artefato;
- contrato do revisor, incluindo criterios, escala e formato JSON;
- caminho relativo do artefato dentro do workspace;
- feedback completo do ciclo anterior, quando houver.

Ausencia, ambiguidade ou divergencia em qualquer entrada e falha de validacao. Nao improvise valores nem converta um caminho absoluto em relativo.

## Ciclo obrigatorio

O ciclo exato e:

```text
cycle-start → executor → deterministic checks → fresh reviewer
→ structured result → approve or feedback → next cycle
```

Para cada ciclo:

1. Registre `cycle-start` com o numero do ciclo, contrato e caminho do artefato.
2. Faca uma chamada `task` nova e isolada para o `executor`. Nao reutilize a conversa, estado ou memoria de outro executor.
3. Confirme deterministicamente que o executor respeitou o contrato, escreveu o artefato no caminho relativo esperado e nao produziu saida incompleta.
   Registre o resultado dos deterministic checks antes de chamar o revisor.
4. Faca outra chamada `task` nova e isolada para o `revisor`, diferente do executor. Entregue somente o artefato, o contrato do revisor e o feedback necessario.
5. Aceite o resultado apenas se ele for JSON valido, parseavel e conforme o contrato. O objeto deve conter `decision`, `coverage`, `criteria`, `hard_failures`, `feedback` e `artifact`.
6. Persista `runs/<run_id>/topics/<topic_id>/reviews/cycle-<NN>.yaml` ou o caminho de review definido pelo caller antes de avancar.
7. Aprove somente quando `decision` for `approved`, `coverage > 0.99` (coverage >99%, mais de 99%) e todos os criterios forem `>=9/10` (all criteria at least 9/10), sem `hard_failures`.
8. Se o JSON for valido, mas `coverage <=99%` ou algum `criteria <9/10`, o resultado e `feedback`, nao bloqueia. Exija feedback completo e acionavel associado a cada criterio falho; para coverage abaixo do gate, exija feedback acionavel. O proximo executor recebe esse feedback e consome uma nova rodada.
9. Se a decisao for `feedback`, exija feedback completo e acionavel para cada criterio falho. O proximo executor recebe esse feedback e inicia um novo ciclo.

## Contrato JSON estrito

Antes de avaliar gates, valide sem coercoes:

- a resposta deve ser um objeto raiz JSON, nunca array, string, numero, `null` ou texto adicional;
- os campos obrigatorios devem ter tipos corretos: `decision` string, `coverage` numero, `criteria` objeto, `hard_failures` lista, `feedback` lista e `artifact` string;
- `decision` e um decision enum restrito a `approved` ou `feedback`;
- `coverage` deve ser coverage finito e estar entre 0 e 1, inclusive; rejeite `NaN`, `Infinity`, strings e booleanos;
- `criteria` deve ser criteria objeto exatamente igual à allowlist normativa de 14 critérios (`clareza`, `força da abertura`, `originalidade`, `credibilidade`, `uso de evidências`, `risco de alucinação`, `tom humano`, `densidade`, `relevância`, `consistência com a voz do autor`, `estrutura obrigatória`, `pergunta final`, `tamanho editorial`, `rastreabilidade das fontes`), com valores numeros 0-10, finitos e sem booleanos; critérios omitidos, extras ou renomeados são falha estrutural;
- `hard_failures` e `feedback` devem ser hard_failures/feedback listas JSON, mesmo quando vazias;
- `artifact` deve ser artifact string nao vazia, relativa ao workspace e igual ao artefato verificado.

JSON invalido, objeto raiz errado, campo ausente, tipo incorreto, valor fora dos limites ou qualquer campo extra e falha estrutural terminal.

## Validacao fail-closed

Qualquer uma destas condicoes bloqueia imediatamente, sem aprovar e sem tentar mascarar o erro. Estas sao as unicas categorias terminais:

- executor/revisor indisponivel, ausente, nao isolado ou chamado sem `task` nova;
- contrato ausente, entrada ambigua, missing artifact ou artefato ausente;
- artefato fora do caminho esperado, vazio, incompleto ou nao verificavel (artifact ausente);
- saida do revisor que nao seja valid JSON, seja JSON truncado ou nao contenha todos os campos obrigatorios;
- falha estrutural no objeto JSON, incluindo `decision` fora do enum, tipos incorretos, coverage nao finito ou fora de 0-1;
- `hard_failures` nao vazio (hard failure);
- feedback ausente ou incompleto quando houver retry; cada retry exige complete feedback associado ao criterio;
- falha em qualquer validacao deterministica (`failed validation`) ou erro de persistencia do review.

`coverage <=99%` e `criteria <9/10` nao sao falhas terminais quando o JSON, o artefato e os participantes sao validos: produzem `feedback` por criterio e nova rodada. Nao trate texto livre, JSON parcial ou uma aprovacao verbal como resultado estruturado. Em caso de duvida estrutural, o resultado e `blocked`.

## Limite terminal

Execute no maximo 5 rodadas (maximum of 5 rounds). Faca retries ate 5 rodadas, sem sexta rodada. Apos a quinta rodada sem um resultado que passe todos os gates, escreva um resultado terminal `blocked` contendo:

```json
{
  "status": "blocked",
  "failure_reasons": ["..."],
  "failed_criteria": ["..."],
  "last_artifact": "relative/path/to/artifact",
  "cycle_count": 5
}
```

Inclua tambem o ultimo review persistido e o feedback recebido. Nao abra uma sexta rodada, nao aprove por aproximacao e nao continue automaticamente a fila. O caller, nao o Gauntlet, decide se continua o batch queue.

Os campos `failure reasons`, `failed criteria`, `last artifact` e `cycle count` sao obrigatorios no registro terminal, ainda que tambem sejam serializados nas chaves JSON com underscore.

## Persistencia e idempotencia

Cada ciclo deve deixar um arquivo de review identificavel pelo numero `cycle-01` ate `cycle-05`. Escreva de forma atomica e nao sobrescreva um review valido com resultado diferente para a mesma chave `(run_id, topic_id, gauntlet, cycle)`. Ao retomar, valide o review existente; se estiver invalido, bloqueie em vez de confiar nele.

Quando `persistence_dir` for fornecido, grave atomicamente `cycle-01.yaml` ate `cycle-05.yaml`, `events.yaml` e `state.yaml`. O ciclo usa a chave `(run_id, artifact, cycle)`; uma repeticao do mesmo ciclo nao duplica review ou evento. `events.yaml` deve registrar `cycle-start`, `deterministic-checks` e `review` nessa ordem, e `state.yaml` deve conter o resultado terminal completo.

Every stage writes an event, and every reviewer result is saved per cycle. A resumed run skips only stages with valid artifacts and passing reviews; **Never rerun an approved topic automatically**. The caller must create an explicit new run for approved work that needs revision.

The caller's run manifest records `queue_size`, `completed`, `blocked`, `cycles_per_stage`, `reviewer_coverage`, `human_writing_conformity`, and `time_to_approval`. These operational metrics do not weaken the acceptance gate: coverage must be `> 0.99`, every criterion must be `>=9/10`, and any `hard_failures` blocks approval.

O resultado `blocked` apos a quinta rodada deve conter `failed_criteria`, `last_artifact`, `last_review`, `feedback` completo, `cycles` igual a 5 e as razoes da falha. O resultado tambem pode expor `cycle_count` para compatibilidade com os checkpoints existentes.

## Checklist

- [ ] executor e revisor sao chamadas `task` novas e isoladas;
- [ ] deterministic checks passaram;
- [ ] artefato existe no caminho relativo esperado;
- [ ] review e JSON valido e completo;
- [ ] coverage maior que 99% e todos os criterios no minimo 9/10, ou feedback foi gerado para cada falha de qualidade;
- [ ] feedback e completo em cada retry;
- [ ] limite de 5 rodadas foi respeitado;
- [ ] resultado final e `approved` ou `blocked` e esta persistido.
