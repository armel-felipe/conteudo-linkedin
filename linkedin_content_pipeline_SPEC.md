# SPEC — LinkedIn Content Intelligence Pipeline

**Status:** Draft v0.1  
**Objetivo:** Construir um pipeline agentico, simples, auditável e consistente para descobrir temas, identificar debates relevantes, gerar pautas, pesquisar evidências e produzir posts profissionais para LinkedIn.

---

## 1. Problema

O processo atual de criação de conteúdo depende de uma skill ampla de pesquisa (`last-30-days`) que tenta encontrar tendências e produzir contexto diretamente para geração de posts.

Esse fluxo apresenta problemas:

- resultados inconsistentes;
- excesso de ruído;
- pouca rastreabilidade;
- dificuldade de distinguir fato, opinião e tendência;
- baixa repetibilidade;
- dependência excessiva de buscas diretas no LinkedIn;
- dificuldade para entender por que uma pauta foi escolhida;
- tendência da IA a produzir textos genéricos.

O projeto deve substituir o fluxo:

```text
tema → pesquisa → post
```

por:

```text
fontes
→ sinais
→ debates
→ temas
→ oportunidades
→ tese
→ evidências
→ contexto pessoal/profissional
→ post
```

---

# 2. Princípios do projeto

## 2.1. Simplicidade primeiro

Não utilizar arquitetura complexa de multiagentes enquanto o pipeline básico não estiver estável.

A primeira versão deve funcionar com:

- arquivos Markdown;
- arquivos YAML;
- arquivos JSON;
- scripts Python;
- skills/agentes especializados;
- execução manual ou semiautomática.

---

## 2.2. Cada etapa gera um artefato

Nenhuma etapa deve depender apenas do contexto de conversa de um agente.

Cada estágio deve produzir um arquivo persistente.

Exemplo:

```text
discover-signals
    ↓
signals.json

cluster-signals
    ↓
topics.json

score-opportunities
    ↓
content_backlog.md

research-topic
    ↓
brief.md

write-post
    ↓
draft.md
```

---

## 2.3. Separar pesquisa de redação

O agente responsável por encontrar sinais não deve escrever posts.

O agente responsável por escrever posts deve receber um briefing estruturado.

---

## 2.4. LinkedIn não será a única fonte

O pipeline deve tratar LinkedIn como uma fonte complementar de sinal profissional.

As principais camadas de pesquisa serão:

### Conversa
- Reddit
- Hacker News
- fóruns
- comunidades públicas

### Fatos
- veículos de imprensa
- blogs especializados
- releases
- sites institucionais

### Evidências
- relatórios
- pesquisas
- estudos
- bases estatísticas

### Ambiente profissional
- posts públicos do LinkedIn;
- conteúdos indexados em mecanismos de busca;
- autores acompanhados manualmente.

---

# 3. Escopo inicial

O MVP deve fazer cinco coisas bem:

1. Encontrar sinais relevantes.
2. Agrupar sinais relacionados.
3. Identificar oportunidades de conteúdo.
4. Criar um briefing confiável.
5. Gerar um post alinhado ao estilo do autor.

Não faz parte do MVP:

- publicação automática no LinkedIn;
- scraping massivo;
- crescimento automático de rede;
- comentários automáticos;
- mensagens automáticas;
- otimização de engajamento artificial;
- banco vetorial;
- orchestration framework complexo.

---

# 4. Estrutura de diretórios

```text
linkedin-content/
│
├── README.md
├── SPEC.md
│
├── config/
│   ├── pillars.yaml
│   ├── sources.yaml
│   ├── authors.yaml
│   └── scoring.yaml
│
├── research/
│   ├── signals/
│   ├── topics/
│   └── briefs/
│
├── content/
│   ├── backlog.md
│   ├── drafts/
│   ├── approved/
│   └── published/
│
├── memory/
│   ├── professional_experience.md
│   ├── opinions.md
│   ├── writing_style.md
│   └── successful_posts.md
│
├── skills/
│   ├── discover-signals/
│   ├── analyze-discussions/
│   ├── cluster-signals/
│   ├── score-opportunities/
│   ├── research-topic/
│   ├── write-post/
│   └── critique-post/
│
├── scripts/
│   ├── collect_signals.py
│   ├── cluster_signals.py
│   ├── score_topics.py
│   └── build_backlog.py
│
└── logs/
```

---

# 5. Configuração dos pilares

Arquivo:

```text
config/pillars.yaml
```

Exemplo inicial:

```yaml
pillars:

  operations:
    name: Operações
    priority: 10

    keywords:
      - operations
      - operational excellence
      - productivity
      - service operations
      - process improvement
      - efficiency

  artificial_intelligence:
    name: Inteligência Artificial aplicada aos negócios
    priority: 10

    keywords:
      - artificial intelligence
      - generative AI
      - AI agents
      - LLM
      - automation
      - AI operations

  customer_experience:
    name: Customer Experience
    priority: 8

    keywords:
      - customer experience
      - customer success
      - customer service
      - support operations
      - service automation

  leadership:
    name: Liderança
    priority: 7

    keywords:
      - leadership
      - management
      - decision making
      - high performance teams

  data:
    name: Dados e tomada de decisão
    priority: 9

    keywords:
      - data driven
      - analytics
      - business intelligence
      - metrics
      - decision making
```

---

# 6. Fontes

Arquivo:

```text
config/sources.yaml
```

Estrutura:

```yaml
sources:

  reddit:
    enabled: true
    weight: 8

  hacker_news:
    enabled: true
    weight: 6

  news:
    enabled: true
    weight: 9

  reports:
    enabled: true
    weight: 10

  company_blogs:
    enabled: true
    weight: 7

  linkedin_public:
    enabled: true
    weight: 7

  google_search:
    enabled: true
    weight: 8
```

---

# 7. Watchlist de autores

Arquivo:

```text
config/authors.yaml
```

Objetivo:

manter uma lista limitada de profissionais, empresas e pesquisadores relevantes.

Exemplo:

```yaml
authors:

  artificial_intelligence:
    - name: ""
      linkedin: ""
      notes: ""

  operations:
    - name: ""
      linkedin: ""
      notes: ""

  customer_experience:
    - name: ""
      linkedin: ""
      notes: ""
```

Meta inicial:

```text
20 a 40 autores
```

Não buscar volume.

Buscar qualidade.

---

# 8. Objeto Signal

O Signal é a unidade básica da pesquisa.

Cada descoberta relevante deve ser convertida em um Signal.

Formato recomendado:

```yaml
id: signal_20260831_001

title: "Empresas estão ampliando uso de agentes de IA no suporte"

pillar:
  - artificial_intelligence
  - customer_experience

source:
  type: article
  publisher: Example
  url: https://...
  published_at: 2026-08-30

observation:
  "Empresas estão utilizando agentes de IA para resolver interações de suporte sem intervenção humana."

debate:

  side_a:
    "A automação reduz custos e tempo de atendimento."

  side_b:
    "Automação excessiva pode aumentar frustração e reincidência."

evidence:
  - "..."
  - "..."

possible_angle:
  "Automatizar um processo ruim apenas acelera um processo ruim."

author_connection:
  "Experiência com atendimento, SLA, FCR e automação operacional."

scores:

  freshness: 9
  relevance: 10
  debate: 8
  evidence: 7
  author_fit: 10

created_at: 2026-08-31
```

---

# 9. Descoberta de sinais

Skill:

```text
discover-signals
```

Responsabilidade:

buscar novos acontecimentos, discussões e ideias relacionadas aos pilares.

A skill NÃO deve:

- criar posts;
- definir opinião final;
- inventar dados;
- resumir apenas notícias populares.

Deve procurar:

- acontecimentos recentes;
- discussões com opiniões divergentes;
- mudanças de comportamento;
- novas tecnologias;
- pesquisas recentes;
- decisões controversas;
- cases;
- falhas;
- aprendizados;
- novas práticas.

---

# 10. Pergunta central da descoberta

A skill deve tentar responder:

```text
Sobre o que profissionais inteligentes estão discutindo,
discordando ou mudando de opinião?
```

e não apenas:

```text
O que está trending?
```

---

# 11. Análise de discussões

Skill:

```text
analyze-discussions
```

Entrada:

```text
Signal
```

Saída:

```yaml
discussion:

  question:
    "Qual é o verdadeiro impacto da automação de atendimento?"

  position_a:
    "Automação deve maximizar deflection."

  position_b:
    "Automação deve maximizar resolução."

  disagreement:
    "O conflito está em custo vs qualidade."

  unanswered_question:
    "Qual indicador determina quando a automação passou do limite?"

  content_opportunity:
    "Discutir FCR como métrica superior ao simples deflection."
```

---

# 12. Clusterização

Skill:

```text
cluster-signals
```

Objetivo:

agrupar Signals que tratam do mesmo fenômeno.

Exemplo:

```text
Signal 1
AI agents em customer service

Signal 2
empresa reduz 30% do atendimento humano

Signal 3
clientes reclamam de chatbot

Signal 4
novo benchmark sobre AI support
```

Cluster:

```text
AI + automação de atendimento
```

---

# 13. Objeto Topic

Formato:

```yaml
id: topic_20260831_01

title:
  "Automação de atendimento está sendo medida pela métrica errada"

pillars:
  - artificial_intelligence
  - customer_experience
  - operations

signals:
  - signal_20260831_001
  - signal_20260831_002
  - signal_20260831_006

central_question:
  "Estamos medindo automação por deflection quando deveríamos medir resolução?"

possible_thesis:
  "O objetivo de uma automação não deveria ser evitar contato humano.
   Deveria ser resolver o problema."

author_connection:
  strong

status:
  candidate
```

---

# 14. Scoring de oportunidades

Skill:

```text
score-opportunities
```

Cada topic recebe nota de 0 a 10 em:

```text
freshness
relevance
debate
evidence
author_fit
originality
linkedin_fit
```

Fórmula inicial:

```text
score =
freshness * 0.15
+ relevance * 0.20
+ debate * 0.15
+ evidence * 0.10
+ author_fit * 0.20
+ originality * 0.10
+ linkedin_fit * 0.10
```

Resultado final:

```text
0-100
```

---

# 15. Content Backlog

Arquivo:

```text
content/backlog.md
```

Formato:

```markdown
# Content Backlog

## 92 — Automação está sendo medida pela métrica errada

Pilares:
AI / Customer Experience / Operations

Tese:
O objetivo da automação não deveria ser reduzir contato humano,
mas aumentar resolução.

Por que agora:
...

Evidências disponíveis:
3

Experiência pessoal relacionada:
Alta

Status:
Ready for research
```

---

# 16. Research Topic

Skill:

```text
research-topic
```

Essa skill é executada apenas quando uma pauta for escolhida.

Entrada:

```text
topic_id
```

Objetivo:

fazer pesquisa aprofundada.

Deve buscar:

- fatos;
- números;
- estudos;
- opiniões relevantes;
- exemplos;
- contrapontos;
- riscos;
- contexto histórico.

---

# 17. Research Brief

Saída:

```text
research/briefs/<topic_id>.md
```

Estrutura:

```markdown
# Research Brief

## Tema

...

## Pergunta

...

## Tese potencial

...

## O que está acontecendo

...

## Evidências

### Evidência 1

Fonte:
URL:
Data:

Resumo:

### Evidência 2

...

## Argumentos favoráveis

...

## Argumentos contrários

...

## Pontos ainda incertos

...

## Conexão com experiência profissional

...

## Possíveis ângulos

1.
2.
3.

## Riscos de afirmações não verificadas

...
```

---

# 18. Memória profissional

O projeto precisa manter contexto real do autor.

Arquivo:

```text
memory/professional_experience.md
```

Deve conter apenas fatos profissionais relevantes que possam ser utilizados nos textos.

Exemplos:

- gestão de operações;
- atendimento;
- Customer Experience;
- SLA;
- FCR;
- produtividade;
- gestão de equipes;
- automação;
- dados;
- processos;
- tecnologia;
- decisões operacionais.

Objetivo:

evitar posts genéricos.

---

# 19. Banco de opiniões

Arquivo:

```text
memory/opinions.md
```

Formato:

```markdown
## Automação

Automação não deve ser usada apenas para reduzir headcount.

## Métricas

Uma boa métrica precisa induzir o comportamento correto.

## Inteligência Artificial

IA aplicada em processo ruim tende a amplificar problemas existentes.
```

Esse arquivo pode evoluir conforme novos posts forem produzidos.

---

# 20. Perfil de escrita

Arquivo:

```text
memory/writing_style.md
```

Deve conter:

- tom;
- vocabulário;
- tamanho médio;
- estrutura;
- tipos de abertura;
- frases que devem ser evitadas;
- nível de informalidade;
- preferência por primeira pessoa;
- uso de dados;
- uso de storytelling;
- CTA.

---

# 21. Write Post

Skill:

```text
write-post
```

Entrada obrigatória:

```text
Research Brief
Professional Experience
Opinions
Writing Style
```

O writer não deve pesquisar.

Ele deve escrever apenas com o material recebido.

---

# 22. Estrutura recomendada do post

Modelo inicial:

```text
HOOK

observação / problema

↓

CONTEXTO

o que está acontecendo

↓

TESE

qual é a visão do autor

↓

ARGUMENTAÇÃO

dados
experiência
exemplo

↓

INSIGHT

o que isso significa na prática

↓

FECHAMENTO

pergunta
reflexão
ou conclusão
```

---

# 23. Critique Post

Skill:

```text
critique-post
```

Objetivo:

criticar a primeira versão antes da aprovação.

Critérios:

```text
clareza
originalidade
credibilidade
tom humano
densidade
relevância
consistência
uso de evidências
risco de alucinação
linguagem genérica de IA
```

A skill deve procurar especificamente frases como:

```text
"Em um mundo cada vez mais..."
"A inteligência artificial veio para..."
"Mais do que nunca..."
"Não é sobre X, é sobre Y..."
```

quando utilizadas de maneira genérica ou clichê.

---

# 24. Workflow operacional

## Diário

Executar:

```text
discover-signals
```

Objetivo:

```text
20 a 50 sinais
```

---

## Duas vezes por semana

Executar:

```text
cluster-signals
score-opportunities
build-backlog
```

Objetivo:

produzir:

```text
5 a 10 oportunidades
```

---

## Quando houver intenção de publicar

Selecionar:

```text
topic_id
```

Executar:

```text
research-topic
write-post
critique-post
```

---

# 25. Estados de conteúdo

Um Topic pode assumir:

```text
discovered
clustered
candidate
ready_for_research
researched
drafted
approved
published
archived
```

---

# 26. Logs

Cada execução deve registrar:

```yaml
timestamp:
skill:
inputs:
outputs:
model:
duration:
errors:
```

Isso permitirá identificar onde o pipeline está falhando.

---

# 27. Métricas do sistema

Inicialmente medir:

```text
signals encontrados por execução
signals aproveitados
topics criados
topics aprovados
posts gerados
posts publicados
tempo médio até post
taxa de rejeição de drafts
```

Posteriormente:

```text
impressions
reactions
comments
saves
profile views
follows
```

---

# 28. Critério de sucesso do MVP

O sistema será considerado funcional quando conseguir, por quatro semanas consecutivas:

1. gerar pelo menos 5 boas pautas por semana;
2. apresentar fontes rastreáveis;
3. evitar temas repetitivos;
4. gerar briefs úteis;
5. produzir drafts que exijam pouca reescrita manual;
6. manter coerência com a experiência e opinião do autor.

---

# 29. Regra central

O sistema nunca deve começar pela pergunta:

```text
"Sobre o que devemos escrever?"
```

Deve começar por:

```text
"O que está acontecendo?"
```

seguido de:

```text
"Onde existe debate?"
```

depois:

```text
"Existe algo relevante que o autor possa acrescentar?"
```

e apenas então:

```text
"Isso merece virar um post?"
```

---

# 30. MVP — Ordem de implementação

## Fase 1

Criar:

```text
config/pillars.yaml
config/sources.yaml
memory/professional_experience.md
memory/opinions.md
memory/writing_style.md
```

---

## Fase 2

Implementar:

```text
discover-signals
```

Validar manualmente os Signals.

---

## Fase 3

Implementar:

```text
cluster-signals
score-opportunities
```

Gerar backlog.

---

## Fase 4

Implementar:

```text
research-topic
```

Validar qualidade das evidências.

---

## Fase 5

Implementar:

```text
write-post
critique-post
```

---

## Fase 6

Automatizar execução recorrente.

---

# 31. Princípio final

A finalidade do sistema não é automatizar a criação de posts.

A finalidade é construir uma máquina de:

```text
inteligência de conteúdo
```

que identifica assuntos sobre os quais o autor possui contexto,
experiência ou opinião suficientemente relevantes para contribuir
com uma discussão profissional.

A geração do texto é apenas a última etapa.
