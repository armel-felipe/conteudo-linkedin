# Content Backlog

> Temas com `status: ready_for_research` nos arquivos `research/topics/topics_*.yaml`.
> Temas já `approved` não aparecem aqui nem são elegíveis para o Bloco 2.
> Leva de 2026-09-23: 12 topics candidatos pontuados; 7 entram no backlog.

## 91.00 — O agente em produção trava na operação, não no modelo

`topic_20260923_01`

Novidade: Revisitado — delta: o gargalo operacional (dado, observabilidade, custo, verificação), não a avaliação pós-deploy.

Pilares: IA Aplicada

Tese: O gargalo do agente em produção não é capacidade do modelo: é dado confiável, observabilidade, controle de custo e verificação — sem isso, a automação só transfere o esforço para a conferência.

Por que agora: Relato de que "conferir os agentes virou outro emprego", entrevista com 10 executivos apontando o dado (não o modelo) como maior desafio de produção, e a tese de que quem vence controla custo e enxerga a falha em detalhe.

Evidências disponíveis: 6

Experiência pessoal relacionada: Alta

Status: ready_for_research

## 89.00 — A última milha cobra caro pela promessa que faz

`topic_20260923_07`

Novidade: Revisitado — delta: a origem do atraso antes da rua (alocação, visibilidade, intervenção), não a métrica da promessa.

Pilares: Logística, last mile e CX

Tese: A última milha não é competição por minutos: é a promessa cumprida dentro da margem — e o atraso que importa nasce antes da rua, na alocação, na visibilidade e na capacidade de intervir.

Por que agora: Custo da última milha subindo 12% com combustível e escassez de motorista, Shadowfax reportando salto de 5x no lucro sob escrutínio, e a tese de que o atraso começa antes da rua.

Evidências disponíveis: 4

Experiência pessoal relacionada: Alta

Status: ready_for_research

## 86.50 — O agente que age em nome do cliente esbarra no dono da plataforma

`topic_20260923_02`

Novidade: Revisitado — delta: o conflito de autoridade entre agente e plataforma, não a contestabilidade da previsão.

Pilares: IA Aplicada / Riscos, compliance e resiliência

Tese: Autonomia que age em nome de alguém sem identidade, autorização explícita e trilha de auditoria não é conveniência: é acesso não autorizado — e a plataforma vai barrar.

Por que agora: Amazon bloqueando o agente Muse da Meta (151 pontos no HN), bancos sinalizando desconforto com compras por agente e o agente lendo mensagens privadas sem pedido.

Evidências disponíveis: 3

Experiência pessoal relacionada: Média

Status: ready_for_research

## 86.00 — Prova de entrega que aceita qualquer dado não é controle

`topic_20260923_08`

Novidade: Revisitado — delta: a integridade do controle (aceita qualquer entrada), não a escapatória humana na falha.

Pilares: Logística, last mile e CX / Riscos, compliance e resiliência

Tese: Controle que aceita qualquer entrada não é controle: é teatro de conformidade — e a mentira no status de entrega custa mais ao cliente do que a falha admitida.

Por que agora: Issue crítica documentando que nome e telefone errados ainda marcam o pedido como entregue, e reclamação de que admitir a perda gera reembolso enquanto marcar "entregue" remove o recurso do cliente.

Evidências disponíveis: 2

Experiência pessoal relacionada: Alta

Status: ready_for_research

## 84.00 — Accountability só funciona com autoridade e consequência

`topic_20260923_09`

Novidade: Revisitado — delta: a condição da cobrança (autoridade, recurso, consequência), não a liderança na cobrança.

Pilares: Liderança em operações

Tese: Cobrança sem autoridade, recurso e consequência é só pressão: o padrão que ninguém inspeciona deixa de existir, e repetir a mesma coisa cinco vezes é sintoma de accountability, não de comunicação.

Por que agora: Série de conteúdo operacional sobre time que para de tratar prazo como compromisso, cobrança sobre resultado sem autoridade para influenciar e o custo de evitar a conversa difícil.

Evidências disponíveis: 4

Experiência pessoal relacionada: Alta

Status: ready_for_research

## 83.00 — O agente que entrega valor começa pelo gargalo chato, não pela vitrine

`topic_20260923_04`

Novidade: Novo — nenhum post publicado sobre priorização do caso de uso do agente.

Pilares: IA Aplicada

Tese: O agente que dá retorno não substitui o sistema nem brilha na demo: ele orquestra o que já existe e ataca o gargalo operacional doloroso, um de cada vez.

Por que agora: Casos de agente em pequenos negócios concentrados em follow-up, CRM e admin, e levantamento de casos enterprise descrevendo o agente como camada de orquestração sobre o ERP existente.

Evidências disponíveis: 2

Experiência pessoal relacionada: Alta

Status: ready_for_research

## 79.50 — Prova, permissão e infraestrutura de agente viram categoria de mercado

`topic_20260923_03`

Novidade: Revisitado — delta: o mercado de prova e permissão de agente, não o desenho interno do controle.

Pilares: IA Aplicada / Riscos, compliance e resiliência

Tese: Quando o agente ganha autonomia, a prova de capacidade e a permissão escopada deixam de ser detalhe técnico e viram item de compra — com atestado, sandbox e identidade próprios.

Por que agora: Verificação de agente com atestado assinado e OWASP Agentic Top 10, permissões just-in-time, Série B de US$ 72M para agentes de DLP e ferramentas de sandbox e observabilidade nascendo para agentes.

Evidências disponíveis: 4

Experiência pessoal relacionada: Média

Status: ready_for_research

## Fora do backlog

- **77.50 — Desperdício de alimento é problema de operação, não de conscientização** (`topic_20260923_11`): empate no corte com `topic_20260923_05`; pilar de prioridade 4 e conexão média com a experiência do autor. Permanece `candidate`.
- **75.50 — Segurança alimentar se prova por rastreabilidade, não por política** (`topic_20260923_12`): score abaixo do corte; pilar de prioridade 4. Permanece `candidate`.

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
Rode run-editorial-batch --topics topic_20260923_01,topic_20260923_07
```

O lote pesquisa, escreve, revisa e humaniza os temas selecionados. Ao final, os arquivos aparecem em `content/drafts/` para QA humano. Ele não aprova, agenda ou publica automaticamente.
