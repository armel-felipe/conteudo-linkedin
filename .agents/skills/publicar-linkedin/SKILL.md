---
name: publicar-linkedin
description: Use quando um post em content/drafts/ tiver marco aprovado (approved) e precisar ser publicado ou agendado no LinkedIn pelo browser do OpenWork já logado, sem credenciais. Após confirmar o agendamento, move o arquivo para content/published/.
---

# Publicar no LinkedIn (navegação assistida)

## Overview

Core principle: levar conteúdo APROVADO (marco lógico `approved`) de `content/drafts/` ao LinkedIn via browser do OpenWork já logado, sem nova aprovação de texto e sem credenciais. A aprovação é decidida no QA (`qa-draft`); esta skill é a invocação explícita do Bloco 3 que executa o agendamento/publicação.

## Quando Usar / Quando NÃO Usar

- Usar: post em `content/drafts/` com marco `approved` pronto para LinkedIn, envio "agora" ou agendado (dia/horário), e mover para `content/published/` após confirmação.
- NÃO usar: conteúdo que ainda não tem marco editorial `approved` (ex.: drafts em revisão), anexo automático de imagem (roadmap futuro), publicações corporativas/múltiplas contas.

## Invocação (opção A — por argumento)

- "Publica content/drafts/<arquivo>.md agora"
- "Publica content/drafts/<arquivo>.md amanhã às 9h"
- Validar que o arquivo EXISTE em content/drafts/ e que tem marco `approved`.

## Fluxo (passos numerados)

1. Localizar arquivo em content/drafts/ (valida existência e marco approved; se não existir ou não tiver aprovação, parar e informar).
2. Ler o arquivo Markdown e converter para texto LinkedIn (opção B): remover `# ` de título, converter/remover `**`/`__`/`*` sem vazar literal, manter quebras de linha, emojis e hashtags (`#palavra` preservadas).
3. **Obrigatoriamente iniciar pela rota visual do CUA embedded browser:** usar `browser.open_url` para criar/selecionar a aba, guardar `browser_url` e `target_id`, e capturar screenshot antes de tentar Playwright.
4. Usar **visão nativa** para localizar texto, botões, ícones, campos, menus e coordenadas no screenshot. Interagir pelo alvo correto da aba, inclusive atravessando `#interop-outlet.shadowRoot` quando a interface estiver encapsulada. Não inferir posições sem screenshot.
5. Se o modelo não tiver visão nativa, invocar `image-analyzer` com o screenshot e `reason: no_native_vision`. Se a visão nativa falhar, usar `image-analyzer` com `reason: native_failed`. Só depois dessas tentativas visuais, se ainda necessário, usar Playwright.
6. Playwright é somente diagnóstico read-only, nunca a rota de mutação: conectar ao target `linkedin.com`, registrar URL/título/estado e falhar fechado em `about:blank`, ausência de target, timeout ou seletor não encontrado.
7. Colar o conteúdo no campo de texto.
8. Aplicar agendamento:
   - Envio "agora": colar conteúdo, PAUSAR antes do clique final, informar que a pessoa pode anexar imagem manualmente, e aguardar o comando para concluir.
   - Agendado: abrir o seletor de agendamento e preencher data/hora conforme o caso (ver "Agendamento — detalhes").
9. Verificar o agendamento (ver "Verificação pós-agendamento").
10. Somente depois da verificação, registrar o agendamento no arquivo (ver "Registro do agendamento").

## Conversão Markdown → texto LinkedIn (OBRIGATÓRIA, antes da colagem)

O LinkedIn NÃO renderiza Markdown. Marcação crua colada vira literal na postagem. NUNCA cole o texto com `**`, `__`, `*` de ênfase, nem com `# ` de título como estão no arquivo. Hashtags (`#palavra`) são a ÚNICA exceção e devem ser preservadas. Siga a Opção B:

Como distinguir `# Título` de `#hashtag` (CRITÉRIO):

- Regra universal e binária: **qualquer sequência de `#` seguida de espaço é REMOVIDA inteira; qualquer `#` colado diretamente à palavra (sem espaço) é MANTIDO** — independente de posição na linha.
- Exemplos: `# Título`, `## Subtítulo`, `### Seção` → remova a sequência inteira de `#` (viram texto normal). `#gestao`, `#IA` → preservados como hashtag.
- Não há exceção: um `#` (ou run de `#`) é uma coisa ou outra, decidida pelo que vem depois — espaço (remove tudo) ou palavra (mantém).

Regras de conversão por elemento:

- Sequência de `#` seguida de espaço (qualquer posição): REMOVER todos os `#`. Manter o texto como normal, SEM caixa alta automática — preserve exatamente como está no arquivo, a menos que a pessoa peça explicitamente para mudar.
- `**texto**` / `__texto__`: REMOVER os asteriscos/sublinhados e MANTER apenas `texto`. O conteúdo negritado fica como texto comum — não tente "reproduzir" o negrito, pois o LinkedIn não aceita.
- `*item*`: remover os asteriscos; manter o `-`/`•` de lista se o arquivo já usar.
- Links `[texto](url)`: manter apenas `texto` (ou o `texto (url)` se a pessoa quiser expor o link).
- Manter quebras de linha, parágrafos, emojis e hashtags como estão.

Checklist antes de colar:
- [ ] Nenhum `**`, `__` ou `*` de ênfase restante no texto.
- [ ] Nenhuma run de `# ` de título restante (hashtags `#palavra` devem permanecer).
- [ ] `[texto](url)` virou texto legível.
- [ ] Linhas, emojis e hashtags preservados.

Regra prática: se o texto colado ainda contém `**`, `__` ou uma run de `# ` de título, você errou a conversão — corrija antes de prosseguir.

## Ponto de espera (único)

- Texto em `content/drafts/` com marco `approved` já está aprovado → NÃO pedir nova confirmação textual.
- Envio "agora": PAUSA obrigatória para anexo manual de imagem; concluir só ao receber comando.
- Agendado: não há nova aprovação textual; a validação visual do resumo, da prévia final e da publicação em "Publicações agendadas" é obrigatória antes de registrar sucesso.

## Agendamento — detalhes

O seletor de agendamento do LinkedIn é um popover com campos de data e hora. Erros comuns: clicar em "amanhã" mas deixar a hora no padrão, ou preencher a data mas não confirmar o valor antes de clicar em "Agendar".

- **Seleção explícita obrigatória**: escolher a data solicitada e preencher a hora solicitada; nunca aceitar silenciosamente os valores padrão.
- **Hoje mais tarde** (ex.: "hoje às 18h"): selecionar explicitamente a data de HOJE e o horário desejado.
- **Outro dia** (ex.: "amanhã às 9h"): selecionar explicitamente o dia correto e o horário desejado.
- **Ao mudar a data**: selecionar novamente o horário, inclusive quando o horário desejado for o mesmo de antes; depois confirmar os dois valores.
- **Antes de "Avançar"**: fazer um resumo visual e confirmar que data e hora exibidas correspondem exatamente ao pedido.
- **Antes de "Agendar"**: confirmar visualmente a prévia final e o conteúdo correto; se qualquer valor não bater, corrigir antes de agendar.
- Se o seletor não abrir ou os campos não aparecerem, parar e informar — não tentar agendar "às cegas".

### Reagendamento

Para uma divergência pós-agendamento, localizar a publicação existente na lista de publicações agendadas e usar exatamente `... → Alterar agenda`. Nunca criar duplicata nem abrir um compositor novo para corrigir uma publicação existente. Depois de alterar a agenda, repetir a seleção explícita da data e do horário, incluindo selecionar novamente o horário após mudar a data, o resumo visual antes de "Avançar", a prévia final antes de "Agendar" e a verificação na lista.

## Registro do agendamento

Antes de registrar, preencher `docs/schemas/linkedin-scheduling-checklist.yaml`. O gate é literal e fail-closed: `scheduled_list_confirmed` e `timestamp_registered` devem ser booleanos `true`, nunca strings truthy como `"pass"` ou `"fail"`. O receipt deve ser válido, `summary_confirmed` e `confirmation_received` devem estar confirmados, `requested_timestamp` e `displayed_timestamp` devem ser não vazios e exatamente iguais, e `failure_state` deve ser `null`. Se qualquer estado for `not_run`, `simulated`, `blocked` ou falho, não registrar o timestamp.

Após agendar com sucesso, anotar no arquivo do post (em `content/drafts/<arquivo>.md`) um bloco no final:

```markdown
<!-- agendado: 2026-09-01T09:00 America/Sao_Paulo -->
```

- Usar o dia/horário EXATO que foi preenchido no LinkedIn.
- Se o arquivo já tiver um bloco `<!-- agendado: ... -->` anterior, substituir pelo novo.
- Isso garante rastreabilidade de "o que está agendado para quando" sem depender de memória de conversa.

## Movimentação do arquivo (OBRIGATÓRIA após confirmação)

A confirmação em "Publicações agendadas" conclui a publicação/agendamento do arquivo. Nesse momento, **mover literalmente** o arquivo de `content/drafts/` para `content/published/`:

```bash
git mv content/drafts/<arquivo>.md content/published/<arquivo>.md
# caso o arquivo não esteja rastreado (não versionado), usar `mv` simples:
# mv content/drafts/<arquivo>.md content/published/<arquivo>.md
```

- O bloco `<!-- agendado: ... -->` registrado acima **acompanha o arquivo** na movimentação (fica em `content/published/<arquivo>.md`).
- A aprovação editorial é um marco lógico (`approved`), não uma pasta: o post vem de `content/drafts/`, nunca de `content/approved/`.
- O estado correto de cada pasta é sempre: `drafts/` = posts ainda não agendados; `published/` = posts já agendados ou com publicação disparada; `arquived/` = descartados (decisão humana); `approved/` = vazia.
- Um arquivo de post vive em **exatamente uma** pasta de `content/` por vez.

## Protocolo browser dry-run (rodadas 4 e 5)

Quando a finalidade for produzir evidência sem mutar o LinkedIn, executar
somente a sequência abaixo:

1. Abrir o seletor de data/hora sem confirmar publicação ou alteração.
2. Selecionar explicitamente a data solicitada.
3. Selecionar novamente o horário solicitado.
4. Confirmar visualmente o resumo exibido contra o pedido.
5. Registrar `blocked_before_advance` e parar antes de `Avançar`.

O dry-run não pode conter `advance`, `schedule`, `confirmation`,
`scheduled_list_confirmed` ou `timestamp_registered`. Criação, publicação,
agendamento, exclusão e alteração de publicação não foram executados por
segurança. Para uma publicação existente, é permitido apenas inspecionar o
caminho `... → Alterar agenda`; não confirmar uma segunda mudança.

### Estados de evidência

Cada cenário deve declarar exatamente um estado: `real_non_destructive`
(browser observado sem mutação), `real_existing_post` (somente caminho da
publicação existente), `simulated` (contrato/teste, sem alegação de browser) ou
`not_run` (não executado por segurança ou indisponibilidade). Um receipt de
dry-run não pode declarar confirmação, presença na lista ou timestamp
registrado.

## Verificação pós-agendamento

Após clicar em "Agendar", o LinkedIn mostra uma confirmação. Verificar:

1. A confirmação apareceu (se não apareceu, o agendamento pode não ter sido criado — parar e informar).
2. Navegar até "Ver publicações agendadas" (menu de publicações) e confirmar que o post está na lista, com a data/hora corretas. No reagendamento, confirmar a nova data/hora do post alterado.
3. Se o post NÃO estiver na lista ou a data/hora estiverem erradas, informar a pessoa e NÃO concluir como sucesso — o agendamento falhou silenciosamente.

A confirmação final deve ocorrer em **Publicações agendadas**, com o post e o horário esperado visíveis na lista.

## Visão e rota de interação

O contrato compartilhado está em `docs/browser-route-contract.md`. Use esta ordem
obrigatória de decisão. A evidência visual vem antes de qualquer automação Playwright:

```text
CUA embedded browser → screenshot/AX → image-analyzer (se necessário) → Playwright read-only → stop
```

1. Abrir ou selecionar a aba com `browser.open_url`, guardar exatamente `browser_url` e `target_id`, e capturar screenshot.
2. Usar visão nativa para resumir conteúdo, data, hora, botões e prévia a partir do screenshot; os cliques devem seguir a localização visual confirmada.
3. Se não houver visão nativa, delegar ao `image-analyzer` com `reason: no_native_vision`; se a visão nativa falhar, usar `reason: native_failed`, sempre passando o screenshot.
4. Só se a rota visual não conseguir concluir a interação, tentar Playwright (`npm run linkedin:check` ou `node scripts/linkedin_browser_check.js`) somente como diagnóstico read-only e registrar a razão da transição.
5. Se nenhuma rota funcionar ou a imagem estiver ilegível, registrar `stop`, relatar a limitação e não inferir o estado da tela.

Cada execução deve preservar a operação, alvo, rota tentada, rota efetiva, resultado,
razão de fallback (`no_native_vision` ou `native_failed`),
evidência de verificação e classificação final. Para publicar, agendar, reagendar
ou excluir, confirmar alvo e intenção antes do envio; após o envio, verificar o
estado independente. Em `ambiguous_mutation`, aplicar fail-closed: não repetir,
não avançar e nunca abrir um novo composer.

Siga `.agents/skills/visao-nativa-primeiro/SKILL.md` como protocolo complementar para a visão nativa.

### Contrato comportamental

Uma execução válida usa estes eventos na ordem indicada; `playwright_attempt`
só aparece depois da tentativa visual:

```text
approved_file → markdown_converted → browser_attempt → screenshot → visual_route → date_selected → time_selected → summary_confirmed → advance → final_preview_confirmed → schedule → confirmation → scheduled_list_confirmed → timestamp_registered
```

O screenshot é obrigatório na primeira rota; não autoriza inferência sem evidência. Os branches são `browser_native`, `image-analyzer`, `playwright` e `stop`; `browser_native` é a primeira tentativa, `image-analyzer` é usado quando necessário, `playwright` só aparece depois da tentativa visual e `stop` encerra quando não há evidência suficiente.

Para reagendamento, a sequência é `existing_post_menu → alter_schedule → date_selected → time_selected`. O fluxo não contém `new_composer`: divergências usam a publicação existente.

## Credenciais

- NUNCA guardar/ler e-mail, senha, token ou cookie. Usar apenas a sessão já logada do browser.

## Erros comuns (Common Mistakes)

 - Colar Markdown cru (`**`, `__`, `*`, `# ` de título) — deve converter antes; hashtags `#palavra` são preservadas e não são erro.
 - Pedir nova aprovação de texto — o arquivo em `content/drafts/` com marco `approved` já é aprovado.
 - Pular a pausa no envio "agora" — a pausa é obrigatória (anexo manual de imagem).
 - Tentar autenticar — usar a sessão já logada.
 - Não validar que o arquivo está em `content/drafts/` e com marco `approved` — bloquear se não estiver.
- Agendar sem confirmar o valor exibido no seletor — o LinkedIn pode manter data/hora padrão; confirmar antes de clicar em "Agendar".
- Concluir como sucesso sem verificar "Ver publicações agendadas" — o agendamento pode ter falhado silenciosamente.
- Pular o navegador embutido e começar por Playwright — CUA embedded browser + screenshot + visão é a rota obrigatória inicial.
- Tratar a confirmação visual como fallback — screenshot/AX (ou image-analyzer) é a primeira evidência.
- Não selecionar novamente o horário depois de trocar a data.
- Reagendar abrindo um compositor novo em vez de usar `... → Alterar agenda`.
- Não registrar o agendamento no arquivo do post — sem o bloco `<!-- agendado: ... -->` não há rastreabilidade.

## Roadmap (fora de escopo)

- Anexo automático de imagem → docs/roadmap.md.
- Múltiplas contas/redes, métricas → depreciado.
