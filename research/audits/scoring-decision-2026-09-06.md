---
date: "2026-09-06"
decision: inconclusive
recommendation: keep_current
approval_required: human
artifacts:
  - research/audits/scoring-inventory-2026-09-06.yaml
  - research/audits/source-quality-2026-09-06.yaml
  - research/audits/scoring-comparison-2026-09-06.yaml
  - research/audits/scoring-parallel-2026-09-06.yaml
---

# Decisão de scoring

## Decisão

**inconclusive**. A recomendação é `keep_current`: manter os pesos ativos e não
substituir `config/scoring.yaml`. A evidência disponível não sustenta uma
alteração de pesos nem um teste alternativo como mudança operacional.

## Evidências

- `scoring-inventory-2026-09-06.yaml` reproduz a fórmula executável, a origem
  dos pesos e o fingerprint da amostra congelada.
- `source-quality-2026-09-06.yaml` classifica nove sinais. Há fontes de alta
  qualidade, mas também fontes promocionais, de verificabilidade limitada e
  conexões indiretas com manufatura; várias afirmações não têm metodologia,
  baseline ou resultado independente.
- `scoring-comparison-2026-09-06.yaml` classifica os cinco tópicos como
  `inconclusive`. Quatro têm divergência entre `score_status` e
  `backlog_status`; o quinto não tem qualidade observada.
- `scoring-parallel-2026-09-06.yaml` mostra que a alternativa preserva as
  posições 1, 4 e 5 e troca apenas as posições 2 e 3. Isso demonstra
  sensibilidade dos pesos, não superioridade preditiva.
- A amostra paralela tem cinco tópicos, `author_fit: 0` em todos e não inclui
  métricas de desempenho ou engajamento do LinkedIn.

## Limitações

- Não há amostra comparável de resultados publicados para medir acertos, falsos
  positivos ou falsos negativos.
- O backlog ainda contém tópicos em `ready_for_research`, portanto a decisão
  editorial não pode ser reconciliada com resultado observado.
- A auditoria de fontes usa os campos persistidos nos signals; não houve
  verificação externa, transcrição nova ou validação dos dados quantitativos.
- Os pesos alternativos foram comparados na mesma amostra congelada, sem
  validação fora da amostra.

## O que não mudou

- `config/scoring.yaml` permanece byte a byte inalterado.
- A fórmula em `score_opportunities.py` permanece inalterada.
- Nenhum signal, tópico, post, brief ou estado de backlog foi alterado por esta
  decisão.
- Não foi criado nem executado teste de produção com pesos alternativos.
- Nenhuma ação de navegador do LinkedIn foi executada; nada foi publicado ou
  agendado.

## Próxima condição de revisão

Uma revisão de pesos só deve ocorrer com uma amostra maior e comparável, com
decisões editoriais reconciliadas, qualidade de fontes verificável e resultados
observados. Qualquer `test_alternative` deve ser isolado, documentado e
precedido de **aprovação humana** explícita.

## Aprovação humana

Esta decisão é um registro técnico conservador e não substitui aprovação
humana para alterar pesos, executar um experimento alternativo, publicar ou
agendar conteúdo.
