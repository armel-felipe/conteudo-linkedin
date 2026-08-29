# Orquestrador híbrido com revisão obrigatória

## Objetivo

Garantir que cada bloco do pipeline editorial siga o fluxo canônico executor → validação determinística → revisor independente → loop de correção → aprovação → gate. O sistema deve falhar fechado: nenhuma etapa posterior pode iniciar sem a revisão aprovada e registrada da etapa anterior.

## Arquitetura

O runtime OpenCode coordena o trabalho e o `contentctl` é a autoridade determinística.

### Runtime OpenCode

- Coordena a rodada.
- Lê o `AGENT.md` exato de cada executor e revisor.
- Lê o `memory.md` do revisor.
- Dispara subagentes independentes via `task`.
- Passa ao revisor o artefato, o estado e o contrato específico.
- Passa o feedback do revisor ao executor em novo ciclo.
- Pausa nos gates humanos definidos pelo pipeline.

### `contentctl`

- Valida pré-condições, artefatos, paths e referências.
- Registra eventos e validações de forma transacional no SQLite.
- Confirma que a revisão aprovada corresponde à mesma rodada, bloco e artefato.
- Impede dupla conclusão e avanço fora de ordem.
- Mantém a rodada bloqueada em caso de erro.

O `contentctl` não dispara subagentes. O runtime OpenCode não substitui as validações determinísticas.

## Fluxo por bloco

```text
pré-condições
  → executor
  → validação determinística contentctl
  → revisor subagente com AGENT.md + memory.md
  → aprovado? ─ não → feedback → executor novamente
             └ sim → registro contentctl bloco-ok
  → gate humano, quando aplicável
  → próximo bloco
```

Qualquer timeout, erro, resposta ambígua, artefato ausente ou divergência de estado interrompe a rodada.

## Contrato dos subagentes

Cada chamada recebe o nome do bloco, os caminhos dos contratos, a rodada, os artefatos esperados, o estado relevante do `contentctl` e limites explícitos de escopo.

O revisor retorna uma decisão estruturada:

```json
{
  "decision": "approved",
  "artifact": "content/drafts/exemplo.md",
  "feedback": [],
  "checks": [
    {"name": "cobertura", "status": "passed", "evidence": "..."}
  ]
}
```

Ou retorna `decision: "feedback"` com itens contendo contrato, problema e mudança exigida. Respostas inválidas são rejeitadas e não contam como aprovação.

O limite padrão é de três ciclos por bloco. O limite é configurável; ao atingi-lo, a rodada pausa sem forçar aprovação. Cada ciclo é registrado sem credenciais.

## Estado e eventos

O SQLite persistirá, por rodada e bloco:

- início do executor;
- resultado da validação determinística;
- feedback do revisor;
- aprovação do revisor;
- espera por gate;
- conclusão do bloco;
- falha e motivo.

Cada aprovação terá rodada, bloco, artefato, ciclo, agente revisor, resultado estruturado e timestamp.

`bloco-ok` só será aceito quando houver revisão aprovada correspondente ao mesmo bloco, rodada e artefato.

Após interrupção, a retomada parte do último evento persistido, sem repetir blocos concluídos ou pular revisões.

## Falhas e segurança

- Timeout: registrar falha e repetir dentro do limite.
- Artefato ausente ou fora da rodada: bloquear antes do revisor.
- Feedback sem mudança: interromper por loop improdutivo.
- Falha do `contentctl`: não chamar o próximo agente.
- Credencial detectada em artefato ou log: bloquear e redigir o diagnóstico.
- B7 permanece sempre humano.

Logs não armazenam valores de `.env`, tokens ou prompts com segredos.

## Testes de aceitação

1. Aprovação no primeiro ciclo.
2. Feedback, correção e aprovação no ciclo seguinte.
3. Limite de ciclos atingido.
4. Resposta inválida do revisor.
5. Artefato ausente ou fora da rodada.
6. Avanço sem `bloco-ok` rejeitado.
7. Retomada após interrupção.
8. Ordem canônica preservada.
9. B7 sempre humano.
10. Credenciais ausentes dos logs e artefatos.

## Decisão de configuração

O workspace já permite `task` em `opencode.jsonc`. Portanto, a coordenação usa o backend OpenCode nativamente, sem exigir alteração em um `config.jsonc` global. O runtime deve, contudo, carregar explicitamente o `AGENT.md` correto, pois o diretório de agentes não deve ser presumido como seleção automática do subagente.
