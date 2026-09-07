# P2.3 Scoring e Fontes — Design

## Objetivo

Auditar a qualidade das fontes e avaliar o scoring editorial atual para produzir
uma recomendação de pesos baseada em evidência do próprio pipeline, sem alterar
a fórmula automaticamente e sem depender de métricas de engajamento.

## Escopo

Incluído:

- inventário da fórmula, critérios e pesos atuais;
- auditoria de uma amostra de signals e topics;
- classificação de fontes por qualidade e independência;
- comparação entre score previsto e decisões editoriais observadas;
- execução paralela da fórmula atual e de uma proposta alternativa;
- registro de hipótese, evidências, decisão e aprendizado.

Fora do escopo:

- automação recorrente;
- coleta de métricas do LinkedIn;
- publicação, agendamento ou alteração de posts;
- substituição automática dos pesos ativos;
- alteração de posicionamento editorial sem aprovação humana.

## Artefatos

- `research/topics/topics_scored_*.yaml`: entrada do scoring e scores
  calculados por rodada.
- `research/signals/signals_*.yaml`: sinais e fontes auditadas.
- `config/scoring.yaml`: fórmula e pesos ativos, caso a configuração exista;
  se a fórmula estiver em script, documentar o caminho do script.
- `research/audits/source-quality-*.yaml`: auditoria estruturada de fontes.
- `research/audits/scoring-comparison-*.yaml`: comparação entre scoring atual,
  proposta alternativa e decisões editoriais.
- `docs/roadmap.md`: decisão final e aprendizado acumulado.

## Modelo de auditoria de fonte

Cada fonte auditada deve registrar:

- `source_id` ou referência ao signal;
- tipo da fonte: primária, secundária, opinião, marketing ou comunidade;
- independência em relação às demais fontes;
- recência na data de coleta;
- verificabilidade por URL, título e data;
- conexão com a pergunta do topic;
- qualidade observada e justificativa textual;
- limitações e risco de inferência.

Uma fonte comercial ou um painel pode provar que existe uma afirmação ou debate,
mas não deve ser tratado automaticamente como prova de adoção, escala ou
resultado operacional.

## Avaliação do scoring

O diagnóstico deve separar:

1. **Score previsto:** resultado produzido pela fórmula antes da decisão.
2. **Decisão editorial:** selecionado, descartado, bloqueado, pesquisado,
   aprovado ou publicado.
3. **Qualidade observada:** evidência disponível após pesquisa, revisão e
   aprovação.

Falsos positivos são topics com score alto e evidência/aderência fraca. Falsos
negativos são topics com score baixo que demonstraram evidência, debate e
aderência suficientes após pesquisa. A classificação deve registrar a razão e
não pode usar desempenho de engajamento inexistente como proxy.

## Comparação de pesos

Uma proposta alternativa pode ajustar apenas pesos já existentes ou tornar
explícita uma dimensão que esteja ausente, desde que a mudança seja justificada
por exemplos auditados. O scoring atual e o alternativo devem rodar sobre o
mesmo conjunto congelado de topics, com a mesma escala e os mesmos dados.

O resultado deve mostrar:

- ranking atual e alternativo;
- topics que subiram, desceram ou permaneceram;
- critérios responsáveis por cada mudança;
- casos em que a proposta piora a seleção;
- recomendação de manter, testar ou rejeitar a proposta.

Nenhum peso ativo será substituído apenas porque uma proposta produz um ranking
mais conveniente. A substituição exige aprovação humana e registro da decisão.

## Fluxo e gates

1. Congelar a amostra e registrar data, arquivos e fingerprint.
2. Documentar a fórmula e os pesos atuais.
3. Auditar as fontes sem alterar os signals originais.
4. Comparar scores com as decisões editoriais e os briefs produzidos.
5. Formular uma hipótese de ajuste, se houver evidência suficiente.
6. Rodar scoring paralelo e revisar os casos divergentes.
7. Obter aprovação humana para alterar a configuração ativa.
8. Registrar a decisão e o aprendizado no roadmap.

Se a amostra for insuficiente ou as fontes não forem verificáveis, o resultado
deve ser `inconclusive`, sem alteração de pesos. Dados ausentes ficam ausentes;
nenhuma nota é inventada para completar a amostra.

## Critérios de sucesso

- A fórmula ativa está documentada com caminho e pesos verificáveis.
- Cada fonte auditada tem classificação, justificativa e limitação.
- A comparação usa um conjunto congelado e reproduzível.
- Falsos positivos e negativos são identificados ou declarados inconclusivos.
- A recomendação deixa claro o que muda, o que permanece e por quê.
- Nenhuma alteração ativa ocorre sem aprovação humana.
- Os artefatos e o aprendizado ficam persistidos no workspace.

## Aprendizado esperado

O P2.3 deve responder se os critérios atuais valorizam evidência, debate,
relevância, originalidade e aderência ao autor de forma coerente. O resultado
mais importante pode ser manter os pesos atuais com evidência de que a amostra
é pequena ou que uma mudança seria especulativa.
