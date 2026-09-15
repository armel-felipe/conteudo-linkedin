# Content Backlog

> Temas com `status: ready_for_research` nos arquivos `research/topics/topics_*.yaml`.
> Temas já `approved` não aparecem aqui nem são elegíveis para o Bloco 2.
> Leva de 2026-09-14: 9 topics candidatos pontuados; top 8 entram no backlog.

## 88.00 — A última milha dos agentes de IA: ler é fácil, commitar é o que quebra

Pilares: IA Aplicada

Tese: A autonomia de um agente se prova na última milha — o trecho onde a ação precisa ser commitada — e é ali que a demo vira prejuízo: 80.000 unidades de estoque perecível, writes com 4xx, integração que ninguém testou.

Por que agora: Operador relata 18 dias de métricas reais (milhares de leituras, 1 write completo) e post-mortem de agente que pediu 80.000 unidades de estoque perecível por não distinguir congestionamento de pico de demanda.

Evidências disponíveis: 5

Experiência pessoal relacionada: Alta

Status: ready_for_research

## 84.00 — A última milha é uma decisão de margem, não de velocidade

Pilares: Logística, last mile e CX

Tese: O teste econômico da IA na entrega é o custo unitário da última milha — 53% do custo total da supply chain — e a promessa cumprida vale mais que a velocidade bruta: prometer 4 e entregar em 3 ganha; prometer 2 e entregar em 3 quebra.

Por que agora: Dado da Statista (53% do custo) circulando no LinkedIn e Amazon transformando confiabilidade em requisito de participação (90% de taxa em janela horária ou oferta desativada).

Evidências disponíveis: 5

Experiência pessoal relacionada: Alta

Status: ready_for_research

## 82.00 — Quando a operação falha, a ausência de humano transforma atraso em crise de confiança

Pilares: Logística, last mile e CX

Tese: O cliente não perdoa a falha, perdoa a demora — mas não perdoa ficar preso no loop: quando a operação quebra e não existe humano alcançável, o atraso vira crise de confiança.

Por que agora: Caso Just Eat com 180 upvotes e 157 comentários (4+ horas, comida fria, sem falar com humano) e Whole Foods marcando pedido como entregue com foto de uma parede.

Evidências disponíveis: 3

Experiência pessoal relacionada: Alta

Status: ready_for_research

## 81.00 — O humano no loop só é controle se tiver tempo, contexto e autoridade para dizer não

Pilares: IA Aplicada / Liderança

Tese: O checkbox de human-in-the-loop não é controle: sem permissões claras, políticas fortes e um dono de C-level para os limites, o humano aprova rápido demais e confia na explicação da própria IA.

Por que agora: Série de governança ("A checkbox is not control"), 76% dos CEOs planejando contratar Chief AI Officer e Microsoft lançando Entra Agent ID — agentes ganhando identidade formal.

Evidências disponíveis: 5

Experiência pessoal relacionada: Média

Status: ready_for_research

## 78.00 — Agent washing: o que se vende como agente autônomo é automação com passos extras

Pilares: IA Aplicada

Tese: A adoção em massa não prova nada: só ~130 vendors entregam autonomia real, 70-90% dos PoCs morrem antes da produção, e a linha divisória é simples — a ação transacional com write real e consequência.

Por que agora: Gartner batizando o padrão "agent washing" e 72% das supply chains já declarando deploy de IA generativa — a pergunta virou "com que resultado?".

Evidências disponíveis: 5

Experiência pessoal relacionada: Média

Status: ready_for_research

## 77.50 — Avaliar agente em produção: a régua não é a demo, é o que acontece depois do deploy

Pilares: IA Aplicada

Tese: A régua de maturidade não é o benchmark nem a demo: é o resultado de negócio medido em produção (claims pagas, escalonamento, correção) e o ciclo contínuo que puxa casos novos de volta para o eval.

Por que agora: Thread de r/AI_Agents com 42 comentários sobre avaliação pós-deploy e benchmark Real-SWE (271 pontos no HN) testando modelos em codebases privadas reais.

Evidências disponíveis: 3

Experiência pessoal relacionada: Média

Status: ready_for_research

## 76.50 — O gargalo dos agentes não é mais inteligência — é infraestrutura e custo no caminho de execução

Pilares: IA Aplicada

Tese: O gargalo migrou do modelo para a infraestrutura — identidade, permissões, observabilidade e controle de custo no runtime; dado sujo e gasto desperdiçado são o teto real do resultado.

Por que agora: Pesquisa com 1.295 organizações mostrando controle de custo migrando para o execution path e Databricks identificando gasto desperdiçado significativo com agentes.

Evidências disponíveis: 4

Experiência pessoal relacionada: Média

Status: ready_for_research

## 74.00 — Governança de IA se prova por evidência operacional, não por política

Pilares: Riscos, compliance e resiliência / IA Aplicada

Tese: Não falta política nem framework — NIST, ISO 42001 e EU AI Act existem; falta a camada que prova, no encanamento, que a regra está sendo cumprida, e a fiscalização (RFIs da Comissão Europeia) chegou antes da prova.

Por que agora: Comissão Europeia enviou as primeiras requisições de informação do EU AI Act a 30+ empresas de IA — e a pergunta que fica é se elas conseguem produzir a evidência.

Evidências disponíveis: 4

Experiência pessoal relacionada: Baixa

Status: ready_for_research

---

## Fora do backlog

- **69.00 — Velocidade de geração não é velocidade de operação** (`topic_20260914_09`): author_fit baixo (3/10), tema de engenharia de software distante da experiência do autor. Permanece `candidate`.