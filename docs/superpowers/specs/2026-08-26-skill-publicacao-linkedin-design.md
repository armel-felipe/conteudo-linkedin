# Design — Skill de publicação no LinkedIn (navegação assistida)

- **Data:** 26/08/2026
- **Status:** aprovado (design)
- **Escopo:** skill que publica conteúdo aprovado no LinkedIn usando o browser do OpenWork já logado

---

## Contexto e motivação

O fluxo de publicação corporativa via Zernio está **depreciado** (não haverá contas corporativas em
rede social). O destino do conteúdo aprovado em `content/approved/` passa a ser a **publicação
assistida no LinkedIn** via uma skill que usa a capacidade de navegação do OpenWork (browser já
logado, sem credenciais).

O pipeline de produção de conteúdo é **local** (pesquisa → ideia → draft → revisão → aprovação) e
não depende de Zernio. Esta skill é a camada final: leva o arquivo aprovado até o LinkedIn.

---

## Fluxo (visão geral)

```
content/approved/<arquivo>.md
   ↓  skill de publicação (navegação no browser do OpenWork já logado)
nova publicação no LinkedIn
   ↓ cola conteúdo (texto ajustado, sem rich-text)
agendamento
   ├─ "agora":          pausa → pessoa anexa imagem manualmente → comando para concluir
   └─ dia/horário:      agenda direto (pessoa valida no LinkedIn antes do disparo)
```

---

## Decisões de design (aprovadas)

### 1. Formatação do conteúdo — **Opção B (texto simples + convenções)**
- A skill converte o Markdown em **texto pronto para colagem limpa**: remove `#` de título,
  converte/remove `**` para não vazar literal, mantém quebras de linha, emojis e hashtags.
- Não depende de formatação rich-text do LinkedIn (mais simples e robusto).

### 2. Invocação — **Opção A (por argumento)**
- A pessoa informa o **arquivo** e o **agendamento** na chamada:
  - `Publica content/approved/artigo-l5-ia-fosso.md agora`
  - `Publica content/approved/artigo-l5-ia-fosso.md amanhã às 9h`
- A skill valida que o arquivo existe em `content/approved/`.

### 3. Acesso ao LinkedIn — **Opção A (sessão já logada)**
- A skill usa o browser do OpenWork **já logado**; **nunca** guarda/login ou senha.
- Respeita o `AGENTS.md` (sem credenciais em chat, arquivos versionados, banco ou commits).

### 4. Ponto de espera — **só no envio "agora" (para anexar imagem)**
- O texto em `content/approved/` **já está aprovado** (filtros do pipeline + revisão pessoal).
- A skill **não** pede nova confirmação textual.
- **Agendamento (dia/horário):** a skill agenda direto; a pessoa valida no próprio LinkedIn
  antes do disparo.
- **Envio "agora":** a skill cola o conteúdo e **pausa** antes do clique final, para a pessoa
  poder **anexar imagem manualmente**; conclui ao receber o comando.

---

## Componentes da skill

1. **Localizador de arquivo** — resolve o caminho em `content/approved/`, valida existência.
2. **Preparador de texto** — converte Markdown → texto LinkedIn (opção B).
3. **Navegação** — abre/navega no browser do OpenWork logado até a área de nova publicação.
4. **Colagem** — insere o conteúdo no campo do post.
5. **Agendamento** — aplica "agora" ou dia/horário; orquestra o ponto de espera.

---

## Fora do escopo (roadmap registrado em `docs/roadmap.md`)

- **Anexar imagem automaticamente** na postagem (futuro; hoje manual e só no envio "agora").
- Suporte a múltiplas contas/redes (sem contas corporativas).
- Automação de métricas/analytics pós-publicação (depreciado com o Zernio).

---

## Verificação

- Sem novas credenciais introduzidas; a skill depende da sessão do browser já logada.
- O conteúdo publicado vem somente de `content/approved/` (aprovado).
- Envios "agora" sempre passam pelo ponto de espera (anexo manual de imagem).
- Agendamentos são validáveis no LinkedIn antes do disparo.
