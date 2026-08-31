# Conteúdo LinkedIn — Pipeline de Inteligência de Conteúdo

Pipeline agentico manual que transforma pesquisa em posts profissionais para LinkedIn.

Fluxo: frentes → sinais → debates → temas → oportunidades → tese → evidências → contexto do autor → post.

## Estrutura

- `config/` — frentes, fontes, autores, scoring
- `research/` — signals, topics, briefs
- `content/` — backlog, drafts, approved, published
- `memory/` — experiência profissional, opiniões, estilo de escrita
- `.agents/skills/` — skills do pipeline (ver `mapa.md`)

## Uso

1. `discover-signals` (diário) → 20-50 sinais
2. `cluster-signals` + `score-opportunities` (2x/semana) → 5-10 oportunidades
3. `research-topic` → `write-post` → `critique-post` → `escrita-humana` → aprovação → `publicar-linkedin`

Ver `mapa.md` para o guia de skills e `AGENTS.md` para o contrato de operação.

## Dependências

- PyYAML (para validar os YAML de config/ e research/): `pip install pyyaml`
