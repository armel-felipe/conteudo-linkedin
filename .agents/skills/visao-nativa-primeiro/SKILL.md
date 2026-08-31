---
name: visao-nativa-primeiro
description: Use when uma tarefa envolve interpretar, descrever ou extrair informação de uma imagem e o modelo pode ter visão nativa ou precisar de um analisador visual
---

# Visão nativa primeiro

## Protocolo

Siga esta ordem para qualquer imagem:

1. **Tente a visão nativa primeiro.** Se o modelo atual consegue ver imagens, use a
   visão nativa e registre a rota `native`.
2. **Modelo sem visão.** Se o modelo não tem visão, delegue a análise para
   `image-analyzer` e registre a rota `image-analyzer`.
3. **Falha da visão nativa.** Se a visão nativa falhar, estiver indisponível ou
   retornar erro, use `image-analyzer` como fallback e registre o motivo
   `native_failed`.

Não trate uma imagem ilegível, corrompida ou inacessível como evidência. Informe a
limitação de leitura ao solicitante e não produza conteúdo inferido, preenchido por
suposição ou inventado. Não invente texto, objetos, valores ou contexto que não
estejam visíveis.

## Metadados internos

Os metadados internos de rota podem conter apenas:

- `route`: `native` ou `image-analyzer`;
- `reason`: `no_native_vision`, `native_failed` ou `unreadable_image`;
- estado resumido da operação, sem dados sensíveis.

O logging deve ser secret-free: não registre o conteúdo da imagem e não armazene
esse conteúdo,
URLs privadas, credenciais, tokens, chaves de API ou qualquer outro segredo. Esses
metadados servem apenas para rastrear a decisão de roteamento e não substituem a
resposta baseada no que foi realmente observado.
