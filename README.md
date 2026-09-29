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

### 5. Convites (dar acesso a outras pessoas)

A tela de login é só para entrar. Criar conta é por convite, então saber o
endereço do painel não basta para virar usuário: é preciso o código que o
administrador manda.

1. Logado como `adm`, abra **Convites** no menu lateral.
2. Escolha a função (operador ou administrador) e a validade, e clique em
   **Gerar convite**.
3. Copie o link e envie para a pessoa. O link fica
   `http://<servidor>/cadastro/<código>`, e quem abrir preenche nome, e-mail e
   senha, já entrando no sistema.

O código aparece **uma vez só** e é de uso único. O banco guarda apenas o hash
do código, então um dump do banco não serve para criar conta com convite
pendente. Para tirar o convite do ar antes de ser usado, é só cancelar na
mesma aba.

`INVITE_VALIDADE_HORAS` no `.env` muda a validade padrão (72 h).

### 6. Frontend

```bash
cd frontend
npm install
```

### 7. Subir

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

### Logs

O app escreve no console e em `backend.log`, com rotação (2 MB por arquivo,
3 arquivos antigos). Ajustes no `.env`:

- `LOG_LEVEL` — `DEBUG`, `INFO` (padrão), `WARNING`, `ERROR` ou `CRITICAL`
- `LOG_FILE` — caminho do arquivo; deixe **vazio** para logar só no console

Erro não tratado vira resposta 500 com mensagem genérica, e o traceback
completo (com método e rota) vai para o log — o cliente não vê nada de
interno. Os logs de acesso do uvicorn também caem no arquivo.

### Backup do banco

O banco é um arquivo SQLite só, e a rodoviária perde o dia se ele sumir. O
`backup.py` usa o `backup()` do próprio SQLite, que copia de forma
consistente mesmo com o servidor escrevendo ao mesmo tempo.

**Automático:** um backup por dia, logo depois do reinício da grade (o retrato
do dia anterior fechando). Vai para `backups/`, e os 14 mais novos são
mantidos — o resto é apagado sozinho.

**Na mão, para agendar:**

```bash
python backup.py                  # um backup agora
python backup.py --manter 30      # e guarda os últimos 30
```

No Windows, use o Agendador de Tarefas; no Linux, o cron:

```cron
0 */2 * * *  cd /caminho/busboard && .venv/bin/python backup.py
```

Ajustes: `BACKUP_PASTA` e `BACKUP_MANTER` no `.env`. A pasta `backups/` não vai
para o git.

Para restaurar, é só parar o servidor e copiar o arquivo por cima do `banco.db`
(mais o `alembic_version` que vem junto, então o schema volta junto).

## Produção

### Um processo só, uma porta só

O backend também entrega o painel. Se `frontend/dist` existir, o FastAPI serve
o front inteiro: `/` é o painel, `/painel` é a TV da rodoviária e `/assets` são
os arquivos com hash. Sem nginx, sem dois serviços, sem CORS chateando.

```bash
cd frontend && npm run build     # uma vez a cada mudança no front
cd .. && .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Se o `dist` não existir, a API sobe normal e o log avisa que o painel não vai
abrir (é o caso do desenvolvimento, em que o Vite serve o front na 5173 e faz
proxy da API). O caminho pode ser mudado com `FRONTEND_DIST=/var/www/panel`.

Conferência de saúde para o supervisor, sem senha (só diz se está de pé):

```bash
curl http://localhost:8000/health     # {"status":"ok"}
```

Cache: `/assets` tem hash no nome, então vai com `immutable` de um ano; o
`index.html` vai com `no-cache`, senão um deploy novo continua servindo o index
antigo e o navegador nunca vê a versão nova.

### Reinicie depois de atualizar

Com `uvicorn --reload` em produção você perde o banco SQLite aberto e o
reinício diário some junto. Melhor:

```ini
# /etc/systemd/system/busboard.service
[Unit]
Description=BusBoard
After=network.target

[Service]
Type=simple
User=busboard
WorkingDirectory=/opt/busboard
EnvironmentFile=/opt/busboard/.env
ExecStart=/opt/busboard/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable --now busboard
```

Como usar systemd gerenciando a aplicação (e não a nossa vida):

```bash
sudo apt install nginx
sudo tee /etc/nginx/sites-available/busboard > /dev/null <<'CONF'
server {
    listen 80;
    server_name painel.exemplo.com.br;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
CONF
sudo ln -s /etc/nginx/sites-available/busboard /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Com nginx na frente, ponha o domínio real em `CORS_ORIGINS` no `.env`.

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
- **adm** — tudo, mais empresas, destinos, plataformas, usuários e convites

Quem cria conta nova é sempre o `adm`, por convite. Sem ADM logado, a rota de
criação de usuário só aceita `operador`, e o cadastro público só existe com um
convite válido.

---

## Estrutura

```
main.py            configuração, CORS, logging, lifespan, rotas
models.py          models do SQLAlchemy
schemas.py         schemas de entrada e saída
rate_limit.py      trava de tentativas de login
daily_reset.py     reinício diário da grade
backup.py          backup consistente do SQLite
senhas.py           hash e verificação de senha (bcrypt direto)
criar_admin.py     script de linha de comando para o primeiro admin
dependecies.py     sessão do banco e dependências de autenticação
conftest.py        fixtures e banco temporário dos testes
routes/invites.py  convites de cadastro (criar, checar, usar, cancelar)
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
- **Um worker só** (`uvicorn main:app`): o rate limit em memória e o reinício
  diário em processo funcionam bem assim. Com vários workers (`gunicorn -w 4`)
  os dois precisam de store compartilhado, senão o limite de login dilui e o
  reinício pode disparar em paralelo.
- Ainda não há Dockerfile; o caminho pronto é o systemd acima.
- As senhas usam `bcrypt` direto, custo 12, em `senhas.py`. O `passlib` saiu:
  ele não é mantido e não conseguia ler a versão do `bcrypt` 4.x. O formato do
  hash é o mesmo, então quem já tinha conta continua entrando sem trocar a
  senha. Antes de 72 bytes, a senha é passada por SHA-256 para o bcrypt não
  ignorar o resto em silêncio.
