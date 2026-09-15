# Prioridade de rota de navegador: MCP Chrome DevTools → Playwright

> **Status documental:** obsoleto; substituído pela rota visual-first em `docs/browser-route-contract.md`.

**Data:** 2026-09-06  
**Status:** aprovado pelo usuário

## Objetivo

Padronizar todo o pipeline agentico que usa navegador para tentar primeiro o
MCP Chrome DevTools e usar Playwright somente como fallback controlado. A
mudança deve reduzir operações duplicadas ou ambíguas, especialmente em
publicação e agendamento no LinkedIn.

## Escopo

- Atualizar o contrato operacional compartilhado por skills e scripts que usam
  navegador.
- Atualizar `publicar-linkedin` e outras skills do pipeline que mencionem
  browser, Playwright ou CDP.
- Atualizar `README.md`, `mapa.md`, roadmap e planos operacionais conflitantes.
- Ajustar scripts e testes para verificar a ordem das rotas e o comportamento
  fail-closed.
- Manter o lote editorial separado de publicação e agendamento automáticos.

Não faz parte do escopo introduzir publicação automática no lote editorial,
nem persistir credenciais, tokens ou configuração privada.

## Fluxo obrigatório

```text
operação no navegador
  ↓
MCP Chrome DevTools
  ↓ se indisponível, capability ausente ou falha técnica permitida
Playwright (fallback)
  ↓ se também indisponível/falhar
parar com erro explícito
```

Nenhuma chamada Playwright deve ocorrer antes da tentativa MCP. O resultado
operacional deve registrar a rota efetivamente usada:
`mcp_chrome_devtools` ou `playwright_fallback`.

## Classes de operação

### Leitura e inspeção

O MCP deve ser usado primeiro para navegação, leitura, localização de
elementos, captura de estado e verificação. Playwright pode assumir quando a
capability não existir ou falhar tecnicamente, desde que o motivo seja
registrado.

### Ações mutantes

Para publicar, agendar, reagendar ou excluir:

1. Capturar e registrar o estado anterior.
2. Executar uma única mutação pela rota ativa.
3. Confirmar o resultado na interface.
4. Persistir artefatos locais somente após a confirmação.

Se a resposta for ambígua ou houver possibilidade de a mutação ter ocorrido,
nenhuma nova mutação pode ser tentada cegamente. O fluxo deve verificar o
estado atual e parar quando não houver confirmação objetiva. Para corrigir
uma publicação existente, deve usar a ação de alteração da publicação
existente, nunca abrir um novo composer.

## Fallback e falhas

O fallback para Playwright é permitido quando:

- o MCP Chrome DevTools não está disponível;
- a capability necessária não está exposta;
- ocorre uma falha técnica que impede a operação antes de uma mutação
  confirmada.

Falhas ambíguas depois de uma possível mutação exigem verificação de estado e
fail-closed; não autorizam repetição automática. Se MCP e Playwright não
estiverem disponíveis, o fluxo termina com erro explícito e sem registrar
sucesso.

## Evidências e persistência

Cada execução browser deve manter evidência suficiente para distinguir:

- rota tentada e rota efetiva;
- capability ou operação executada;
- estado observado antes e depois;
- motivo do fallback, quando aplicável;
- confirmação ou bloqueio da mutação.

No LinkedIn, o timestamp só pode ser escrito no arquivo aprovado após a
confirmação na lista de publicações agendadas ou após evidência equivalente de
publicação concluída.

## Testes e critérios de aceite

Os testes devem cobrir:

- MCP sempre precede Playwright;
- fallback somente em condições permitidas;
- registro da rota efetiva e do motivo;
- bloqueio de repetição após resultado ambíguo;
- persistência de timestamp somente depois da confirmação;
- reagendamento por publicação existente, sem novo composer.

Critério global: nenhuma documentação, skill ou teste do pipeline pode
declarar Playwright como primeira rota. O contrato, as instruções operacionais
e os testes devem apresentar a mesma ordem MCP → Playwright.
