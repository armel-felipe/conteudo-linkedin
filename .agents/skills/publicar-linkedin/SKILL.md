---
name: publicar-linkedin
description: Use quando um arquivo em content/approved/ precisar ser publicado ou agendado no LinkedIn pelo browser do OpenWork já logado, sem credenciais.
---

# Publicar no LinkedIn (navegação assistida)

## Overview

Core principle: levar conteúdo APROVADO de content/approved/ ao LinkedIn via browser do OpenWork já logado, sem nova aprovação de texto e sem credenciais.

## Quando Usar / Quando NÃO Usar

- Usar: arquivo em content/approved/ pronto para LinkedIn, envio "agora" ou agendado (dia/horário).
- NÃO usar: conteúdo que ainda não está em approved/ (ex.: drafts, ideas), anexo automático de imagem (roadmap futuro), publicações corporativas/múltiplas contas.

## Invocação (opção A — por argumento)

- "Publica content/approved/<arquivo>.md agora"
- "Publica content/approved/<arquivo>.md amanhã às 9h"
- Validar que o arquivo EXISTE em content/approved/.

## Fluxo (passos numerados)

1. Localizar arquivo em content/approved/ (valida existência; se não existir, parar e informar).
2. Ler o arquivo Markdown e converter para texto LinkedIn (opção B): remover `#` de título, converter/remover `**` sem vazar literal, manter quebras de linha, emojis e hashtags.
3. Abrir o browser do OpenWork já logado (openwork_execute browser.open_url → linkedin.com/feed) e navegar até "Começar publicação".
4. Colar o conteúdo no campo de texto.
5. Aplicar agendamento:
   - Envio "agora": colar conteúdo, PAUSAR antes do clique final, informar que a pessoa pode anexar imagem manualmente, e aguardar o comando para concluir.
   - Agendado (dia/horário): preencher data/hora e agendar; avisar que a validação ocorre no próprio LinkedIn antes do disparo.

## Conversão Markdown → texto LinkedIn (OBRIGATÓRIA, antes da colagem)

O LinkedIn NÃO renderiza Markdown. Marcação crua colada vira literal na postagem. NUNCA cole o texto com `**` ou `#` como estão no arquivo. Siga a Opção B:

- `# Título` / `## Subtítulo`: REMOVER o(s) `#` (título vira texto normal; opcionalmente deixar em caixa alta se fizer sentido para o tom).
- `**texto**` / `__texto__`: REMOVER os asteriscos/sublinhados e MANTER apenas `texto`. O conteúdo negritado fica como texto comum — não tente "reproduzir" o negrito, pois o LinkedIn não aceita.
- `*item*`: remover os asteriscos; manter o `-`/`•` de lista se o arquivo já usar.
- Links `[texto](url)`: manter apenas `texto` (ou o `texto (url)` se a pessoa quiser expor o link).
- Manter quebras de linha, parágrafos, emojis e hashtags como estão.

Checklist antes de colar:
- [ ] Nenhum `**` restante no texto.
- [ ] Nenhum `#` restante no texto.
- [ ] `[texto](url)` virou texto legível.
- [ ] Linhas, emojis e hashtags preservados.

Regra prática: se o texto colado ainda contém `**` ou `#`, você errou a conversão — corrija antes de prosseguir.

## Ponto de espera (único)

- Texto em approved/ já está aprovado → NÃO pedir nova confirmação textual.
- Envio "agora": PAUSA obrigatória para anexo manual de imagem; concluir só ao receber comando.
- Agendado: sem pausa na skill; pessoa valida no LinkedIn.

## Visão (delegar ao image-analyzer)

- Se o modelo hospedeiro não ler imagens, delegar leitura de tela ao subagente image-analyzer (task com subagent_type "image-analyzer", passando o caminho do screenshot). Usar para confirmar estado da tela (campo de texto, botão publicar, seletor de agendamento).

## Credenciais

- NUNCA guardar/ler e-mail, senha, token ou cookie. Usar apenas a sessão já logada do browser.

## Erros comuns (Common Mistakes)

- Colar Markdown cru (`**`, `#`) — deve converter antes.
- Pedir nova aprovação de texto — o arquivo em approved/ já é aprovado.
- Pular a pausa no envio "agora" — a pausa é obrigatória (anexo manual de imagem).
- Tentar autenticar — usar a sessão já logada.
- Não validar que o arquivo está em approved/ — bloquear se não estiver.

## Roadmap (fora de escopo)

- Anexo automático de imagem → docs/roadmap.md.
- Múltiplas contas/redes, métricas → depreciado.
