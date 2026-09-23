# Editorial Quality Gates — Design

## Objetivo

Impedir que o pipeline avance um brief ou draft apenas porque recebeu um JSON estruturalmente válido. Cada review deve demonstrar, com evidência textual, que o artefato tem contexto, coesão e decisão operacional suficientes.

## Decisão

Manter os nove stages canônicos, mas separar persistência de qualidade: `persist_stage` só aceita uma review aprovada quando o contrato editorial correspondente estiver preenchido. Reviews de brief devem registrar evidência, contexto do leitor, linha narrativa, decisão, consequência e limites. Reviews de draft devem registrar evidência dos batimentos narrativos, transições e mecanismo operacional.

Reviews com notas perfeitas, mas sem justificativas textuais, serão rejeitadas. Feedback deve apontar o trecho ou a afirmação que exige mudança. O executor não cria reviews; ele apenas valida e persiste a review produzida pela etapa editorial.

## Fluxo

1. `research-topic` produz brief.
2. `brief_review_gauntlet` valida contexto, evidência principal, linha causal, decisão, consequência e limites.
3. `write-post` produz draft a partir do brief.
4. `critique-post` valida promessa, quebra, reação, custo, coesão entre parágrafos e contexto para o leitor.
5. `correction_gauntlet` só avança se todo feedback acionável tiver sido resolvido.
6. As passagens de humanização preservam a tese e revalidam a coesão; nenhuma delas pode ser marcada aprovada por notas genéricas.

## Estado e falha

Qualquer ausência de evidência editorial bloqueia o stage atual. O topic não recebe `drafted` até `humanize_review_2` passar. Drafts existentes sem comprovação substancial retornam para revisão e não podem ser enviados ao QA humano.

## Testes de aceitação

- Review estruturalmente válida, com todos os critérios em 10, mas sem evidência editorial, falha.
- Review com evidência específica para brief e draft passa quando os gates estão completos.
- O caso de duas etapas compartilharem o mesmo artefato continua idempotente.
- O topic 09 permanece `drafted` apenas depois de uma review substantiva; até lá, fica marcado para reescrita.
