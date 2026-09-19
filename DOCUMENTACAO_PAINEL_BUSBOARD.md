# Documentação da arquitetura do BusBoard

## 1. Visão geral do projeto

O BusBoard é um painel digital de rodoviária com foco em monitoramento operacional de viagens. A lógica principal não é de e-commerce nem de pedidos. O sistema deve mostrar:

- ônibus/viagens em andamento
- horários programados
- status da viagem
- plataforma de embarque
- destino e empresa
- atualização de status em tempo real

O modelo ideal é parecido com um painel de aeroporto, onde a informação principal é o estado atual da viagem.

---

## 2. O que o projeto já está fazendo certo

O código atual já tem alguns elementos importantes para esse tipo de aplicação:

- [models.py](models.py): possui modelos de `User`, `Company`, `Destination`, `Platform` e `Trip`
- [schemas.py](schemas.py): já separa schemas para entrada e resposta
- [routes/trips.py](routes/trips.py): já define rotas de criação e atualização de viagens
- [routes/auth.py](routes/auth.py): já tem autenticação via JWT

Esses pontos são bons para um painel de rodoviária, porque a estrutura do domínio já faz sentido:

- `Company` = empresa/operadora
- `Destination` = destino
- `Platform` = plataforma/terminal
- `Trip` = viagem
- `User` = administrador do painel

---

## 3. O que está errado ou incompleto

### 3.1 O domínio ainda está genérico demais

O projeto ainda parece um CRUD abstrato, e não um painel operacional real. O foco ainda está muito em "cadastro básico" e pouco em "monitoramento da operação".

Exemplo:
- há rota de criar viagem
- há rota de atualizar status
- mas ainda faltam recursos muito comuns de painel:
  - histórico de eventos da viagem
  - painel público de exibição
  - exibição por plataforma
  - filtro por empresa/destino
  - busca por status
  - atualização em tempo real

### 3.2 Status da viagem precisa ter papel central

No seu projeto, o status da viagem é o coração do sistema. Ele deve ser bem definido e padronizado.

Status ideal:

- AGENDADO
- NO HORARIO
- EMBARQUE
- ATRASADO
- SAIU
- CHEGOU
- CANCELADO

Essa parte já existe em [models.py](models.py), o que está certo. O que falta é deixar esse fluxo mais robusto e claro.

### 3.3 A arquitetura atual ainda não representa bem "painel digital"

Para um painel digital, o backend precisa pensar em dois tipos de uso:

1. Painel administrativo
   - criar viagens
   - alterar status
   - cadastrar empresas, plataformas e destinos
   - gerenciar usuários

2. Painel público / monitoramento
   - listar viagens por horário
   - mostrar status atual
   - mostrar plataforma e destino
   - filtrar por terminal ou empresa

O código atual tem o primeiro tipo, mas ainda está fraco no segundo.

### 3.4 Faltam entidades extras para refletir o cenário real

Para ficar mais próximo do funcionamento real de uma rodoviária, o ideal seria ter entidades como:

- `Route` ou `Trip` (viagem)
- `StatusLog` (histórico de alterações do estado da viagem)
- `TerminalPanel` ou `Display` (painel de exibição)
- `ArrivalBoard` (painel de chegada)
- `DepartureBoard` ou `Board` (painel de saída)

Esses itens tornam a aplicação mais realista e ajudam a representar o que aparece no monitor.

---

## 4. Estrutura correta do projeto

A arquitetura correta para o BusBoard deve seguir esta lógica:

### 4.1 Dominio principal

- Usuário
- Empresa
- Destino
- Plataforma
- Viagem
- Status da viagem
- Histórico de status

### 4.2 Fluxo principal

1. Administrador cadastra a empresa
2. Administrador cadastra destino
3. Administrador cadastra plataforma
4. Administrador cadastra viagem
5. Sistema define status inicial como `AGENDADO`
6. Admin atualiza status conforme a operação avança
7. Painel público lê os dados e mostra em tela

---

## 5. Estrutura ideal de rotas

### Autenticação

- `POST /auth/login`
- `POST /auth/login-form`
- `POST /auth/creat_user`
- `PATCH /auth/users/{user_id}/role`

### Empresas

- `POST /companies`
- `GET /companies`
- `PATCH /companies/{id}`

### Destinos

- `POST /destinations`
- `GET /destinations`
- `PATCH /destinations/{id}`

### Plataformas

- `POST /platforms`
- `GET /platforms`
- `PATCH /platforms/{id}`

### Viagens

- `POST /trips/creat_trips`
- `GET /trips/list`
- `GET /trips/{id}`
- `PATCH /trips/{id}/status`

### Painel externo

- `GET /board/departures`
- `GET /board/arrivals`
- `GET /board/active`

---

## 6. Modelo de dados recomendado

### User

- id
- name
- email
- password_hash
- role
- active

### Company

- id
- name
- active

### Destination

- id
- city
- state
- active

### Platform

- id
- number
- active

### Trip

- id
- type
- scheduled_time
- estimated_time
- status
- company_id
- destination_id
- platform_id
- created_at
- updated_at

### StatusLog

- id
- trip_id
- old_status
- new_status
- changed_at
- changed_by

---

## 7. Como o endpoint de status deve funcionar

O endpoint principal do painel deve ser parecido com isto:

```http
PATCH /trips/{id}/status
```

Payload:

```json
{
  "status": "EMBARQUE"
}
```

Resposta:

```json
{
  "mensagem": "Status da viagem atualizado com sucesso",
  "trip_id": 12,
  "status_atual": "EMBARQUE"
}
```

Esse endpoint é o equivalente ao "atualizar item do pedido" do vídeo, mas no contexto do painel de ônibus.

---

## 8. Conclusão

### Resposta honesta

Não está "muito errado", mas também não está totalmente alinhado com um painel de rodoviária operacional. Ele está em uma etapa de estrutura básica, e precisa evoluir para refletir a realidade do negócio.

### O que está certo:

- autenticação
- cadastro de entidades
- viagem com status
- rota de atualização

### O que precisa melhorar:

- painel de monitoramento público
- histórico de eventos
- filtro e listagem por status
- clareza do fluxo operacional
- modelagem mais realista de um painel digital de rodoviária

---

## 9. Recomendação final

O melhor caminho é continuar usando a base atual, mas transformar o foco de "CRUD geral" para "operacional dashboard". Em outras palavras:

- o projeto não precisa virar pizzaria
- ele precisa virar um painel de rodoviária funcional e visualmente ligado ao aeroporto/terminal

A base atual já lhe dá a fundação correta; agora o próximo passo é estruturar a parte de monitoramento e atualização de status como centro do sistema.
