# 🚌 BusBoard -` Painel Digital de Rodoviária

> Projeto **para produção real**: painel de chegadas/saídas de ônibus, estilo aeroporto,
> para uma rodoviária de capital (cliente real, sogro do desenvolvedor).
> Prioridade: confiabilidade e simplicidade de manutenção acima de sofisticação técnica.

---

## 1. Contexto e restrições

- Ambiente real, sem monitoramento técnico constante — precisa "rodar sozinho".
- Internet disponível no local (confirmado).
- Prazo: entrega em semanas.
- Vai ter mais de um tipo de usuário administrando o sistema.
- TV pública ficará em uma Smart TV com navegador (plano B: mini-PC/Fire TV Stick se o
  navegador da TV não sustentar WebSocket por longos períodos).

---

## 2. Visão do produto

### 2.1 Painel público (o que os passageiros veem)

```
┌────────────────────────────────────────────────────────────────────┐
│  🚌 RODOVIÁRIA CENTRAL                         27 AGO  16:42:18    │
├────────────────────────────────────────────────────────────────────┤
│                         SAÍDAS                                     │
│  HORÁRIO   DESTINO           EMPRESA          PLAT.   STATUS       │
│  16:50     Brasília          Real Expresso      03    EMBARQUE     │
│  17:10     Goiânia           Catedral           07    NO HORÁRIO   │
│  17:45     Belo Horizonte    Gontijo            05    ATRASADO     │
├────────────────────────────────────────────────────────────────────┤
│                         CHEGADAS                                   │
│  HORÁRIO   ORIGEM            EMPRESA          PLAT.   STATUS       │
│  16:55     Goiânia           Catedral           07    A CAMINHO    │
├────────────────────────────────────────────────────────────────────┤
│  ⚠️ ATENÇÃO: Embarque para Brasília será encerrado às 16:45        │
└────────────────────────────────────────────────────────────────────┘
```

Requisitos funcionais:
- Atualização em tempo real (WebSocket), sem F5.
- **Reconexão automática** se o WebSocket cair.
- **Refresh de segurança**: recarregar a página inteira a cada ~15 min caso fique sem
  receber updates — evita painel "travado" sem ninguém por perto para intervir.
- Destaque automático da próxima saída.
- Aviso de atraso com nova previsão de horário.
- Modo fullscreen / kiosk.

### 2.2 Painel administrativo (`/admin`)

Dois níveis de acesso:

| Papel        | Pode fazer |
|--------------|------------|
| **Admin**    | CRUD completo: empresas, destinos, plataformas, viagens; altera status; cria/gerencia usuários operadores |
| **Operador** | **Apenas** altera data/horário de uma viagem já existente. Não cria viagem, não mexe em empresa/destino/plataforma, não gerencia usuários |

A restrição do operador é garantida **por design de rota** (endpoint específico que só
aceita horário), não apenas por validação — assim fica impossível ele alterar outra coisa
mesmo em caso de bug de validação.

---

## 3. Stack técnica

| Camada         | Escolha                          | Motivo |
|----------------|-----------------------------------|--------|
| Backend        | FastAPI + Python                  | Async nativo, bom para WebSocket, curva de aprendizado ok para o nível atual |
| Banco de dados | **PostgreSQL**                    | Padrão de produção, disponível pronto em qualquer VPS, evita migração dolorosa depois |
| ORM            | SQLAlchemy + Alembic              | Migrations versionadas |
| Autenticação   | JWT com campo `role` no payload   | Simples, sem precisar de sessão em memória |
| Frontend       | React + TypeScript + Vite         | Painel público e admin |
| Real-time      | WebSocket nativo (FastAPI)        | Redis fica **fora do MVP** — menos peças para manter no ar |
| Hospedagem     | VPS (DigitalOcean ou Hetzner)     | Mais simples e barato que AWS para este porte; ainda dá prática de Linux (alinhado ao roadmap Cloud/DevOps) |
| Processo       | systemd (auto-restart)            | Sistema reinicia sozinho se travar ou se o servidor reiniciar |

> Docker, CI/CD e migração para AWS/Terraform ficam para uma **Fase 2**, depois que o
> sistema estiver estável em produção. Não bloqueiam a entrega urgente.

---

## 4. Modelo de dados

```
companies        destinations       platforms
├── id           ├── id             ├── id
├── name         ├── name           ├── number
├── active       ├── state          └── active
└── created_at   ├── active
                 └── created_at

trips                          users
├── id                         ├── id
├── type (saída/chegada)       ├── name
├── scheduled_time             ├── username
├── estimated_time             ├── password_hash
├── company_id (FK)            └── role (admin | operador)
├── destination_id (FK)
├── platform_id (FK)
├── status                     announcements
├── created_at                 ├── id
└── updated_at                 ├── message
                                ├── active
status ∈ {AGENDADO, NO_HORARIO, EMBARQUE,          ├── start_at
           ATRASADO, CANCELADO, SAIU, CHEGOU}       └── end_at
```

---

## 5. API (rascunho de endpoints)

```
GET    /api/v1/trips
GET    /api/v1/trips/departures
GET    /api/v1/trips/arrivals
POST   /api/v1/trips                 [admin]
PUT    /api/v1/trips/{id}            [admin]
PATCH  /api/v1/trips/{id}/horario    [admin, operador]   ← rota restrita
DELETE /api/v1/trips/{id}            [admin]

GET/POST/PUT/DELETE /api/v1/companies      [admin]
GET/POST/PUT/DELETE /api/v1/destinations   [admin]
GET/POST/PUT/DELETE /api/v1/platforms      [admin]
GET/POST/PUT/DELETE /api/v1/users          [admin]

POST   /api/v1/auth/login            → retorna JWT (id + role)

WS     /ws/board                     → push de atualizações para o painel público
```

---

## 6. Roadmap de entrega

### Fase 1 — MVP funcional (prazo: semanas)
- [ ] Backend FastAPI + PostgreSQL + Alembic
- [ ] Modelos: companies, destinations, platforms, trips, users, announcements
- [ ] Autenticação JWT com `role`
- [ ] CRUD completo (admin) de viagens/empresas/destinos/plataformas
- [ ] Rota restrita `PATCH /trips/{id}/horario` (admin + operador)
- [ ] Tela admin: login, dashboard, CRUDs, criação de operadores
- [ ] Painel público: chegadas, saídas, relógio, destaque da próxima saída
- [ ] WebSocket com reconexão automática + refresh de segurança periódico
- [ ] Deploy em VPS com systemd (auto-restart)

### Fase 2 — Consolidação (depois de estável em produção)
- [ ] Dockerizar (backend, frontend, nginx, postgres)
- [ ] GitHub Actions (testes, lint, build)
- [ ] Backups automáticos do banco
- [ ] Avaliar migração para AWS/Terraform, se fizer sentido

---

## 7. Riscos e decisões em aberto

- **Navegador da Smart TV** pode não sustentar WebSocket por longas horas — testar cedo;
  plano B é mini-PC ou Fire TV Stick/Chromecast com Google TV.
- Definir provedor de VPS específico (DigitalOcean vs Hetzner) na hora do deploy.
- Definir política de senha/recuperação de acesso para os operadores.
