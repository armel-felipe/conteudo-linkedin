# Especificação: execução editorial sequencial com Loop Gauntlet

## Objetivo

Permitir selecionar de 1 a X topics do backlog, inclusive todos os topics elegíveis, e processá-los um por vez através das etapas editoriais até a aprovação humana, preservando qualidade, rastreabilidade e retomada segura.

O agendamento/publicação no LinkedIn permanece fora deste fluxo e será tratado por uma skill operacional separada.

## Princípios preservados

- Pesquisa começa por acontecimentos e debates, não por “sobre o que escrever?”.
- Cada etapa produz um artefato persistente.
- Pesquisa e redação são executadas por agentes distintos.
- Nenhum fato entra no post sem fonte, URL e data no brief.
- Todo post passa duas vezes por `escrita-humana`.
- Nenhum critério editorial do post pode ficar abaixo de 9/10.
- Um erro em um topic não interrompe os demais topics selecionados.
- Nenhum topic bloqueado pode ser promovido automaticamente.

## Escopo

### Incluído

- Seleção ordenada de 1 a X topics.
- Fila congelada no início da execução.
- Processamento sequencial, um topic por vez.
- Máquina de estados por topic.
- Execução isolada de executor e revisor.
- Loop Gauntlet independente, com até 5 rodadas.
- Cobertura mínima de 99% dos requisitos (`coverage >= 0.99`).
- Dois ciclos obrigatórios de `escrita-humana` com revisor após cada ciclo.
- Validação determinística antes de cada transição.
- Revisão obrigatória do research brief.
- Mínimo de duas fontes independentes no brief, quando disponíveis.
- Conexão explícita com a experiência/opiniões do autor.
- Manifesto persistente da execução e eventos por topic.
- Bloqueio individual e continuidade da fila após falha.

### Fora do escopo

- Publicar ou agendar automaticamente no LinkedIn dentro do lote editorial.
- Anexar imagens automaticamente.
- Processar múltiplos topics em paralelo.
- Publicações corporativas ou múltiplas contas.

## Seleção da fila

O comando aceitará uma seleção de 1 a X topics:

```text
--topics 1
--topics 3
--topics all
--topics topic_20260901_01,topic_20260901_03
```

O sistema deve:

1. Ler o backlog e os estados dos topics.
2. Considerar somente topics em `ready_for_research`.
3. Ordenar por score decrescente, salvo seleção explícita.
4. Resolver `all` como todos os topics elegíveis naquele instante.
5. Congelar a lista em um manifesto de execução.
6. Processar os itens na ordem congelada.

## Estados

```text
ready_for_research
  → researched
  → drafted
  → humanized
  → approved
```

Falha terminal por topic:

```text
blocked
```

O agendamento pode acrescentar metadado operacional ao arquivo aprovado, mas não faz parte da máquina de estados editorial.

## Contratos por etapa

Cada etapa terá um contrato próprio com:

- entradas obrigatórias;
- artefato esperado;
- critérios de aceitação;
- validações determinísticas;
- revisor responsável;
- transição permitida.

### Discover signals

Executa por frente e produz 20–50 signals com URL, data, observação, debate e evidências. Deve distinguir produção, piloto, promessa, resultado mensurável e problema de implantação em IA Aplicada.

### Cluster signals

Agrupa sinais por fenômeno comum. Um signal pode aparecer em no máximo um topic. Sinais sem grupo suficiente permanecem fora do topic.

### Score opportunities

Aplica a fórmula de `config/scoring.yaml`, ordena topics e atualiza o backlog. Não deve pontuar com base em potencial imaginado nem inflar `author_fit` sem conexão real na memória.

### Research topic

Executa `last30days`, abre URLs dos signals e busca fontes complementares. O brief deve conter fatos, opiniões, contrapontos, incertezas e riscos rastreáveis.

Requisitos obrigatórios:

- pelo menos duas fontes independentes, quando houver disponibilidade;
- ao menos uma fonte primária ou uma justificativa registrada para sua ausência;
- respostas às `research_questions` da frente;
- conexão explícita com `memory/`;
- declaração das limitações de cobertura.

O brief passa pelo Loop Gauntlet antes de mudar para `researched`.

### Write post

Escreve exclusivamente a partir do brief e das memórias do autor. Não pesquisa. Deve cumprir 900–1500 caracteres, 150–250 palavras, estrutura ABERTURA→SITUAÇÃO→APLICAÇÃO→PROBLEMA→DECISÃO→APRENDIZADO→PERGUNTA e seção `## Fontes`.

### Critique e correção

`critique-post` não reescreve. Produz feedback estruturado. O executor corrige o draft dentro do Loop Gauntlet.

Critérios do post, todos de 0 a 10:

- clareza;
- força da abertura;
- originalidade;
- credibilidade;
- uso de evidências;
- risco de alucinação;
- tom humano;
- densidade;
- relevância;
- consistência com a voz do autor;
- estrutura obrigatória;
- pergunta final;
- tamanho editorial;
- rastreabilidade das fontes.

Gate: nenhum critério abaixo de 9/10 e cobertura de pelo menos 99% dos requisitos (`coverage >= 0.99`).

### Escrita humana

Obrigatória em duas passagens:

```text
escrita-humana 1 → revisor 1 → escrita-humana 2 → revisor 2
```

Cada revisor deve usar a checklist da própria skill. A conformidade mínima é 95% dos itens aplicáveis, mas os seguintes requisitos são absolutos:

- zero padrões relevantes de IA;
- zero afirmações novas não presentes no brief;
- zero alteração de fonte, URL ou data;
- zero emojis e travessões proibidos;
- voz do autor preservada;
- tamanho e estrutura válidos.

Falha em requisito absoluto exige novo ciclo do Gauntlet, ainda que a conformidade geral seja superior a 95%.

## Loop Gauntlet

O Loop Gauntlet é um procedimento independente e reutilizável, não uma característica específica de uma skill.

```text
gauntlet(executor, reviewer, artifact, contract)
```

Para cada rodada:

1. iniciar rodada e registrar `cycle`;
2. criar tarefa nova para o executor;
3. fornecer contrato, estado, artefato e feedback completo;
4. exigir saída estruturada;
5. executar validações determinísticas;
6. criar tarefa nova para o revisor, sem reutilizar contexto;
7. exigir revisão estruturada;
8. aprovar se os gates passarem;
9. caso contrário, retornar feedback ao executor;
10. encerrar após 5 rodadas sem aprovação.

Resultado mínimo do revisor:

```json
{
  "decision": "approved | feedback",
  "coverage": 0.0,
  "criteria": {},
  "hard_failures": [],
  "feedback": [],
  "artifact": "path"
}
```

Após cinco rodadas sem aprovação, o topic recebe `blocked`, com motivo, critérios falhos, ciclos realizados e caminho do último artefato. A fila continua no próximo topic.

## Persistência e retomada

Cada execução criará:

```text
runs/<run_id>/manifest.yaml
runs/<run_id>/events.yaml
runs/<run_id>/topics/<topic_id>/state.yaml
runs/<run_id>/topics/<topic_id>/reviews/cycle-01.yaml
```

O manifesto conterá seleção, ordem, timestamp, versão dos contratos e estado de cada topic. Nenhuma decisão dependerá apenas do contexto da conversa.

## Agendamento e publicação

A skill `publicar-linkedin` será revisada separadamente com este contrato:

1. validar `content/approved/`;
2. converter Markdown para texto LinkedIn;
3. tentar primeiro visualização/controle com Playwright;
4. diante de ausência ou dificuldade, capturar screenshot;
5. usar visão nativa primeiro;
6. se falhar, delegar ao `image-analyzer` com `reason: native_failed`;
7. nunca inferir estado da tela sem evidência visual;
8. no reagendamento, usar `... → Alterar agenda`;
9. selecionar explicitamente data e horário, mesmo se o horário não mudar;
10. confirmar visualmente o resumo antes de avançar;
11. confirmar a tela final antes de agendar;
12. verificar a publicação em `Publicações agendadas`;
13. só então registrar `<!-- agendado: ... -->`;
14. se houver divergência, corrigir a publicação existente, sem criar duplicata.

## Falhas e segurança

- Falha de executor, revisor, contrato ou validação bloqueia somente o topic atual.
- Resposta inválida do revisor nunca aprova.
- Artefato ausente nunca permite transição.
- Credenciais, cookies, tokens e dados privados nunca entram em artefatos ou logs.
- O lote não publica nem agenda automaticamente.
- A execução deve poder ser retomada a partir do último checkpoint válido.

## Critérios de aceitação da implantação

- Seleciona corretamente 1, N e `all`.
- Processa topics em ordem, sem paralelismo editorial.
- Retoma após interrupção sem duplicar artefatos.
- Executa o Gauntlet com no máximo 5 ciclos.
- Usa executor e revisor em tarefas separadas.
- Bloqueia individualmente um topic que falhar e continua a fila.
- Exige brief revisado, fontes independentes e conexão autoral.
- Executa duas passagens de `escrita-humana` com dois revisores.
- Rejeita post com qualquer critério abaixo de 9/10.
- Rejeita post com padrão proibido de IA, mesmo com conformidade geral acima de 95%.
- Mantém fontes no final de drafts e aprovados.
- Mantém publicação/agendamento fora do lote editorial.
- Usa Playwright antes do fallback visual no agendamento.
- Registra agendamento somente após confirmação visual na lista do LinkedIn.
