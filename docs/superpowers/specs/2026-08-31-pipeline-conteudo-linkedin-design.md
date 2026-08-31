# Design — Pipeline de Conteúdo LinkedIn (recomeço)

**Data:** 2026-08-31
**Status:** Aprovado
**Base:** `linkedin_content_pipeline_SPEC.md` (draft v0.1)
**Decisão de contexto:** recomeço do zero; nada do histórico git anterior é aproveitado. Skills existentes em `.agents/skills/` são mantidas.

---

## 1. Visão geral

Pipeline agentico **manual** (sem scripts, sem automação) que transforma pesquisa em posts profissionais, com cada etapa gerando um artefato persistente e auditável:

```
frentes → sinais → debates → temas → oportunidades → tese → evidências → contexto do autor → post
```

**Princípios:**
- Simplicidade primeiro (spec §2.1) — sem multiagentes complexos, sem scripts, sem automação no MVP.
- Cada etapa gera um artefato persistente (spec §2.2).
- Pesquisa separada de redação (spec §2.3) — o writer não pesquisa.
- LinkedIn como fonte complementar, não principal (spec §2.4).
- Regra central (spec §29): nunca começar por "sobre o que escrever?" — sempre por "o que está acontecendo?" e "onde existe debate?".

## 2. Estrutura de diretórios

```
conteudo_linkedin/
├── AGENTS.md                  → contrato de operação; referencia mapa.md
├── mapa.md                    → guia de todas as skills (objetivo, vínculo, invocação)
├── README.md                  → visão geral do projeto
├── docs/
│   ├── roadmap.md             → ações futuras com status [ ] / [x]
│   └── superpowers/specs/     → specs de design
├── config/
│   ├── frentes.yaml           → as 5 frentes + prioridades + keywords
│   ├── sources.yaml           → fontes e pesos
│   ├── authors.yaml           → watchlist de autores (20-40)
│   └── scoring.yaml           → pesos da fórmula de score
├── research/
│   ├── signals/               → signals_YYYY-MM-DD.yaml (um por dia/rodada)
│   ├── topics/                → topics_YYYY-MM-DD.yaml
│   └── briefs/                → briefs/<topic_id>.md
├── content/
│   ├── backlog.md             → oportunidades ranqueadas
│   ├── drafts/                → rascunhos
│   ├── approved/              → aprovados (prontos p/ publicar)
│   └── published/             → publicados
└── memory/
    ├── professional_experience.md
    ├── opinions.md
    └── writing_style.md
```

Sem `scripts/` e `logs/` por enquanto (roadmap). Skills novas do pipeline em `.agents/skills/`.

## 3. Configuração

### 3.1. `config/frentes.yaml` — as 5 frentes

| Frente | Prioridade | Keywords (resumo) |
|---|---|---|
| IA Aplicada | 10 | AI in supply chain, AI operations, AI decision making, human in the loop, AI adoption barriers, AI automation failure |
| Logística, last mile e CX | 9 | last mile delivery, delivery speed cost tradeoff, logistics operational efficiency, food delivery operations, delivery reliability |
| Liderança em operações | 8 | operations leadership challenges, delegation and accountability, building trust, frontline workforce productivity, decision making under pressure |
| Riscos, compliance e resiliência | 8 | supply chain risk management, operational resilience, AI governance, food safety, supplier risk |
| Alimentos, consumo e sustentabilidade | 4 | food industry trends, functional foods, food supply chain innovation, circular economy, sustainable logistics |

**Guia de pesquisa da frente IA Aplicada (7 perguntas sofisticadas, embutidas na skill `discover-signals` e reutilizadas no `research-topic`):**
1. Quem está usando IA em produção, e para quê?
2. Que ganhos estão sendo relatados: tempo, custo, qualidade ou receita?
3. Quais aplicações falharam?
4. Onde a decisão humana continua indispensável?
5. Quais competências os líderes precisam desenvolver?
6. O debate está falando de automação ou de aumento da capacidade das equipes?
7. Quais casos são reais e quais são apenas marketing?

### 3.2. `config/sources.yaml` — fontes e pesos

Da spec §6: Reddit 8, Hacker News 6, imprensa 9, relatórios 10, blogs de empresa 7, LinkedIn público 7, busca web 8.

### 3.3. `config/authors.yaml` — watchlist

Lista limitada (20-40) de profissionais, empresas e pesquisadores relevantes por frente. Qualidade, não volume.

### 3.4. `config/scoring.yaml` — fórmula

Da spec §14: freshness .15, relevance .20, debate .15, evidence .10, author_fit .20, originality .10, linkedin_fit .10 → score 0-100.

## 4. Memória do autor (3 arquivos)

Preenchidos na implementação com base no contexto do autor (food delivery, operações, IA, CX) e **revisados/corrigidos pelo autor**:

- `memory/professional_experience.md` — fatos profissionais (gestão de operações, delivery, atendimento, SLA, FCR, automação, dados, processos).
- `memory/opinions.md` — opiniões (automação não é só cortar headcount; métrica boa induz comportamento certo; IA em processo ruim amplifica problema; etc.).
- `memory/writing_style.md` — regras de escrita (ver §6).

## 5. Skills do pipeline (7, em `.agents/skills/`)

| Skill | Entrada → Saída |
|---|---|
| `discover-signals` | frentes + last30days + busca manual → `research/signals/signals_*.yaml` (20-50 sinais) |
| `analyze-discussions` | 1 signal → análise do debate (opcional, sob demanda) |
| `cluster-signals` | signals → `research/topics/topics_*.yaml` (agrupa fenômenos) |
| `score-opportunities` | topics → notas 0-100 + `content/backlog.md` |
| `research-topic` | topic_id → `research/briefs/<topic_id>.md` |
| `write-post` | brief + memória → `content/drafts/<topic_id>.md` |
| `critique-post` | draft → críticas (clareza, originalidade, credibilidade, tom humano, densidade, risco de alucinação, clichês) |

**Skills existentes mantidas:**
- `last30days` — ferramenta primária de pesquisa do `discover-signals` (fontes ativas: Reddit, HN, YouTube, TikTok/Instagram/Threads via ScrapeCreators, LinkedIn opt-in, GitHub, Polymarket, Digg; X desligado; web keyless degradado).
- `publicar-linkedin` — publicação/agendamento via browser do OpenWork logado (atualizada com 4 melhorias: detalhes de agendamento, registro no arquivo, verificação pós-agendamento, erros comuns).
- `visao-nativa-primeiro` — política visual central (essencial: o modelo não lê imagens nativamente; delega ao `image-analyzer`).
- `orquestrador-runtime` — mantida na pasta, mas **fora do fluxo novo**; documentada no mapa.md como legado.
- `escrita-humana` — revisão obrigatória de todo post antes da aprovação.

## 6. Escrita dos posts

### 6.1. Formato

- **Tamanho**: 900–1500 caracteres / 150–250 palavras (padrão fixo).
- **Formato**: texto + imagem (anexo manual na publicação, via `publicar-linkedin`).

### 6.2. Esqueleto textual obrigatório

```
ABERTURA    → frase forte e específica (nunca genérica)
SITUAÇÃO    → contexto real, concreto
APLICAÇÃO   → ferramenta/aplicação específica
PROBLEMA    → o que deu errado / o limite encontrado
DECISÃO     → o que foi feito (com critério)
APRENDIZADO → o insight operacional
PERGUNTA    → fechamento que convida à conversa
```

### 6.3. Critérios de qualidade

- Experiência concreta > conceito.
- Liderança parte de tensão prática, não de frase motivacional.
- Casos de empresas e movimentos de mercado têm alto potencial.
- Abertura sempre com frase forte e específica (ex.: "O cliente percebe rapidamente quando a escolha da frota foi errada.").
- Densidade: uma ideia por post.

### 6.4. Revisão obrigatória

Todo post passa por `escrita-humana` antes da aprovação. Fluxo de produção:

```
research-topic → write-post → critique-post → escrita-humana → aprovação do autor → publicar-linkedin
```

## 7. Fluxo operacional

- **Diário**: `discover-signals` → 20-50 sinais.
- **2x/semana**: `cluster-signals` + `score-opportunities` → 5-10 oportunidades no backlog.
- **Ao publicar**: `research-topic` → `write-post` → `critique-post` → `escrita-humana` → aprovação → `publicar-linkedin`.

Estados de conteúdo: `discovered → clustered → candidate → ready_for_research → researched → drafted → approved → published → archived`.

## 8. Roadmap (`docs/roadmap.md`)

Itens futuros com `[ ]`/`[x]`:
- [ ] Configurar X na last30days (cookies do browser — grátis)
- [ ] Adicionar web key (Brave grátis) para elevar qualidade de imprensa/relatórios
- [ ] Scripts Python (scoring, cluster) quando o fluxo manual estabilizar
- [ ] Logs de execução
- [ ] Automação recorrente (Fase 6 da spec)
- [ ] Ajuste periódico das frentes conforme métricas de engajamento/posicionamento

## 9. Fora de escopo (MVP)

Publicação automática, scraping massivo, banco vetorial, orchestration framework complexo, scripts Python, logs estruturados, automação recorrente (spec §3).

## 10. Critério de sucesso

Da spec §28: por 4 semanas consecutivas — 5+ boas pautas/semana, fontes rastreáveis, sem temas repetitivos, briefs úteis, drafts com pouca reescrita, coerência com experiência/opinião do autor.
