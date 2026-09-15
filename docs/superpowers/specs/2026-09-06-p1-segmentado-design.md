# P1 segmentado — design de execução

> **Status documental:** histórico; não é contrato operacional. Consulte `AGENTS.md` e `docs/roadmap.md`.

**Data:** 2026-09-06  
**Status:** aprovado pelo usuário

## Objetivo

Executar o P1 em entregas independentes, com evidência e critério de conclusão
por parte, sem misturar validação de fontes, observabilidade, automação de
triagem e mutações no LinkedIn.

## Ordem e dependências

```text
P1-A: validar X
  ↓
P1-B: criar logs
  ↓
P1-C: automatizar scoring/clustering
  ↓
P1-D: validar matriz de agendamento
```

Cada parte termina com testes ou evidência operacional própria e uma atualização
do roadmap. Uma falha em uma parte bloqueia somente as partes que dependem
dela; não autoriza atalhos ou ações mutantes.

## P1-A — validação real do X

Usar um tópico já existente no backlog, executar uma pesquisa somente de leitura
e verificar se o backend X retorna dados. Registrar comando, status da fonte,
data, quantidade de evidências e limitações. Não publicar, seguir contas,
enviar mensagens ou alterar qualquer conteúdo.

Critério: backend X confirmado em execução real ou bloqueio documentado com causa
objetiva e próximo passo mínimo.

## P1-B — logs de execução

Criar observabilidade persistente por etapa, rota, estado, duração e receipt.
Os logs devem registrar MCP Chrome DevTools como primeira rota e o motivo de
qualquer fallback para Playwright. Segredos, cookies, tokens e conteúdo privado
não podem aparecer nos logs.

Critério: um teste de execução produz log sanitizado e validável sem depender de
uma sessão real.

## P1-C — scoring e clustering

Criar scripts Python separados para consumir signals/topics persistidos, aplicar
scoring e clusterizar sinais. Os scripts produzem artefatos persistentes e não
escrevem briefs ou posts. A redação continua separada da pesquisa.

Critério: execução reproduzível em fixtures, com saída validada e teste para
entrada vazia, duplicada e inválida.

## P1-D — matriz de agendamento

Executar somente depois de P1-A–C e com uma publicação de teste autorizada.
Validar criação, confirmação, alteração, verificação e bloqueio de duplicata.
Em qualquer resultado ambíguo, verificar estado e parar fail-closed.

Critério: todos os casos da matriz têm receipt, rota efetiva e estado final
confirmado; nenhum novo composer é usado para reagendar publicação existente.

## Limites

- P1 não cria automação recorrente; isso continua no P2.
- P1-D não reutiliza nem altera o post do incidente anterior.
- Nenhuma chave de API ou credencial é versionada.
- Cada parte atualiza `docs/roadmap.md` somente depois da evidência correspondente.
