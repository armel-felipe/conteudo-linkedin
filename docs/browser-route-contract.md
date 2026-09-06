# Contrato de Rota de Navegador

Este documento define a rota normativa para qualquer skill ou script que opere
um navegador no pipeline editorial. A rota padrão é sempre:

```text
MCP Chrome DevTools → Playwright (fallback) → stop
```

Os nomes normativos das rotas são:

- `mcp_chrome_devtools`: rota primária. Deve ser tentada primeiro para abrir,
  inspecionar, ler ou interagir com uma página.
- `playwright_fallback`: rota secundária, usada somente quando a rota primária
  não estiver disponível ou não conseguir completar uma operação ainda não
  confirmada como mutação.
- `ambiguous_mutation`: resultado em que uma operação de mutação pode ter sido
  aplicada, mas seu resultado não foi confirmado.
- `fail_closed` (também referido como **fail-closed**): comportamento
  obrigatório diante de uma mutação ambígua:
  interromper novas ações e não presumir sucesso.

## Ordem e limite do fallback

1. Registrar a intenção da operação e tentar `mcp_chrome_devtools`.
2. Se a operação não puder ser concluída e ainda não houver confirmação de
   mutação, registrar a falha e tentar `playwright_fallback`.
3. Se o fallback também não concluir a operação, registrar a rota efetiva e
   parar. Não tentar uma terceira rota e não abrir uma nova composição de ação.
4. Depois que uma mutação for enviada, fallback não é permitido para repetir
   a ação. Primeiro é necessário verificar o estado resultante.

Fallback é permitido somente antes de uma mutação ser confirmada. Em especial,
uma resposta de timeout, desconexão ou erro após o envio de uma ação deve ser
tratada como `ambiguous_mutation`, não como autorização para repetir a ação.

Toda operação deve registrar, no artefato ou log persistente, pelo menos a rota
efetiva (`mcp_chrome_devtools`, `playwright_fallback` ou `stop`), o tipo de
operação, o resultado e, quando houver, a verificação do estado. A ausência de
registro torna a operação não auditável e impede sua aprovação.

## Leitura e inspeção

Para abrir, ler, localizar elementos, capturar estado ou inspecionar uma tela:

- usar `mcp_chrome_devtools` primeiro;
- permitir `playwright_fallback` se a tentativa primária falhar antes de
  qualquer mutação;
- registrar a rota efetiva mesmo quando a operação terminar sem dados;
- em caso de falha nas duas rotas, parar sem converter uma leitura incerta em
  uma decisão editorial.

Leituras não devem criar, enviar ou alterar conteúdo. Uma ação de inspeção que
possa alterar estado deve ser classificada como mutação antes de ser executada.

## Publicar, agendar, reagendar e excluir

Publicar, agendar, reagendar e excluir são mutações de alto risco. Para cada
uma delas:

- confirmar o alvo, o conteúdo e a intenção antes do envio;
- usar `mcp_chrome_devtools` como rota primária;
- usar `playwright_fallback` somente se a falha ocorrer antes de a mutação ser
  confirmada como enviada;
- após o envio, verificar o estado no navegador ou por uma leitura independente
  antes de registrar sucesso;
- se o estado não puder distinguir sucesso de não execução, classificar como
  `ambiguous_mutation` e aplicar `fail_closed`;
- em `fail_closed`, não repetir, não publicar novamente, não reagendar, não
  excluir e não avançar o item para o próximo estado do pipeline.

Em particular, diante de um resultado ambíguo, **nunca abrir novo composer**:
o composer existente pode conter uma mutação já enviada ou um rascunho cujo
estado ainda precisa ser verificado. A próxima ação permitida é somente a
verificação de estado e, se necessário, a intervenção humana definida pelo
pipeline.

## Registro mínimo

Cada execução deve preservar:

- operação solicitada e alvo identificado;
- rota tentada e rota efetiva;
- ponto em que a mutação foi ou não confirmada;
- evidência da verificação de estado;
- classificação final (`success`, `failed`, `ambiguous_mutation` ou `stop`);
- qualquer aplicação de `fail_closed`.

Skills e scripts que não conseguirem produzir esse registro devem parar antes
de executar uma mutação.
