---
name: visao-nativa-primeiro
description: Use when uma tarefa envolve interpretar, descrever ou extrair informação de uma imagem e o modelo pode ter visão nativa ou precisar de um analisador visual
---

# Visão nativa primeiro

## Protocolo

As condições abaixo são exclusivas: cada uma define uma rota obrigatória e não pode
ser substituída por uma inferência implícita. A ordem das seções é parte do contrato.

### Modelo com visão nativa

Quando o modelo atual consegue ver imagens, tente a visão nativa.

**Rota obrigatória: `native`.**

### Modelo sem visão nativa

Quando o modelo atual não consegue ver imagens, não tente visão nativa.

**Rota obrigatória: `image-analyzer`.**

### Falha da visão nativa

Quando a tentativa nativa falhar, estiver indisponível ou retornar erro, delegue a
análise ao fallback visual.

**Rota obrigatória: `image-analyzer`.**
**Motivo: `native_failed`.**

### Falha do image-analyzer

Quando o fallback visual também falhar, não há rota adicional.

**Rota obrigatória: nenhuma.**

Responda com uma limitação de leitura e não produza inferência, texto, objetos,
valores ou contexto não observados.

### Imagem ilegível ou corrompida

Quando a imagem estiver ilegível, corrompida ou inacessível, não trate seus dados como
evidência.

**Rota obrigatória: nenhuma.**

Responda com uma limitação de leitura e não produza inferência, preenchimento por
suposição ou conteúdo inventado.

Este documento define o protocolo de roteamento; não implementa detecção automática
de capacidade do modelo nem validação automática de arquivos.

## Metadados internos

### Campos permitidos nos metadados

- `route`: `native` ou `image-analyzer`;
- `reason`: `no_native_vision`, `native_failed` ou `unreadable_image`;
- estado resumido da operação.

### Campos proibidos nos metadados

Não registre nem armazene conteúdo da imagem, URLs privadas, credenciais, tokens,
chaves de API ou qualquer outro segredo. Os metadados servem apenas para rastrear a
decisão de roteamento.
