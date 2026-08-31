# Política de visão nativa antes do fallback

## Objetivo

Garantir que toda tarefa visual do projeto tente primeiro a capacidade nativa de visão do modelo hospedeiro. O `image-analyzer` será usado somente quando o modelo não possuir visão ou quando a tentativa nativa falhar tecnicamente.

## Escopo

A política vale para todas as skills e tarefas visuais do projeto, não apenas para `publicar-linkedin`. Skills visuais devem referenciar esta política central em vez de definir uma ordem diferente.

## Protocolo obrigatório

Ao receber uma imagem:

1. Verificar se o modelo hospedeiro possui capacidade de visão.
2. Se possuir, analisar a imagem diretamente.
3. Se não possuir visão, delegar ao subagente `image-analyzer`.
4. Se a visão nativa falhar por incapacidade técnica, delegar ao `image-analyzer` como fallback.
5. Nunca delegar antes da tentativa nativa quando houver visão disponível.
6. Se nenhuma rota funcionar, informar a limitação sem inventar conteúdo.

O protocolo distingue explicitamente modelo com visão, modelo sem visão, falha da visão nativa e imagem ilegível/corrompida.

## Aplicação

A regra será implementada em uma skill compartilhada:

`.agents/skills/visao-nativa-primeiro/SKILL.md`

`publicar-linkedin/SKILL.md` e qualquer outra skill visual deverão referenciá-la. A política não altera o modelo nem cria uma detecção artificial de capacidades; o runtime OpenCode é a fonte da decisão sobre a visão nativa disponível.

## Rastreabilidade

O runtime registra internamente, quando aplicável:

- rota: `native` ou `image-analyzer`;
- motivo do fallback;
- se a análise foi direta ou delegada;
- limitações de legibilidade.

Esses registros não devem conter dados privados da imagem, credenciais ou tokens. A resposta ao usuário só menciona o fallback quando isso for relevante para a confiabilidade do resultado.

## Falhas

- Modelo com visão: análise nativa, sem delegação.
- Modelo sem visão: delegação ao `image-analyzer`.
- Falha nativa: fallback ao `image-analyzer` e registro do motivo.
- Falha do fallback: informar que a análise não foi possível.
- Imagem ilegível ou corrompida: informar a limitação e não inferir conteúdo.

## Testes de aceitação

1. Modelo com visão analisa diretamente e não chama `image-analyzer`.
2. Modelo sem visão delega ao `image-analyzer`.
3. Falha nativa aciona o fallback.
4. Falha do fallback informa a limitação.
5. Imagem ilegível/corrompida não gera conteúdo inventado.
6. Todas as skills visuais referenciam a política central.
7. Registros de rota não expõem segredos nem conteúdo sensível.
