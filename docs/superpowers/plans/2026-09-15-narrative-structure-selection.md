# Seleção de Estrutura Narrativa — Plano de Implementação

> **Para agentes executores:** use `superpowers:subagent-driven-development` (recomendado) ou `superpowers:executing-plans` para executar este plano tarefa por tarefa. As etapas usam caixas de seleção para acompanhamento.

**Objetivo:** formalizar a regra de negócio que escolhe a estrutura narrativa de cada post e reestruturar o `topic_20260914_07` para demonstrar, por continuidade causal, o conflito entre margem e velocidade.

**Arquitetura:** a seleção começa pela evidência dominante do tema e escolhe um motor narrativo — caso, conflito, contraste, métrica, experiência ou movimento de mercado. A tese continua podendo abrir o post, mas os parágrafos seguintes devem explicitar decisão, tensão e consequência. A estrutura é um diagnóstico editorial, não um molde fixo: cada post usa apenas o motor que melhor explica sua evidência principal.

**Tech Stack:** Markdown, arquivos YAML do pipeline editorial, `qa-draft`, `critique-post` e `escrita-humana`.

## Restrições globais

- Preservar a fronteira do Bloco 2.5: o draft permanece `drafted` e não pode ser marcado `approved` pelo agente.
- Manter o post entre 900–1500 caracteres e 150–250 palavras, aceitando a exceção já registrada de até aproximadamente 1600 caracteres/270 palavras somente quando necessária à narrativa.
- Manter a seção `## Fontes` e não introduzir fatos que não estejam no brief.
- Uma ideia central por post; evidências devem ter função narrativa explícita.
- Não aplicar uma sequência fixa que faça os posts parecerem cópias.

---

## Regra de negócio

Escolher a estrutura pelo tipo de evidência mais forte disponível, nesta prioridade:

1. caso com promessa, quebra, reação e custo → estrutura de caso;
2. escolha entre objetivos incompatíveis → estrutura de conflito;
3. diferença verificável entre dois cenários → estrutura de contraste;
4. métrica que incentiva o comportamento errado → estrutura de métrica;
5. experiência concreta do autor → estrutura de experiência;
6. mudança de mercado, plataforma ou regra → estrutura de movimento.

Em empate, priorizar a evidência que contém uma decisão real e uma consequência observável. A abertura pode ser a conclusão; o teste é se o desenvolvimento responde, em ordem causal: “qual decisão está em jogo?”, “o que ela otimiza?”, “qual custo ou risco cria?” e “qual critério deve orientar a escolha?”.

## Tarefas

### Tarefa 1: Registrar o contrato editorial da regra

**Arquivos:**
- Modificar: `memory/writing_style.md`
- Modificar: `docs/roadmap.md`

**Resultado esperado:** o contrato editorial passa a dizer que a estrutura deve ser selecionada pela evidência dominante, preservando variação de motor narrativo e permitindo abertura com a conclusão.

- [x] **Passo 1:** adicionar em `memory/writing_style.md` uma seção de regra de seleção narrativa após “Fio narrativo”, contendo a prioridade dos seis motores e o critério de desempate por decisão/consequência.
- [x] **Passo 2:** incluir na mesma seção que cada evidência deve responder a uma função (“provar”, “complicar” ou “resolver” o conflito) e que nenhuma estrutura deve ser aplicada mecanicamente.
- [x] **Passo 3:** confirmar em `docs/roadmap.md` o item ativo e o vínculo para este plano.
- [x] **Passo 4:** verificar com `rg -n "seleção narrativa|motor narrativo|evidência dominante" memory/writing_style.md docs/roadmap.md` que a regra está registrada uma única vez como contrato e uma vez como pendência.

### Tarefa 2: Reestruturar o argumento do `topic_20260914_07`

**Arquivos:**
- Ler: `research/briefs/topic_20260914_07.md`
- Ler: `memory/writing_style.md`
- Modificar: `content/drafts/topic_20260914_07.md`

**Resultado esperado:** o post mantém a conclusão “a última milha é uma decisão de margem”, mas desenvolve uma única história: a empresa compra velocidade, a promessa cria custo quando não é cumprida, e a decisão correta é calibrar promessa e capacidade. A IA aparece apenas como mecanismo para reduzir custo unitário/falhas.

- [x] **Passo 1:** classificar o motor como `conflito`, registrando mentalmente o conflito “velocidade prometida versus margem preservada”.
- [x] **Passo 2:** manter ou ajustar a abertura para declarar a tese sem introduzir uma segunda tese.
- [x] **Passo 3:** ordenar os parágrafos pela cadeia: pressão por velocidade → custo de comprar velocidade → exemplo dos 4 dias/3 dias versus 2 dias/3 dias → efeito econômico e de confiança → decisão operacional → aplicação seletiva de IA → pergunta.
- [x] **Passo 4:** retirar ou integrar qualquer evidência que não avance essa cadeia, especialmente referências que entrem apenas como nova notícia.
- [x] **Passo 5:** atribuir com cautela os dados de 53%, 76%/15% e Amazon conforme as limitações e riscos descritos no brief.
- [x] **Passo 6:** preservar `## Fontes` e o status físico em `content/drafts/`; não mover nem aprovar o arquivo.

### Tarefa 3: Revalidar qualidade editorial

**Arquivos:**
- Ler: `content/drafts/topic_20260914_07.md`
- Ler: `research/briefs/topic_20260914_07.md`
- Verificar: `content/drafts/topic_20260914_07.md`

**Resultado esperado:** a nova versão tem continuidade narrativa, fatos rastreáveis, tamanho válido e uma pergunta final derivada do conflito.

- [x] **Passo 1:** rodar a crítica do post pelos critérios de clareza, originalidade, credibilidade, tom humano, densidade, relevância, consistência, evidências, risco de alucinação e linguagem genérica.
- [x] **Passo 2:** confirmar que cada número e afirmação factual encontra origem no brief e que as limitações das fontes não são apresentadas como certeza auditada.
- [x] **Passo 3:** contar somente o corpo antes de `## Fontes`; registrar caracteres e palavras e confirmar 900–1500 caracteres/150–250 palavras, ou justificar a exceção de tamanho no máximo aproximado de 1600/270.
- [x] **Passo 4:** rodar `escrita-humana` conforme o fluxo do projeto e revalidar tamanho, fontes e continuidade após o passe.
- [ ] **Passo 5:** apresentar o draft ao autor para decisão humana; manter `drafted` até aprovação explícita.

### Tarefa 4: Aplicar a regra ao próximo draft sem repetir o molde

**Arquivos:**
- Ler: `content/drafts/topic_20260914_01.md`
- Ler: `research/briefs/topic_20260914_01.md`

**Resultado esperado:** o próximo draft recebe uma estrutura escolhida por diagnóstico próprio, não por cópia do conflito margem versus velocidade.

- [ ] **Passo 1:** identificar a evidência dominante do topic 01 e registrar o motor narrativo escolhido antes de editar.
- [ ] **Passo 2:** comparar o motor escolhido com o motor `conflito` usado no topic 07 e remover repetições de abertura, conectores e sequência de provas.
- [ ] **Passo 3:** só então propor a reestruturação do topic 01 em uma rodada separada de QA.

## Verificação do plano

- Cobertura: a regra geral está na Tarefa 1; a aplicação ao topic 07 está na Tarefa 2; os gates de qualidade estão na Tarefa 3; a proteção contra cópia está na Tarefa 4.
- Consistência: `drafted` permanece estado final da edição; `approved` continua decisão exclusiva do autor.
- Escopo: este plano trata estrutura narrativa e documentação editorial; não altera o motor do pipeline nem publica ou agenda posts.
- Placeholders: não há `TBD`, `TODO` ou instruções sem critério operacional.
