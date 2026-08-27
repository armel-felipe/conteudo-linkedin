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
2. Ler o arquivo Markdown e converter para texto LinkedIn (opção B): remover `# ` de título, converter/remover `**`/`__`/`*` sem vazar literal, manter quebras de linha, emojis e hashtags (`#palavra` preservadas).
3. Abrir o browser do OpenWork já logado (openwork_execute browser.open_url → linkedin.com/feed) e navegar até "Começar publicação".
4. Colar o conteúdo no campo de texto.
5. Aplicar agendamento:
   - Envio "agora": colar conteúdo, PAUSAR antes do clique final, informar que a pessoa pode anexar imagem manualmente, e aguardar o comando para concluir.
   - Agendado (dia/horário): preencher data/hora e agendar diretamente; concluir sem nova validação de texto (o texto em approved/ já está aprovado).

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

- Texto em approved/ já está aprovado → NÃO pedir nova confirmação textual.
- Envio "agora": PAUSA obrigatória para anexo manual de imagem; concluir só ao receber comando.
- Agendado: sem pausa na skill e sem nova validação; o agente agenda direto (o texto já foi aprovado no pipeline). A pessoa pode conferir/cancelar/edit a em "Ver publicações agendadas" no LinkedIn antes da hora.

## Visão (delegar ao image-analyzer)

- Se o modelo hospedeiro não ler imagens, delegar leitura de tela ao subagente image-analyzer (task com subagent_type "image-analyzer", passando o caminho do screenshot). Usar para confirmar estado da tela (campo de texto, botão publicar, seletor de agendamento).

## Credenciais

- NUNCA guardar/ler e-mail, senha, token ou cookie. Usar apenas a sessão já logada do browser.

## Erros comuns (Common Mistakes)

- Colar Markdown cru (`**`, `__`, `*`, `# ` de título) — deve converter antes; hashtags `#palavra` são preservadas e não são erro.
- Pedir nova aprovação de texto — o arquivo em approved/ já é aprovado.
- Pular a pausa no envio "agora" — a pausa é obrigatória (anexo manual de imagem).
- Tentar autenticar — usar a sessão já logada.
- Não validar que o arquivo está em approved/ — bloquear se não estiver.

## Roadmap (fora de escopo)

- Anexo automático de imagem → docs/roadmap.md.
- Múltiplas contas/redes, métricas → depreciado.
