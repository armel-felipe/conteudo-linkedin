# P1-C — Scoring e clustering automatizados

**Data:** 2026-09-06  
**Status:** aprovado pelo usuário

## Objetivo

Automatizar scoring e clustering de signals/topics persistidos com scripts
determinísticos e separados, preservando a separação entre pesquisa e redação.

## Arquitetura

`score_opportunities.py` lê `config/scoring.yaml` e calcula scores ponderados de
0 a 100. `cluster_signals.py` agrupa signals por pilares, termos e lados do
debate. Cada script tem uma única responsabilidade, aceita arquivos de entrada
explícitos e gera artefatos persistentes sem escrever briefs ou posts.

## Entradas e saídas

- Entrada de scoring: `research/topics/*.yaml` e `config/scoring.yaml`.
- Saída de scoring: topic YAML com critérios e total recalculados.
- Entrada de clustering: `research/signals/*.yaml`.
- Saída de clustering: artefato YAML em `research/topics/` com grupos e ids.
- Entradas vazias produzem saída vazia válida.
- Entradas duplicadas ou inválidas produzem erro explícito e não sobrescrevem
  artefatos existentes.

## Regras

- Pesos são lidos do arquivo de configuração; não ficam duplicados no código.
- Cada critério é validado no intervalo 0–10.
- A soma dos pesos deve ser 1.0.
- Score final é `sum(critério × peso) × 10`, arredondado de forma determinística.
- Clusters preservam ids de signals, pilares, títulos e evidências sem inventar
  fatos ou fontes.
- Nenhum script produz brief, draft ou post.

## Testes e aceite

- Fixtures cobrem scoring normal, pesos inválidos e critérios fora do intervalo.
- Fixtures cobrem clustering por pilar/debate, entrada vazia, ids duplicados e
  signal sem campos obrigatórios.
- Saídas são estáveis entre duas execuções iguais.
- Suite existente continua passando.
- Artefatos reais só são escritos depois de todos os testes passarem.
