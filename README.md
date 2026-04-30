# HolyRead — Bíblia

> App de leitura bíblica moderno, responsivo e multilíngue. MVP desenvolvido para validar a experiência de leitura antes de ser integrado ao ecossistema **HolyPleiiiz**.

---

## Sumário

1. [Visão geral](#visão-geral)
2. [Funcionalidades](#funcionalidades)
3. [Arquitetura](#arquitetura)
4. [Dados](#dados)
5. [Rodando localmente](#rodando-localmente)
6. [Publicação na Internet](#publicação-na-internet)
   - [GitHub Pages (gratuito, recomendado para MVP)](#opção-1-github-pages--gratuito)
   - [Netlify (gratuito, CI/CD automático)](#opção-2-netlify--gratuito)
   - [Vercel (gratuito, CDN global)](#opção-3-vercel--gratuito)
   - [Cloudflare Pages (melhor performance global)](#opção-4-cloudflare-pages--gratuito)
   - [Servidor próprio / VPS (produção avançada)](#opção-5-servidor-próprio--vps)
7. [Estratégia de cache e performance](#estratégia-de-cache-e-performance)
8. [Roadmap de integração com HolyPleiiiz](#roadmap-de-integração-com-holypleiiiz)
9. [Variáveis e configurações](#variáveis-e-configurações)
10. [Estrutura de pastas](#estrutura-de-pastas)

---

## Visão geral

HolyRead é um app de leitura bíblica **100% client-side** — não há backend, banco de dados ou servidor de aplicação. Todo o processamento acontece no navegador do usuário.

Isso significa:

- **Custo de hospedagem próximo de zero** (qualquer CDN estático serve)
- **Sem dados de usuário armazenados em servidor** (preferências ficam no `localStorage`)
- **Offline parcial possível** via Service Worker (próxima versão)
- **Escala infinita** sem custo adicional (o CDN absorve qualquer número de usuários)

---

## Funcionalidades

| Funcionalidade | Detalhe |
|---|---|
| 7 versões bíblicas | NVI, AA, ACF (PT) · KJV, BBE (EN) · RVR (ES) · APEE (FR) |
| Dark / Light mode | Tema salvo por usuário |
| Tamanho de fonte | Slider 12–26 px, salvo por usuário |
| Navegação por livro | Sidebar com filtro, separação AT/NT |
| Navegação por capítulo | Pills clicáveis, swipe mobile |
| Busca inteligente | Referência (`João 3:16`) + texto livre |
| Seleção e compartilhamento | Multi-versículo → WhatsApp, Twitter, Facebook, Copiar |
| Text-to-Speech | Vozes do sistema com auto-seleção da melhor qualidade |
| Seletor de voz | Lista todas as vozes disponíveis no idioma, ranqueadas |
| Velocidade de leitura | 0.75×, 1×, 1.25×, 1.5× |
| Progresso salvo | Última posição (livro + capítulo) no `localStorage` |
| Atalhos de teclado | `←/→` capítulo anterior/próximo · `/` abre busca · `Esc` fecha painéis |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Navegador do Usuário                        │
│                                                                     │
│  ┌─────────────┐   fetch()    ┌───────────────────────────────────┐ │
│  │  index.html │ ──────────▶  │  data/{versao}.json               │ │
│  │  (app SPA)  │             │  ~4 MB por versão, carregado      │ │
│  │             │             │  sob demanda e cacheado em RAM     │ │
│  │  CSS inline │◀─────────── │                                   │ │
│  │  JS inline  │  resposta   └───────────────────────────────────┘ │
│  └─────────────┘                                                    │
│         │                                                           │
│         │  localStorage                                             │
│         ▼                                                           │
│  ┌──────────────────────────────────────────┐                      │
│  │  holyread_prefs                          │                      │
│  │  { version, bookIdx, chapterIdx,         │                      │
│  │    theme, fontSize }                     │                      │
│  └──────────────────────────────────────────┘                      │
│                                                                     │
│         │  Web Speech API (SpeechSynthesis)                        │
│         ▼                                                           │
│  ┌──────────────────────────────────────────┐                      │
│  │  Sistema Operacional / Browser           │                      │
│  │  (vozes TTS nativas + Google voices)     │                      │
│  └──────────────────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │  HTTPS
                              ▼
              ┌───────────────────────────────┐
              │   CDN / Hospedagem Estática   │
              │  (GitHub Pages / Netlify /    │
              │   Vercel / Cloudflare Pages)  │
              └───────────────────────────────┘
```

### Decisões de design

**Por que um único arquivo HTML?**
Para o MVP, um `index.html` com CSS e JS embutidos elimina build steps, bundlers e configuração. O código é revisável diretamente no browser. A única dependência externa é a fonte Google Inter+Lora (opcional — o app funciona com system fonts se offline).

**Por que os JSONs ficam fora do HTML?**
Cada versão tem ~4 MB. Embutir todas as 7 versões criaria um arquivo de ~28 MB, tornando o carregamento inicial inaceitável. O app carrega apenas a versão selecionada, sob demanda, e mantém um cache em memória (`state.cache`) para não refazer o fetch em trocas de versão.

**Por que não há backend?**
Para este MVP não há necessidade de autenticação, sincronização entre dispositivos ou dados personalizados. O `localStorage` é suficiente para persistir preferências locais. Quando a integração com HolyPleiiiz exigir accounts compartilhados, um backend (ver roadmap) será adicionado.

### Fluxo de dados

```
Usuário seleciona versão
        │
        ▼
loadVersion(version)
  ├── hit: state.cache[version] → retorna imediato
  └── miss: fetch data/{version}.json
              │
              ▼
           JSON.parse (remove BOM se presente)
              │
              ▼
        state.cache[version] = data   ← fica em RAM até reload
              │
              ▼
        renderBookList()
        renderChapterPills()
        renderChapter()
              │
              ▼
        DOM: div.verse-block por versículo
        (clique → seleção/compartilhamento)
        (TTS → Web Speech API com melhor voz disponível)
```

### Módulo de Vozes TTS

A Web Speech API expõe vozes heterogêneas em qualidade. O app aplica um ranqueamento automático:

| Pontuação | Critério | Exemplo |
|---|---|---|
| 5 | Google Neural / WaveNet | "Google português do Brasil" (Chrome) |
| 4 | Google standard | "Google US English" |
| 3 | Enhanced / Premium / Siri | "Luciana Enhanced" (Safari macOS) |
| 2 | Voz cloud (não local) | Vozes de servidores do browser |
| 1 | Voz local padrão | "Luciana" (macOS system) |

A melhor voz disponível para o idioma atual é pré-selecionada. O usuário pode trocar pelo seletor na barra de TTS.

---

## Dados

```
data/
├── pt_nvi.json   # Nova Versão Internacional  — 66 livros, 31.105 versículos, 3,9 MB
├── pt_aa.json    # Almeida Atualizada          — 66 livros, 31.104 versículos, 3,9 MB
├── pt_acf.json   # Almeida Corrigida Fiel      — 66 livros, 31.106 versículos, 3,9 MB
├── en_kjv.json   # King James Version          — 66 livros, 31.100 versículos, 4,4 MB
├── en_bbe.json   # Bible in Basic English      — 66 livros, 31.104 versículos, 4,2 MB
├── es_rvr.json   # Reina-Valera Revisada       — 66 livros, 31.102 versículos, 3,9 MB
└── fr_apee.json  # Alliance Permanente (FR)    — 66 livros, 30.975 versículos, 4,3 MB
```

**Formato de cada arquivo:**

```json
[
  {
    "abbrev": "gn",
    "chapters": [
      ["No princípio Deus criou os céus e a terra.", "Era a terra sem forma..."],
      ["Adão conheceu sua mulher Eva..."]
    ]
  },
  ...
]
```

- Array raiz: 66 livros (Gênesis → Apocalipse, mesma ordem em todas as versões)
- Mapeamento de livro: **por índice** (0–65), não por `abbrev` — as abreviações diferem entre versões
- Encoding: UTF-8 com BOM (`﻿`) — o app remove automaticamente no browser

---

## Rodando localmente

**Pré-requisito:** Python 3 (qualquer versão) ou Node.js

```bash
# Clone ou baixe o projeto
cd holypleiiiz-bible

# Python 3
python3 -m http.server 8080

# Node.js (sem instalar nada)
npx serve . -p 8080

# Node.js com http-server global
npx http-server -p 8080
```

Acesse: **http://localhost:8080**

> O app **não funciona** via `file://` porque o `fetch()` dos JSONs é bloqueado pelo browser por política de CORS. É necessário um servidor HTTP, mesmo que local.

---

## Publicação na Internet

O projeto é **100% estático** — qualquer serviço de hospedagem de arquivos estáticos funciona. Abaixo as opções em ordem de recomendação para cada perfil.

---

### Opção 1: GitHub Pages — Gratuito

Ideal para: MVP rápido, repositório já no GitHub.

```bash
# 1. Crie o repositório no GitHub
git init
git add .
git commit -m "feat: HolyRead MVP"
git remote add origin https://github.com/SEU_USUARIO/holyread.git
git push -u origin main

# 2. Ative GitHub Pages
# GitHub → Settings → Pages → Branch: main → Folder: / (root) → Save
```

URL resultante: `https://SEU_USUARIO.github.io/holyread`

**Limitação:** arquivos até 100 MB por arquivo, 1 GB por repositório (os JSONs somam ~28 MB, dentro do limite). Sem CDN geográfico avançado — latência maior fora do datacenter do GitHub (EUA).

---

### Opção 2: Netlify — Gratuito

Ideal para: deploy automático a cada `git push`, previews de PR, domínio próprio.

```bash
# Via CLI
npm install -g netlify-cli
netlify login
netlify deploy --dir . --prod
```

Ou arraste a pasta para **app.netlify.com/drop**.

**Configuração recomendada** — crie `netlify.toml` na raiz:

```toml
[build]
  publish = "."

[[headers]]
  for = "/data/*.json"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
    Content-Encoding = "gzip"

[[headers]]
  for = "/*.html"
  [headers.values]
    Cache-Control = "public, max-age=3600"
```

URL resultante: `https://nome-aleatorio.netlify.app` (personalizável gratuitamente)

---

### Opção 3: Vercel — Gratuito

Ideal para: integração futura com Next.js / API routes quando o backend for necessário.

```bash
npm install -g vercel
vercel login
vercel --prod
```

**Configuração** — crie `vercel.json`:

```json
{
  "headers": [
    {
      "source": "/data/(.*).json",
      "headers": [
        { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" },
        { "key": "Content-Type", "value": "application/json; charset=utf-8" }
      ]
    }
  ]
}
```

URL resultante: `https://holyread.vercel.app`

---

### Opção 4: Cloudflare Pages — Gratuito

Ideal para: melhor latência global (rede Cloudflare em 300+ cidades), futura integração com Cloudflare Workers (lógica serverless) e D1 (banco de dados edge).

```bash
# Via CLI
npm install -g wrangler
wrangler pages deploy . --project-name holyread
```

Ou conecte o repositório GitHub em **pages.cloudflare.com**.

**Por que Cloudflare para produção?**
- Os JSONs (~4 MB cada) são cacheados na borda da rede mais próxima do usuário
- Brasil tem PoPs em São Paulo, Rio de Janeiro e Fortaleza — latência < 20ms para usuários brasileiros
- Cloudflare Workers permite adicionar lógica serverless (ex.: analytics, autenticação JWT) sem mudar a arquitetura estática
- Integração natural com Cloudflare D1 (SQLite na borda) para dados de usuário futuros

---

### Opção 5: Servidor próprio / VPS

Para quando precisar de backend completo (integração com HolyPleiiiz, autenticação, banco de dados).

**Stack recomendada:**

```
Internet
    │
    ▼
Cloudflare (proxy + WAF + DDoS)
    │
    ▼
Nginx (reverse proxy + TLS + gzip + cache headers)
    │
    ├── /              → arquivos estáticos (index.html + data/*.json)
    └── /api/v1/       → backend HolyPleiiiz (Node.js / FastAPI)
```

**Configuração Nginx mínima:**

```nginx
server {
    listen 443 ssl http2;
    server_name holyread.com.br;

    ssl_certificate     /etc/letsencrypt/live/holyread.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/holyread.com.br/privkey.pem;

    root /var/www/holyread;
    index index.html;

    # Cache agressivo para os JSONs (imutáveis)
    location /data/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        gzip_static on;
    }

    # HTML: cache curto para receber atualizações
    location / {
        try_files $uri $uri/ /index.html;
        expires 1h;
        add_header Cache-Control "public, must-revalidate";
    }
}
```

**Compressão dos JSONs (economiza ~70% de banda):**

```bash
# Pré-comprimir os JSONs para Nginx gzip_static
for f in data/*.json; do
  gzip -9 -k "$f"
done
# Gera: data/pt_nvi.json.gz (~1.1 MB em vez de 3.9 MB)
```

---

## Estratégia de cache e performance

Os arquivos JSON são o maior custo de carregamento (~4 MB por versão). A estratégia de cache em camadas elimina esse custo para usuários recorrentes:

```
Requisição do usuário
        │
        ▼
┌───────────────────┐
│  Cache em RAM     │  state.cache  ← instante (já carregado nesta sessão)
│  (JavaScript)     │
└────────┬──────────┘
         │ miss
         ▼
┌───────────────────┐
│  Cache do browser │  HTTP Cache-Control  ← < 10ms se em disco
│  (disco local)    │
└────────┬──────────┘
         │ miss
         ▼
┌───────────────────┐
│  CDN Edge         │  PoP mais próximo  ← 20–100ms (Brasil)
└────────┬──────────┘
         │ miss
         ▼
┌───────────────────┐
│  Servidor origem  │  ~200–500ms (primeira vez)
└───────────────────┘
```

**Headers recomendados para os JSONs:**
```
Cache-Control: public, max-age=31536000, immutable
Content-Encoding: gzip
ETag: "<hash-do-arquivo>"
```

Os JSONs são dados estáticos (o texto bíblico não muda). `immutable` informa ao browser que nunca precisa revalidar — zero requisições de rede para versões já visitadas.

---

## Roadmap de integração com HolyPleiiiz

```
Fase 1 — MVP atual (✅ concluído)
  └── HolyRead standalone: leitura, busca, TTS, compartilhamento

Fase 2 — Unificação de identidade
  ├── Login único (OAuth Google / Apple)
  ├── Progresso de leitura sincronizado em nuvem
  └── Backend: Node.js + PostgreSQL ou Firebase

Fase 3 — Integração com Quiz
  ├── Botão "Testar sobre este capítulo" → HolyPleiiiz Quiz
  ├── Plano de leitura vinculado a trilhas do quiz
  └── Compartilhamento de conquistas

Fase 4 — Features avançadas
  ├── Destaques e notas pessoais (sincronizados)
  ├── Modo offline completo (Service Worker + Cache API)
  ├── Planos de leitura (ex.: Bíblia em 1 ano)
  └── Versão PWA instalável (manifest.json)
```

**Sugestão de arquitetura unificada (Fase 2):**

```
holyread.com.br          → HolyRead (este app)
holypleiiiz.com.br/quiz  → Quiz existente
holypleiiiz.com.br/api   → API compartilhada (auth, progresso, usuários)

ou

app.holypleiiiz.com.br/
  ├── /read   → HolyRead
  └── /quiz   → HolyPleiiiz Quiz
```

---

## Variáveis e configurações

Todas as configurações ficam no início do script em `index.html`:

| Constante | Descrição |
|---|---|
| `BOOK_NAMES` | Nomes dos 66 livros em PT, EN, ES, FR |
| `VERSION_LANG` | Mapeamento versão → idioma (`pt_nvi → 'pt'`) |
| `VERSION_LABEL` | Labels curtos exibidos na UI (`pt_nvi → 'NVI'`) |
| `TTS_LANG` | Código BCP-47 por idioma (`pt → 'pt-BR'`) |
| `OT_END` | Índice do último livro do AT (38 = Malaquias) |

**Preferências do usuário** (salvas em `localStorage` como `holyread_prefs`):

```json
{
  "version": "pt_nvi",
  "bookIdx": 42,
  "chapterIdx": 2,
  "theme": "dark",
  "fontSize": 19
}
```

---

## Estrutura de pastas

```
holypleiiiz-bible/
│
├── index.html          # App completo (HTML + CSS + JS em arquivo único)
├── serve.sh            # Servidor local de desenvolvimento
├── README.md           # Este arquivo
│
└── data/               # Versões bíblicas em JSON (~28 MB total)
    ├── pt_nvi.json     # Nova Versão Internacional (Português)
    ├── pt_aa.json      # Almeida Atualizada (Português)
    ├── pt_acf.json     # Almeida Corrigida Fiel (Português)
    ├── en_kjv.json     # King James Version (Inglês)
    ├── en_bbe.json     # Bible in Basic English (Inglês)
    ├── es_rvr.json     # Reina-Valera Revisada (Espanhol)
    └── fr_apee.json    # Alliance Permanente (Francês)
```

---

## Licença dos dados bíblicos

Os textos utilizados são versões de domínio público ou de uso livre para fins não-comerciais. Verifique os termos de cada versão antes de uso comercial, especialmente NVI (Biblica) e RVR (Sociedades Bíblicas).

---

*HolyRead é o módulo de leitura do ecossistema HolyPleiiiz — estimulando pessoas a lerem a Bíblia todos os dias.*
# HolyRead
