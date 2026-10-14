# Design: diversidade dentro das frentes editoriais

**Data:** 2026-10-14  
**Status:** proposta aprovada para especificação; implementação ainda não iniciada

## Objetivo

Reduzir a repetição semântica dos temas descobertos pelo pipeline sem abandonar as frentes editoriais atuais. A janela temporal do `last30days` continua controlando recência, mas deixa de ser tratada como mecanismo de diversidade.

O modo diversidade deve permitir que a frente `ia_aplicada`, por exemplo, produza temas sobre autoridade, trabalho, adoção, confiança, comportamento e desenho organizacional, além dos recortes recorrentes de custo, avaliação e governança.

## Escopo

Incluído:

- taxonomia editorial persistente para signals e topics;
- detecção de distância em relação aos temas recentes;
- penalidade de repetição no scoring;
- uma faixa de descoberta exploratória dentro de cada frente;
- relatório de distribuição e de cobertura no HTML de topics;
- preservação do gate de novidade existente, que continua fail-closed.

Fora do escopo:

- criar novas frentes editoriais;
- alterar a ordem dos blocos do pipeline;
- mudar o processo de aprovação humana;
- substituir a pesquisa `last30days`;
- publicar ou agendar conteúdo automaticamente.

## Modelo editorial

Cada signal e cada topic elegível deve registrar quatro dimensões:

```yaml
diversity:
  context: [varejo, industria, servicos]
  mechanism: [confianca, coordenacao, custo]
  actor: [gestor, operador, cliente]
  change_type: [adocao, falha, conflito, comportamento]
```

As listas devem usar vocabulário controlado configurado no projeto, com possibilidade de mais de um valor por dimensão. A classificação descreve o recorte do signal/topic; não substitui `pillars`, `novelty` ou `scores`.

Um novo topic deve ser considerado semanticamente repetitivo quando mantém o mesmo mecanismo e o mesmo recorte de contexto, ou quando mantém a mesma tese e pergunta central mesmo com título diferente. A distância não deve ser um bloqueio absoluto por si só: ela alimenta o score e só bloqueia quando o topic também falha no gate de novidade existente.

## Scoring e seleção

Adicionar `distance_from_recent_topics` como critério de scoring, na mesma escala de 0 a 10. A avaliação deve comparar o candidato com topics publicados, arquivados e gerados em uma janela configurável de histórico recente.

O critério deve considerar, em ordem:

1. sobreposição de mecanismo;
2. sobreposição de contexto;
3. sobreposição de ator;
4. repetição de tese/pergunta central;
5. repetição do tipo de evidência ou caso.

O score agregado deve aumentar o peso efetivo de originalidade/diversidade sem apagar `author_fit` e relevância. A primeira configuração recomendada é manter os pesos existentes como referência, adicionar o novo critério com peso de 0,15 e reduzir proporcionalmente `relevance`, `author_fit` e `linkedin_fit`, sem permitir que a diversidade sozinha faça uma pauta fraca entrar no backlog.

O score deve registrar também uma explicação curta, por exemplo:

```yaml
diversity_score:
  distance_from_recent_topics: 8
  closest_topics: [topic_20261013_01, topic_20260923_01]
  overlap: [ia_aplicada]
  explanation: "Mesmo pilar, mas mecanismo de autoridade e ator regulador não aparecem nos recortes recentes."
```

## Descoberta exploratória

Cada execução do Bloco 1 deve permitir um modo diversidade. Nesse modo, a coleta combina:

- aproximadamente 50% de queries derivadas das keywords atuais;
- aproximadamente 50% de queries exploratórias derivadas de perguntas editoriais abertas.

As perguntas exploratórias devem variar por frente e buscar mudança, conflito, consequência, comportamento, redistribuição de poder e prática contraintuitiva. Exemplos:

- “que prática está sendo abandonada?”;
- “qual efeito inesperado apareceu depois da adoção?”;
- “onde eficiência e qualidade entraram em conflito?”;
- “quem ganhou ou perdeu poder?”;
- “que setor resolveu o problema de maneira contraintuitiva?”

As queries exploratórias não podem virar um convite a conteúdo genérico ou evergreen: cada signal ainda precisa de fonte, data, debate e evidência conforme o contrato atual.

## Relatório e HTML

O HTML obrigatório de topics deve mostrar, além dos dados atuais:

- distribuição por frente/pilar;
- distribuição por mecanismo;
- distribuição por contexto e ator;
- distância média em relação aos topics recentes;
- alertas de concentração, quando um mecanismo ou combinação de dimensões dominar a leva.

O relatório deve tornar visível quando uma leva parece diversificada por título, mas continua concentrada no mesmo mecanismo.

## Compatibilidade e falhas

- Signals antigos sem `diversity` continuam legíveis; durante a migração, recebem classificação explícita `unknown` e não podem ser usados como evidência de diversidade.
- Se a classificação não puder ser feita com segurança, o signal permanece válido para pesquisa, mas o topic não recebe bônus de distância.
- Se o histórico não estiver disponível, o scoring deve falhar fechado para o bônus de diversidade, sem inventar distância.
- O gate de novidade (`new`, `revisited`, `duplicate`) permanece obrigatório e independente.
- A ausência de variedade não deve ser corrigida removendo ou rebaixando artificialmente signals válidos; deve aparecer como alerta de cobertura.

## Critérios de sucesso

Após três levas do modo diversidade:

- nenhuma leva deve ter mais de 50% dos topics concentrados no mesmo mecanismo;
- cada leva deve conter pelo menos três mecanismos distintos quando houver evidência suficiente;
- pelo menos metade dos topics deve diferir dos dois topics mais próximos em duas ou mais dimensões;
- a taxa de topics arquivados por repetição deve cair em relação às duas levas anteriores;
- não pode haver queda deliberada na rastreabilidade das fontes, no gate de novidade ou na conexão com o autor.

## Sequência de implementação proposta

1. Criar vocabulário controlado e regras de classificação.
2. Adicionar campos `diversity` aos novos signals/topics e compatibilidade para históricos.
3. Implementar cálculo de distância e explicação do score.
4. Adicionar geração de queries exploratórias por frente.
5. Exibir a distribuição no HTML e validar com fixtures de temas repetidos e temas realmente distintos.
6. Rodar três levas em modo diversidade e revisar os thresholds antes de torná-lo padrão.

