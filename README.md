# HolyRead — V1

> Leitor bíblico multilíngue com **estudo no original** (Hebraico / Grego).
> Frontend estático + backend FastAPI publicáveis separadamente.

---

## Sumário

1. [Visão geral V1](#visão-geral-v1)
2. [Arquitetura](#arquitetura)
3. [Dados e licenças](#dados-e-licenças)
4. [Rodando localmente](#rodando-localmente)
5. [QR code para celular na rede local](#qr-code-para-celular-na-rede-local)
6. [Pipeline de ETL (originais)](#pipeline-de-etl-originais)
7. [Endpoints da API](#endpoints-da-api)
8. [Deploy](#deploy)
9. [Estrutura de pastas](#estrutura-de-pastas)
10. [Roadmap](#roadmap)

---

## Visão geral V1

A V0 (MVP) era um único `index.html` que carregava JSONs estáticos. A V1 separa as responsabilidades:

- **Backend** (`backend/`) — FastAPI em Python servindo as Bíblias e os textos no original (Hebraico/Grego) com palavra-por-palavra (lema, Strong's, morfologia, transliteração).
- **Frontend** (`frontend/`) — site estático que consome a API. Todas as features da V0 mais um módulo novo: **📜 Original**.
- **Segurança** — CORS allowlist, rate-limit por IP, security headers. HTTPS obrigatório em produção (Railway provê).
- **Persistência local** — preferências e progresso ainda em `localStorage`. Sincronização com MongoDB ficou para V2.

### Novidade: módulo "Original"

Tocando num versículo do AT, o botão **📜 Original** abre um *bottom sheet* com:

- Texto hebraico apontado (RTL, com cantilação preservada)
- Palavra a palavra: forma original → transliteração → morfemas (prefixo / raiz) → Strong's → morfologia
- 🔊 Pronúncia em hebraico (Web Speech API, voz `he-IL`)

No NT: o mesmo, com texto grego, lema, morfologia e **toggle Erasmiana / Moderna** afetando transliteração e pronúncia.

---

## Arquitetura

```
┌─────────────────────────┐         ┌──────────────────────────────────┐
│ Frontend (estático)     │         │ Backend (FastAPI / Railway)      │
│  - index.html           │  HTTPS  │  /api/bible/...    Bíblias       │
│  - assets/api.js  ──────┼────────►│  /api/original/he/...  Hebraico  │
│  - config.js (API_BASE) │  CORS   │  /api/original/grc/... Grego     │
│ Hospedagem: Pages /     │ allow + │  Rate-limit / security headers   │
│ Render / Usevelty       │ rate    │  Dados em data/ (JSON pré-ETL)   │
└─────────────────────────┘         └──────────────────────────────────┘
```

- **Frontend** é puro HTML/CSS/JS — nenhum build step. Pode ser publicado em qualquer CDN estática.
- **Backend** roda em qualquer host com Docker. `railway.toml` está pronto.
- Todo dado é JSON estático em `backend/data/` — nada de banco. Os arquivos são gerados uma vez via ETL e versionados (ou montados num volume).

---

## Dados e licenças

### Bíblias (frontend MVP)

7 traduções já existentes de domínio público / livre uso (`backend/data/bible/*.json`). Mantidas como estavam na V0.

### Hebraico — `openscriptures/morphhb` (WLC)

- **Licença**: CC BY 4.0 — uso comercial OK.
- **Conteúdo**: Westminster Leningrad Codex pontuado, com lemma (Strong's hebraico) e morfologia OSHM.
- **Versificação**: massorética; mapeada para a numeração protestante via `wlc/VerseMap.xml`.
- **Transliteração**: gerada por nós (`backend/scripts/translit_he.py`, esquema SBL simplificado).

### Grego — `morphgnt/sblgnt`

- **Texto SBLGNT**: CC BY 4.0 (Faithlife). Atribuição requerida.
- **Análise morfológica MorphGNT**: **CC BY-SA 3.0** — derivados redistribuídos precisam manter a mesma licença.
- **Transliteração**: gerada por nós (`backend/scripts/translit_grc.py`, esquemas Erasmiana e Moderna).

### Glossas (literal por palavra) — STEPBible TBESH/TBESG

- `Lexicons/TBESH ... CC BY.txt` (Hebraico)
- `Lexicons/TBESG ... CC BY.txt` (Grego)
- **Licença**: CC BY 4.0 (Tyndale House Cambridge — usamos somente a coluna `Gloss`, autoria Tyndale; a coluna `Meaning` vem do BDB Online Bible com restrições próprias e **não** é usada).
- Cobertura: ~99% das palavras do NT, ~95% das raízes do AT.

### Glossas em múltiplos idiomas

As glossas EN são **traduzidas para PT/ES/FR** localmente via `deep-translator` (Google Translate gratuito), com cache idempotente. A API serve a glossa no idioma ativo do app:

```
GET /api/original/hebrew/0/0/0?lang=pt    → glossas em português
GET /api/original/greek/42/2/15?lang=es   → glossas em espanhol
```

Estrutura em disco:

```
data/glosses/
  en/he.json   en/grc.json   ← gerado pelo import_glosses.py
  pt/he.json   pt/grc.json   ← gerado pelo translate_glosses.py
  es/...       fr/...
  _cache/      ← {en→target} translation cache (resume-friendly)
```

Tradução automatizada é "boa o suficiente" pra estudo (qualidade Google Translate 1-3 palavras, ~95% acurácia em termos bíblicos comuns). Refinamento manual fica pra V2.

### Lemma → Strong's (grego) — `openscriptures/strongs`

MorphGNT não carrega número Strong's; apenas o lemma. Construímos o reverso a partir de `greek/strongs-greek-dictionary.js` do `openscriptures/strongs` (texto base 1890 = domínio público; embalagem JSON CC-BY-SA).

> **Decisão deliberada**: `eliranwong/OpenHebrewBible` (CC BY-NC) **não é usado** — bloqueia uso comercial. O `morphhb` cobre tudo o que precisamos e é mais permissivo.

### Atribuição exibida no app

Ao abrir o sheet "📜 Original":

- AT: `Texto: WLC (morphhb, CC BY 4.0) · Glossa: STEPBible TBESH (CC BY 4.0)`
- NT: `Texto: SBLGNT (CC BY 4.0) · Morf: MorphGNT (CC BY-SA 3.0) · Glossa: TBESG (CC BY 4.0)`

---

## Rodando localmente

### Pré-requisitos

- Python 3.11+ (`python3 --version`)
- Mac/Linux: terminal padrão. Windows: WSL.

### 1) Setup (uma vez só)

```bash
# do diretório raiz do repo
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[etl]'        # runtime + ETL deps

# 1. baixa as glossas Strong's em inglês (TBESH/TBESG, ~30 s)
.venv/bin/python scripts/import_glosses.py

# 2. (opcional) traduz as glossas EN→PT/ES/FR via Google Translate gratuito
#    (~12 min total, idempotente — pode rodar em background depois)
.venv/bin/pip install deep-translator
.venv/bin/python scripts/translate_glosses.py

# 3. baixa hebraico (morphhb) + grego (MorphGNT) e gera JSONs por livro (~2 min)
.venv/bin/python scripts/import_hebrew.py
.venv/bin/python scripts/import_greek.py
cd ..
```

Pronto. Os JSONs ficam em `backend/data/{hebrew,greek}/NN.json` (versionar opcional).

### 2) Subir o serviço — caminho recomendado

```bash
./scripts/dev.sh
```

O script:

- detecta o IP da sua rede local
- sobe **backend** em `0.0.0.0:8000` (FastAPI com `--reload`)
- sobe **frontend** em `0.0.0.0:8080` (estático)
- imprime um **QR code ASCII** no terminal apontando pro frontend
- aceita qualquer origem da LAN automaticamente (CORS dev mode)

Aponte a câmera do celular (mesma WiFi) → app abre direto.
Pelo Mac, acesse `http://localhost:8080`.

### 2-alt) Subir manualmente — dois terminais

**Terminal 1 — backend** (de dentro de `backend/`):

```bash
cd backend
.venv/bin/python run.py
```

> `run.py` é um wrapper que já liga uvicorn em `0.0.0.0:8000` por padrão.
> Se preferir o uvicorn direto: `.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` — **o `--host 0.0.0.0` é obrigatório** se você quer acessar do celular ou outro device da rede.

**Terminal 2 — frontend** (do diretório raiz):

```bash
python3 -m http.server -d frontend 8080
```

Acessar:

- **Mac**: `http://localhost:8080`
- **Celular** (mesma WiFi): descubra seu IP com `ipconfig getifaddr en0` e abra `http://<IP>:8080`

### Verificação rápida

```bash
# backend respondendo?
curl http://localhost:8000/healthz
# {"status":"ok"}

# Bíblia carrega?
curl http://localhost:8000/api/bible/versions

# Hebraico Gn 1:1?
curl http://localhost:8000/api/original/hebrew/0/0/0
```

Se algum desses falhar, pule pro Troubleshooting abaixo.

### Troubleshooting

| Erro no app | Causa provável | Solução |
|---|---|---|
| "Erro ao carregar versão. Verifique conexão / backend." | Backend não está rodando, ou só em `127.0.0.1`. | Confirme que rodou `python run.py` (não `uvicorn ... --port 8000` sem `--host`). Cheque `curl http://<seu-IP>:8000/healthz`. |
| Funciona em `localhost` mas não no celular | Backend em `127.0.0.1` only | Use `python run.py` (já em `0.0.0.0`) ou adicione `--host 0.0.0.0` ao `uvicorn`. |
| `Address already in use` | Porta 8000/8080 ocupada | `lsof -nP -iTCP:8000 -sTCP:LISTEN` → mate o processo, ou exporte `PORT=9000` antes de `python run.py`. |
| CORS error no console | `.env` com `ALLOWED_ORIGINS=` antigo restritivo | Apague `backend/.env` (modo dev libera LAN automaticamente quando vazio). |
| Página em branco no celular | DNS local não resolve | Use o IP cru (não `.local` se o nome não resolver). |

### Variáveis de ambiente (opcional)

Crie `backend/.env` apenas se quiser sobrescrever os defaults dev:

```ini
# Produção: liste explicitamente as origens permitidas
ALLOWED_ORIGINS=https://holyread.example.com,https://staging.holyread.example.com

# Ou use regex para padrões (ex: subdomínios)
ALLOWED_ORIGIN_REGEX=^https://.*\.example\.com$

# Rate limit (defaults: 120/min geral, 20/min busca)
RATE_LIMIT_DEFAULT=120/minute
RATE_LIMIT_SEARCH=20/minute

# Bind
HOST=0.0.0.0
PORT=8000
```

Em **dev**, deixe `.env` inexistente. O código já libera localhost + LANs privadas (`10.*`, `172.16-31.*`, `192.168.*`, `*.local`) em qualquer porta.

---

## QR code para celular na rede local

`scripts/dev.sh` imprime um QR ASCII no terminal apontando pra `http://<seu-IP-LAN>:8080`. Aponte a câmera do celular (mesma WiFi) — abre direto no Safari/Chrome móvel. O `frontend/config.js` detecta automaticamente o IP da LAN no `hostname` e configura `API_BASE` pro backend correto, sem mexer em variáveis.

Sem internet: nada disso usa Cloudflare/ngrok — a app fica 100% na sua rede local.

---

## Pipeline de ETL (originais)

```
                                ┌──────────────────────────┐
   morphhb wlc/*.xml  ─────────►│ scripts/import_hebrew.py │── data/hebrew/NN.json
   morphhb wlc/VerseMap.xml ───►│  · OSIS XML → palavras    │
                                │  · WLC→KJV remap          │
                                │  · transliteração SBL     │
                                └──────────────────────────┘
                                ┌──────────────────────────┐
   morphgnt 61-Mt..87-Re.txt ──►│ scripts/import_greek.py  │── data/greek/NN.json
                                │  · 7-col plain → JSON     │
                                │  · translit. Erasm/Mod    │
                                └──────────────────────────┘
```

Schema saída (Hebraico):

```jsonc
{
  "book": 0, "osis": "Gen",
  "chapters": [
    [
      {
        "text": "בראשית ברא ...",
        "words": [
          {
            "text": "בְּרֵאשִׁית",
            "translit": "bəreʾshiyt",
            "morphemes": [
              { "text": "בְּ", "lemma": "b",    "morph": "R"     },
              { "text": "רֵאשִׁית", "lemma": "7225", "morph": "Ncfsa" }
            ]
          }
        ]
      }
    ]
  ]
}
```

Schema saída (Grego):

```jsonc
{
  "book": 39, "osis": "Matt",
  "chapters": [
    [
      {
        "text": "Βίβλος γενέσεως ...",
        "words": [
          {
            "text": "Βίβλος", "lemma": "βίβλος", "morph": "N- ----NSF-",
            "translit_eras": "biblos", "translit_mod": "vivlos"
          }
        ]
      }
    ]
  ]
}
```

---

## Endpoints da API

| Método | Path | Resposta |
|---|---|---|
| GET | `/healthz` | `{"status":"ok"}` |
| GET | `/api/bible/versions` | lista de códigos |
| GET | `/api/bible/{version}` | Bíblia inteira (66 livros) |
| GET | `/api/bible/{version}/{book}/{chapter}` | versículos de um capítulo |
| GET | `/api/bible/{version}/search?q=…&limit=…` | full-text search (rate limit menor) |
| GET | `/api/original/hebrew/{book}/{chapter}/{verse}` | versículo hebraico + palavras |
| GET | `/api/original/greek/{book}/{chapter}/{verse}` | versículo grego + palavras |

`{book}`, `{chapter}`, `{verse}` são 0-indexed na ordem canônica (0 = Gênesis, 38 = Malaquias, 39 = Mateus, 65 = Apocalipse).

Documentação interativa em `/docs` (Swagger UI).

---

## Deploy

### Estado atual

| | URL | Origem |
|---|---|---|
| Frontend (V1) | https://wcristoni.github.io/HolyRead/ | GitHub Pages serve `index.html` na raiz, que faz redirect pra `frontend/` |
| Backend (V1) | https://holyread-production.up.railway.app | Railway, Dockerfile em `backend/` |

O `frontend/config.js` aponta automaticamente pro Railway em produção e pro `localhost:8000` em dev.

### A V1 não roda inteira no GitHub Pages

> **GitHub Pages só serve estático.** Nosso backend é Python/FastAPI — precisa de um host com runtime. Pages só cobre o **frontend**, e mesmo assim depende do backend estar publicado em outra plataforma com `API_BASE` apontando pra ele.

Resumo dos componentes:

| Componente | Onde rodar | Por quê |
|---|---|---|
| **Backend** (`backend/`) | Railway · Render · Fly.io · Heroku · qualquer Docker | precisa Python 3.11 + FastAPI |
| **Frontend** (`frontend/`) | GitHub Pages · Netlify · Cloudflare Pages · Render · Usevelty · qualquer CDN | só HTML/CSS/JS estático |

**Sequência obrigatória**: 1) deploy backend → 2) atualiza `frontend/config.js` com a URL do backend → 3) deploy frontend.

### Passo 1 — Backend no Railway

```bash
cd backend
railway login
railway init        # cria o serviço
railway up          # build via Dockerfile.  Railway gera URL pública
```

Variáveis de ambiente no painel do Railway:

| Variável | Valor |
|---|---|
| `ALLOWED_ORIGINS` | `https://wcristoni.github.io` (origem do Pages — sem path) |
| `RATE_LIMIT_DEFAULT` | `120/minute` (default) |
| `RATE_LIMIT_SEARCH` | `20/minute` (default) |

`railway.toml` já configura healthcheck em `/healthz`. O `Dockerfile` copia `backend/data/` (~95 MB de JSONs de Bíblias + Hebraico + Grego + glossas) pro container.

Após o deploy: anote a URL gerada (algo como `https://holyread-api-production.up.railway.app`).

### Passo 2 — Apontar o frontend pro backend

Edite `frontend/config.js`:

```js
window.HOLYREAD_CONFIG = {
  API_BASE: (() => {
    const { protocol, hostname } = window.location;
    if (hostname === 'localhost' || hostname === '127.0.0.1' || /^\d+\.\d+\.\d+\.\d+$/.test(hostname)) {
      return `${protocol}//${hostname}:8000`;
    }
    return 'https://holyread-api-production.up.railway.app';   // ← cole aqui
  })(),
};
```

A função detecta dev local automaticamente; em prod usa a URL do Railway.

### Passo 3 — Frontend onde quiser

#### GitHub Pages (já configurado, em uso hoje)

```bash
git add frontend/config.js
git commit -m "chore: aponta frontend pro backend Railway"
git push origin main
```

Como o Pages serve a **raiz** do repo e os arquivos do app estão em `frontend/`, mantemos um `index.html` mínimo na raiz que faz **meta-refresh** pra `./frontend/`. Resultado: o usuário acessa `https://wcristoni.github.io/HolyRead/` e é redirecionado transparentemente pra `https://wcristoni.github.io/HolyRead/frontend/`.

Se preferir URL limpo (sem `/frontend/`), em **Settings → Pages** mudar Source para `main /frontend` e deletar o `index.html` da raiz.

#### Render (estático)

`render.yaml`:
```yaml
services:
  - type: web
    name: holyread-front
    runtime: static
    buildCommand: "true"
    staticPublishPath: ./frontend
```

#### Usevelty / outro estático

Suba o conteúdo da pasta `frontend/` como site estático. Não esqueça do `config.js` apontando pro Railway.

### Por que o backend precisa estar no ar antes do frontend

Se o `frontend/` for publicado no Pages **antes** do backend estar respondendo na URL configurada, o app carrega mas mostra toast `"Erro ao carregar versão. Verifique conexão / backend."`. A sequência correta é: backend → testar `curl /healthz` → frontend.

---

## Estrutura de pastas

```
holypleiiiz-bible/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, rate limit, security headers
│   │   ├── config.py            # config via env
│   │   ├── limiter.py           # slowapi limiter compartilhado
│   │   ├── osis_codes.py        # códigos OSIS dos 66 livros
│   │   ├── routes/
│   │   │   ├── bible.py         # Bíblias + busca
│   │   │   └── original.py      # Hebraico + Grego
│   │   └── services/
│   │       └── data_loader.py   # leitura cacheada dos JSONs
│   ├── data/
│   │   ├── bible/*.json         # 7 traduções (V0)
│   │   ├── hebrew/NN.json       # gerado via ETL
│   │   └── greek/NN.json        # gerado via ETL
│   ├── scripts/
│   │   ├── import_hebrew.py     # ETL morphhb → JSON
│   │   ├── import_greek.py      # ETL MorphGNT → JSON
│   │   ├── translit_he.py       # transliteração hebraica
│   │   └── translit_grc.py      # transliteração grega (Erasm/Mod)
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── railway.toml
│   └── .env.example
├── frontend/
│   ├── index.html               # app
│   ├── config.js                # API_BASE configurável
│   └── assets/
│       └── api.js               # cliente HTTP
├── scripts/
│   └── dev.sh                   # back+front+QR LAN
└── README.md
```

---

## Roadmap

- [ ] Persistir progresso/notas no MongoDB (V2)
- [ ] Login (HolyPleiiiz SSO) e merge com app de quizz
- [ ] Audio Bible (mp3 hospedado em CDN)
- [ ] Service Worker / offline parcial
- [ ] **Tradução das glossas para PT/ES/FR** (V2 — atualmente glossas em inglês via TBESH/TBESG)
- [ ] Concordância: tap numa palavra → todas as ocorrências no AT/NT
- [ ] Modos de leitura (em ordem cronológica, plano de leitura)
