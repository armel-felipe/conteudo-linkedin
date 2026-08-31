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

Se a leitura nativa for bem-sucedida, responda usando somente o que foi observado na
imagem e entregue o resultado pedido pela pessoa.

### Modelo sem visão nativa

Quando o modelo atual não consegue ver imagens, não tente visão nativa.

**Rota obrigatória: `image-analyzer`.**

Informe que a análise foi delegada ao `image-analyzer` e use somente o resultado que
ele devolver, sem tentar completar a leitura por conta própria.

### Falha da visão nativa

Quando a tentativa nativa falhar, estiver indisponível ou retornar erro, delegue a
análise ao fallback visual.

**Rota obrigatória: `image-analyzer`.**
**Motivo: `native_failed`.**

Informe que a visão nativa falhou e que a análise foi encaminhada ao fallback visual.
Use somente o resultado do `image-analyzer` se ele estiver disponível.

### Falha do image-analyzer

Quando o fallback visual também falhar, não há rota adicional.

**Rota obrigatória: nenhuma.**

Responda com uma limitação de leitura e não produza inferência, texto, objetos,
valores ou contexto não observados.

Informe que o fallback visual falhou e que não foi possível ler a imagem.

### Imagem ilegível ou corrompida

Quando a imagem estiver ilegível, corrompida ou inacessível, não trate seus dados como
evidência.

**Rota obrigatória: nenhuma.**

Responda com uma limitação de leitura e não produza inferência, preenchimento por
suposição ou conteúdo inventado.

Informe que a imagem não pôde ser lida e que nenhum resultado confiável pode ser
produzido.

Este documento define o protocolo de roteamento; não implementa detecção automática
de capacidade do modelo nem validação automática de arquivos.

## Metadados internos

### Campos permitidos nos metadados

- `route`: `native` ou `image-analyzer`;
- `reason`: `no_native_vision`, `native_failed` ou `unreadable_image`;
- modo de delegação;
- limitação de legibilidade.

### Campos proibidos nos metadados

Não registre nem armazene conteúdo da imagem, URLs privadas, credenciais, tokens,
chaves de API ou qualquer outro segredo. Os metadados servem apenas para rastrear a
decisão de roteamento.
