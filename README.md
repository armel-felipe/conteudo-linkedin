# Conteúdo LinkedIn — Pipeline de Inteligência de Conteúdo

Pipeline agentico manual para transformar pesquisa em posts relevantes no LinkedIn.

O projeto começa pelo que está acontecendo e onde existe debate. Só depois escolhe uma oportunidade, pesquisa o tema, escreve e revisa o post.

```text
frentes → sinais → debates → temas → oportunidades → tese → evidências
→ contexto do autor → post → revisão → aprovação → publicação
```

## Estado atual

Este é o MVP manual. **Ainda não existe uma CLI própria nem scripts Python do pipeline.** As etapas são executadas pelo agente/OpenWork a partir das skills em `.agents/skills/`, e cada etapa salva um artefato no workspace.

O pipeline não publica automaticamente. A publicação é feita pela skill `publicar-linkedin`, usando a sessão já autenticada do browser do OpenWork.

## Pré-requisitos

- OpenWork/OpenCode com acesso a este workspace.
- Skill `last30days` disponível em `.agents/skills/last30days/`.
- Python 3.12+ para executar o engine do `last30days` quando necessário.
- `PyYAML` apenas para validar os arquivos YAML: `pip install pyyaml`.
- Sessão do LinkedIn já autenticada no browser do OpenWork, somente para publicar.

### Configuração inicial

Se ainda não houver um `.env` local:

```bash
cp .env.example .env
```

O `.env.example` contém o comando portátil da pesquisa:

```env
LAST30DAYS_COMMAND=python3 ".agents/skills/last30days/scripts/last30days.py" --emit=compact --days=30
```

O `.env` é local e nunca deve ser commitado. Credenciais opcionais de fontes ficam somente nele.

## Onde configurar o projeto

Antes da primeira rodada, confira:

| Arquivo | Função |
|---|---|
| `config/frentes.yaml` | Frentes, prioridades, keywords e perguntas de pesquisa |
| `config/sources.yaml` | Fontes disponíveis e pesos |
| `config/authors.yaml` | Autores para acompanhar; pode começar vazio |
| `config/scoring.yaml` | Critérios e pesos do ranking |
| `memory/professional_experience.md` | Experiências que podem fundamentar os posts |
| `memory/opinions.md` | Opiniões e posições do autor |
| `memory/writing_style.md` | Voz, estrutura, tamanho e restrições de escrita |

As memórias atuais são rascunhos e devem ser revisadas pelo autor antes de serem tratadas como definitivas.

## Como rodar o pipeline

As frases abaixo são as invocações usadas no OpenWork. O agente deve ler a skill correspondente, executar somente aquela etapa e salvar o artefato indicado.

### Ponto de entrada atual: lote editorial

Para executar pesquisa e redação de vários topics, use `run-editorial-batch`. A skill seleciona somente topics `ready_for_research`, congela a fila em `runs/<run_id>/manifest.yaml`, processa um topic por vez e marca uma falha individual como `blocked` antes de continuar.

```text
Rode run-editorial-batch --topics 1
Rode run-editorial-batch --topics 5
Rode run-editorial-batch --topics all
Rode run-editorial-batch --topics topic_20260831_01,topic_20260831_03
```

O lote retoma do último checkpoint válido e nunca publica automaticamente. `orquestrador-runtime` permanece disponível apenas como legado e não é o ponto de entrada do fluxo novo.

Cada etapa grava seu artefato, estado e evento; cada resultado de revisor é preservado por ciclo. Na retomada, somente etapas com artefato válido e review aprovado são puladas. Um topic aprovado nunca é reexecutado automaticamente. Um topic `blocked` retoma no mesmo estágio com fingerprint, review, feedback e `cycle_count` preservados. O manifesto também registra `queue_size`, `completed`, `blocked`, `cycles_per_stage`, `reviewer_coverage`, `human_writing_conformity` e `time_to_approval`; as três últimas métricas são, respectivamente, média de todos os `coverage`, média dos dois reviews `humanize_review_*` e duração ISO-8601 entre criação do manifesto e commit de `approval_humana`.

### 1. Descobrir sinais — diariamente

**Pedido ao agente:**

```text
Rode discover-signals para as cinco frentes do projeto.
```

Para uma rodada mais focada:

```text
Rode discover-signals somente para a frente ia_aplicada.
```

**Entrada:** `config/frentes.yaml`, `config/sources.yaml` e a pesquisa `last30days`.

**Saída:** `research/signals/signals_YYYY-MM-DD.yaml`, com aproximadamente 20–50 sinais por execução.

Cada signal deve ter fonte, URL, data, observação, debate, evidências, possível ângulo, conexão com o autor e status `discovered`.

Para a frente **IA Aplicada**, a pesquisa verifica também:

- quem usa IA em produção e para quê;
- ganhos relatados em tempo, custo, qualidade ou receita;
- aplicações que falharam;
- pontos em que a decisão humana continua indispensável;
- competências exigidas dos líderes;
- automação versus aumento da capacidade das equipes;
- casos reais versus marketing.

### 2. Aprofundar um debate — opcional

Use quando um signal tiver conflito, posições divergentes ou potencial especial.

**Pedido ao agente:**

```text
Analise o debate do signal signal_YYYYMMDD_001 usando analyze-discussions.
```

**Entrada:** um signal em `research/signals/`.

**Saída:** bloco `discussion:` no signal, com pergunta central, posição A, posição B, desacordo, pergunta sem resposta e oportunidade de conteúdo.

### 3. Agrupar sinais em temas — duas vezes por semana

**Pedido ao agente:**

```text
Rode cluster-signals sobre os signals ainda não agrupados.
```

**Entrada:** `research/signals/signals_*.yaml`.

**Saída:** `research/topics/topics_YYYY-MM-DD.yaml`.

Signals agrupados recebem status `clustered`. Cada topic nasce com status `candidate` e contém os sinais relacionados, a pergunta central, uma tese possível e a conexão com o autor.

### 4. Pontuar oportunidades — duas vezes por semana

**Pedido ao agente:**

```text
Rode score-opportunities sobre os topics candidatos.
```

**Entrada:** `research/topics/topics_*.yaml` e `config/scoring.yaml`.

**Saída:** `content/backlog.md`, ordenado por score.

Cada topic recebe nota de 0 a 10 em sete critérios:

```text
freshness       15%
relevance       20%
debate          15%
evidence        10%
author_fit      20%
originality     10%
linkedin_fit    10%
```

A soma ponderada é multiplicada por 10, gerando score final de 0 a 100. Os melhores topics recebem status `ready_for_research` no arquivo `research/topics/topics_*.yaml`.

### 5. Execução editorial — somente pelo lote

Para uma rodada, não invoque as etapas editoriais abaixo isoladamente: escolha os topics via `run-editorial-batch`, que congela a fila, executa a sequência completa e registra checkpoints. Pedidos isolados continuam permitidos fora de uma rodada batch, para trabalho sob demanda em um único topic.

**Pedido ao agente:**

```text
Rode `run-editorial-batch --topics topic_YYYYMMDD_01`.
```

**Entrada:** topic escolhido, signals relacionados, `last30days` e busca web manual.

**Saída:** `research/briefs/topic_YYYYMMDD_01.md`.

O brief deve conter fatos, números, estudos, argumentos favoráveis e contrários, incertezas, conexão com a experiência do autor, ângulos possíveis e riscos de afirmações não verificadas. Toda evidência precisa ter fonte, URL e data.

Depois dessa etapa, revise o brief. Se faltar evidência ou contexto, peça uma nova pesquisa antes de escrever.

### 6. Contrato das etapas do lote

Só execute depois que o brief estiver pronto e revisado.

Dentro do lote, as etapas são chamadas nesta ordem: `research-topic` → `brief_review_gauntlet` → `write-post` → `critique-post` → `correction_gauntlet` → `humanize_pass_1` → `humanize_review_1` → `humanize_pass_2` → `humanize_review_2` → `approval_humana`.

**Entrada:** `research/briefs/topic_YYYYMMDD_01.md` e os três arquivos em `memory/`.

**Saída:** `content/drafts/topic_YYYYMMDD_01.md`.

O post deve ter:

- 900–1500 caracteres;
- 150–250 palavras;
- texto + imagem prevista para anexo manual;
- uma ideia principal;
- abertura forte e específica;
- situação real;
- ferramenta ou aplicação específica;
- problema encontrado;
- decisão tomada;
- aprendizado operacional;
- pergunta final.

O writer não faz pesquisa nova. Todo fato precisa estar no brief. O arquivo deve terminar com `## Fontes`, listando título, URL e data das fontes usadas.

### 7. Artefatos produzidos pelo lote

O lote persiste `runs/<run_id>/manifest.yaml` e `runs/<run_id>/topics/<topic_id>/state.yaml`, além dos artefatos editoriais de cada etapa.

Fora de uma rodada batch, também é permitido pedir `critique-post` isoladamente para um draft.

A crítica verifica clareza, originalidade, credibilidade, tom humano, densidade, relevância, consistência, evidências, risco de alucinação e clichês de IA.

O agente deve apontar problemas específicos e sugerir correções, mas não substituir o texto inteiro automaticamente.

### 8. Revisar com escrita humana — obrigatório

Depois da crítica e dos ajustes necessários, o lote executa duas passagens independentes:

Fora de uma rodada batch, também é permitido pedir `escrita-humana` isoladamente para um draft.

Essa revisão preserva sua voz, remove padrões de texto genérico e verifica novamente clareza, naturalidade, fontes, tamanho e estrutura.

### 9. Aprovar

Leia o draft revisado. Só depois da sua aprovação o arquivo pode ir para `content/approved/`.

O arquivo aprovado deve manter:

- o texto final;
- a seção `## Fontes` no final;
- as fontes herdadas do brief;
- nenhuma afirmação sem origem rastreável.

### 10. Publicar ou agendar no LinkedIn

**Publicação imediata:**

```text
Publique content/approved/topic_YYYYMMDD_01.md agora.
```

**Agendamento:**

```text
Agende content/approved/topic_YYYYMMDD_01.md para 2026-09-10 às 09:00, horário de São Paulo.
```

A skill `publicar-linkedin` usa a sessão logada do browser. Para agendamento, ela confirma data e hora no seletor, verifica o post em “Ver publicações agendadas” e registra o horário no arquivo:

```markdown
<!-- agendado: 2026-09-10T09:00 America/Sao_Paulo -->
```

A imagem continua sendo anexada manualmente quando necessário. A aprovação editorial é separada da operação de publicação/agendamento: somente um arquivo em `content/approved/` pode entrar nessa etapa.

Na publicação pelo browser, a primeira tentativa é sempre Playwright. Para confirmações visuais, a rota é `screenshot + visão nativa → image-analyzer(native_failed) → stop`; o fallback não substitui evidência visual. O agendamento exige seleção explícita de data e horário, nova seleção do horário após trocar a data, resumo visual antes de `Avançar`, prévia final antes de `Agendar` e confirmação em `Publicações agendadas`. Para alterar um post existente, use `... → Alterar agenda`, nunca um compositor novo. O timestamp só é registrado no arquivo aprovado depois da confirmação na lista.

## Sequência resumida

```text
1. discover-signals
2. analyze-discussions (opcional)
3. cluster-signals
4. score-opportunities
5. `run-editorial-batch`
6. aprovação humana
7. `publicar-linkedin` (somente após aprovação, fora do lote)
```

Dentro de `run-editorial-batch`, não pule a revisão do brief, a crítica, a correção Gauntlet, as duas revisões com `escrita-humana` nem a aprovação humana. `orquestrador-runtime` continua legado e não deve ser usado como alternativa.

O agendamento permanece separado do lote e pertence ao plano de publicação do LinkedIn. Só chame `publicar-linkedin` depois da aprovação humana e por solicitação explícita.

## Estados dos artefatos

```text
discovered → clustered → candidate → ready_for_research → researched
→ drafted → approved → published → archived
```

Os estados dos topics ficam em `research/topics/topics_*.yaml`. Os arquivos de posts ficam em `content/drafts/`, `content/approved/` e `content/published/`.

## Estrutura

- `config/` — frentes, fontes, autores e scoring
- `research/signals/` — sinais coletados
- `research/topics/` — agrupamentos e oportunidades
- `research/briefs/` — briefs de pesquisa
- `content/backlog.md` — oportunidades ranqueadas
- `content/drafts/` — posts em elaboração
- `content/approved/` — posts aprovados
- `content/published/` — posts publicados
- `memory/` — experiência, opiniões e estilo
- `.agents/skills/` — skills do pipeline
- `editorial_batch.py` — contratos reutilizáveis de seleção e persistência do batch; não é uma CLI própria
- `docs/roadmap.md` — ações futuras
- `mapa.md` — guia de todas as skills
- `AGENTS.md` — contrato de operação

## Skills e documentação

Consulte `mapa.md` para saber o objetivo, o vínculo e a invocação de cada skill. Consulte `AGENTS.md` antes de alterar o fluxo.

O roadmap está em `docs/roadmap.md`. Ele controla melhorias futuras como configurar X, melhorar a busca web, adicionar scripts, logs e automação.

## Segurança

- Nunca commite `.env` ou credenciais.
- Não coloque tokens, cookies ou chaves de API em posts, briefs ou memória.
- A publicação usa somente a sessão já logada do browser do OpenWork.
