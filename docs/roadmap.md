# Roadmap

Itens planejados para desenvolvimento futuro. Nenhum item aqui é obrigatório no fluxo atual.

## Publicação no LinkedIn — skill de navegação

**Contexto:** o fluxo de publicação corporativa via Zernio está **depreciado** (não haverá contas
corporativas em rede social). O destino do conteúdo aprovado é a publicação manual assistida no
LinkedIn via uma skill que usa a navegação do OpenWork (browser já logado, sem credenciais).

**Status do design (26/08/2026):** aprovado. Fluxo: `content/approved/<arquivo>.md` → skill →
browser OpenWork logado → nova publicação → cola conteúdo → agendamento.

### Implementado (escopo atual)
- Publicação **agora**: skill cola o conteúdo e **pausa** antes do clique final, para a pessoa
  anexar imagem manualmente; conclui ao receber o comando.
- Publicação **agendada** (dia/horário): skill preenche data/hora e agenda; a pessoa valida no
  próprio LinkedIn antes do disparo.
- Formatação: **opção B** — converte Markdown em texto pronto para colagem limpa (sem `**`
  literais, remove `#` de título, mantém quebras de linha, emojis e hashtags).
- Invocação: **opção A** — a pessoa informa o arquivo e o agendamento na chamada.
- Aprovação de texto já ocorreu no pipeline (estar em `content/approved/` = aprovado); a skill
  **não** revalida o conteúdo.

### Futuro (roadmap registrado)
- [ ] **Anexar imagem automaticamente** na postagem (hoje o anexo é manual, só no envio "agora").
- [ ] Suporte a múltiplas contas/redes (fora de escopo por enquanto; sem contas corporativas).
- [ ] Qualquer automação de métricas/analytics pós-publicação (depreciado com o Zernio).

---
