# BusBoard

Painel digital de rodoviária: cadastro de empresas, destinos, plataformas e
viagens, com operação em tempo real (partidas, chegadas e status) e um painel
de TV em tela cheia.

- **Backend:** FastAPI + SQLAlchemy + SQLite, com Alembic para o schema
- **Frontend:** React 19 + TypeScript + Vite

---

## Instalação do zero

### 1. Backend

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -r Requirements.txt
```

### 2. Configuração

```bash
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/macOS
```

Abra o `.env` e preencha o `SECRET_KEY` (o app não sobe sem ele):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

As demais chaves já vêm com padrão razoável. O que cada uma faz está
comentado no próprio `.env.example`.

### 3. Banco de dados

O schema é responsabilidade do Alembic. Num banco novo:

```bash
alembic upgrade head
```

O servidor confere as tabelas no boot e, se faltar alguma, diz o que rodar.

### 4. Primeiro administrador

A rota de criação de usuário só promove a `adm` quando já existe um admin
logado — numa instalação nova não existe nenhum, então use o script:

```bash
python criar_admin.py --email admin@busboard.com --nome "Seu Nome"
```

A senha é pedida no terminal. Para trocar a senha de uma conta que já existe
(ou promover alguém a admin):

```bash
python criar_admin.py --email admin@busboard.com --redefinir
```

### 5. Frontend

```bash
cd frontend
npm install
```

### 6. Subir

Dois terminais. Na raiz, o backend:

```bash
.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Em `frontend/`, o painel:

```bash
npm run dev
```

- Painel administrativo: http://localhost:5173
- Painel da TV: http://localhost:5173/painel

O Vite faz proxy de `/auth`, `/board`, `/trips`, `/companies`, `/destinations`
e `/platforms` para `http://localhost:8000` (veja `frontend/vite.config.ts`).

---

## Testes

```bash
pip install -r Requirements-dev.txt
.venv\Scripts\python.exe -m pytest
```

Os testes rodam num SQLite temporário e não encostam no `banco.db`.

No frontend:

```bash
cd frontend
npm run lint
npx tsc -b          # checagem de tipos
npm run build       # build de produção
```

---

## Como o sistema se comporta

### Reinício diário

As viagens da rodoviária se repetem todo dia. De madrugada (3h por padrão) todas
voltam para `AGENDADO` e a previsão de horário é apagada. O "dia" da
rodoviária começa na hora do reinício, não à meia-noite.

A tarefa roda dentro do processo do servidor e confere a cada minuto; se o
servidor estiver desligado na hora, o reinício acontece quando ele volta. Para
ajustar: `DAILY_RESET_HOUR` e `TZ_NAME` no `.env`. Dá para forçar pela mão pelo
botão "Reiniciar o dia" na aba Viagens.

### Trava de login

Cinco tentativas erradas em cinco minutos travam aquele par de IP + e-mail por
60 segundos (HTTP 429 com `Retry-After`). A tentativa que estoura o limite
ainda responde "credenciais inválidas"; a seguinte é barrada.

O contador fica **na memória do processo**: some quando o servidor reinicia e
não é compartilhado entre workers. Para uma rodoviária com um servidor só,
basta. Se um dia rodar com várias instâncias, o lugar certo é o banco ou o Redis.

### Papéis

- **operador** — mexe nas viagens e no painel de operação
- **adm** — tudo, mais empresas, destinos, plataformas e usuários

---

## Estrutura

```
main.py            configuração, CORS, lifespan, rotas
models.py          models do SQLAlchemy
schemas.py         schemas de entrada e saída
rate_limit.py      trava de tentativas de login
daily_reset.py     reinício diário da grade
criar_admin.py     script de linha de comando para o primeiro admin
dependecies.py     sessão do banco e dependências de autenticação
conftest.py        fixtures e banco temporário dos testes
routes/            auth, companies, destinations, platforms, trips, board
alembic/           migrations do schema
tests/             suíte de testes
frontend/src/      painel (App.tsx) e painel da TV (PublicBoard.tsx)
frontend/src/admin/  uma aba do painel por componente
```

## Observações de produção

- `CORS_ORIGINS` precisa do domínio real do painel.
- `SECRET_KEY` fora do git, obviously — e trocar a senha do admin se ele já
  tiver estado em algum lugar.
- SQLite aguenta bem o volume de uma rodoviária. Se crescer para vários
  servidores, o caminho é trocar a URL em `DATABASE_URL` e mover o rate limit
  para um store compartilhado.
