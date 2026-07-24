# Operação pessoal de conteúdo para LinkedIn - Design

## Objetivo

Criar uma operação pessoal de conteúdo para LinkedIn que ajude a construir autoridade em até cinco temas e a buscar oportunidades profissionais. O sistema deve permitir operar o fluxo tanto pelo Codex quanto pelo Hermes Agent via Telegram, sem criar uma interface própria de chat ou integrar diretamente o Telegram.

A primeira vitória é: em uma semana, importar e analisar o histórico disponível, aprovar cinco pilares editoriais e deixar duas publicações revisadas e agendadas.

## Escopo do primeiro produto

O produto é de uso individual. Ele não terá multiusuário, cobrança, painel web ou publicação autônoma.

Ele deve:

- Importar postagens anteriores do LinkedIn pelo Zernio e categorizá-las.
- Propor até cinco pilares editoriais apoiados no histórico importado.
- Pesquisar sinais e conversas recentes usando Last30days.
- Transformar sinais em ideias e rascunhos rastreáveis.
- Manter uma cadência inicial de duas postagens por semana.
- Usar texto como formato principal, com imagem opcional.
- Exigir aprovação explícita antes de qualquer agendamento ou publicação.
- Agendar postagens aprovadas pelo Zernio e registrar resultados posteriores.

Fora de escopo no primeiro produto:

- Integração direta com Hermes ou Telegram.
- Publicação automática.
- Carrosséis e documentos LinkedIn como formato editorial recorrente.
- Painel web.
- Autenticação para outros usuários.

## Decisões de arquitetura

Markdown é a fonte de verdade editorial: contém a pesquisa, o contexto, o rascunho, as fontes e a decisão humana. SQLite é o índice operacional: contém estados, identificadores do Zernio, agenda e métricas. Scripts são a única camada autorizada a sincronizar dados e agendar posts.

```text
Markdown
  pesquisa -> brief -> rascunho -> aprovação -> resultado
                  |
SQLite            v
  catálogo, estados, IDs, agenda e métricas
                  |
Scripts           v
  importar | classificar | pesquisar | validar | agendar | medir
                  |
Zernio API <-> LinkedIn
```

`AGENTS.md` será o contrato de operação para Codex e Hermes. Ele definirá comandos permitidos, regras de aprovação e a proibição de expor credenciais. O Hermes continuará responsável pela conversa com o Telegram e apenas executará ou solicitará os mesmos comandos locais usados pelo Codex.

## Fluxo

### Fundação

1. Importar o histórico disponível via Zernio.
2. Categorizar os posts e propor até cinco pilares editoriais.
3. O usuário aprova ou ajusta os pilares.

Esta fase ocorre inicialmente e pode ser repetida quando o usuário quiser recalibrar a estratégia.

### Operação recorrente

```text
Last30days pesquisa sinais recentes
        |
        v
ideias associadas a um pilar
        |
        v
priorização por oportunidade profissional, relevância e novidade
        |
        v
rascunho Markdown
        |
        v
decisão humana: revisar | descartar | aprovar
        |
        v
agendamento via Zernio
        |
        v
publicação, métricas e aprendizado
```

Estados permitidos: `idea`, `draft`, `in_review`, `approved`, `scheduled`, `published`, `rejected`, `archived`, `failed` e `indeterminate`.

A pesquisa nunca agenda. O agendamento exige, ao mesmo tempo, um post com estado `approved` e uma confirmação final na conversa. Falhas confirmadas de publicação mudam o post para `failed`; não há republicação automática. Se o Zernio puder ter recebido a solicitação, mas o resultado não puder ser persistido localmente, o post muda para `indeterminate`, bloqueia novos agendamentos e exige reconciliação usando a mesma chave de idempotência.

## Estrutura de diretórios

```text
AGENTS.md
docs/
  strategy.md
  pillars.md
research/
  YYYY-MM-DD--tema.md
content/
  ideas/
  drafts/
  approved/
  published/
calendar/
  YYYY-Www.md
data/
  content.db
  imports/
scripts/
  contentctl
  zernio/
  analysis/
```

Cada post em Markdown deve trazer metadados com: identificador local, pilar, estado, objetivo profissional, fontes, texto, imagem opcional, horário sugerido, ID do Zernio, URL publicada e métricas capturadas.

## Interface operacional

A CLI única será `contentctl`. Codex e Hermes usam a mesma interface e os mesmos artefatos.

Comandos iniciais:

```text
contentctl history import
contentctl pillars propose
contentctl research discover "<assunto>"
contentctl ideas list
contentctl draft create <ideia>
contentctl review approve <post>
contentctl schedule <post> --at "<data-hora>"
contentctl report weekly
```

## Segurança e qualidade

- `ZERNIO_API_KEY` fica exclusivamente em `.env` local e nunca em Markdown, SQLite ou Git.
- A ausência de credenciais impede apenas sincronização e publicação; o fluxo editorial continua utilizável.
- Importações são idempotentes e não duplicam registros.
- Antes de agendar, validar: estado aprovado, texto não vazio, pilar definido, horário futuro, conta LinkedIn configurada e imagem acessível quando indicada.
- Guardar o ID retornado pelo Zernio para impedir agendamentos duplicados.
- Registrar a diferença entre evidência recente, interpretação editorial e texto sugerido.
- Testar máquina de estados, importação idempotente, validações e o cliente Zernio com respostas simuladas.

## Critérios de aceite da primeira entrega

1. `history import` cria uma base local sem publicar nada.
2. `pillars propose` gera uma proposta de cinco pilares apoiada no histórico.
3. Uma pesquisa resulta em uma ideia e em um rascunho rastreável em Markdown.
4. Dois posts podem ser aprovados e agendados manualmente, sem risco de publicação acidental.
