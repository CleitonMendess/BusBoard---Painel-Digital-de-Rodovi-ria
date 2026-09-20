# Plano de estudo e execução do projeto BusBoard

Objetivo: entregar um MVP funcional em 30 dias sem ficar preso em estudo eterno.

Regra principal:
- aprender só o necessário para a tarefa do dia
- construir em blocos pequenos
- testar o que foi feito antes de avançar
- não começar por coisas de produção avançada

---

## 1. Estratégia geral

Você já tem boa base em:
- Python básico
- JavaScript
- Git
- FastAPI já começou a estudar

Então o caminho mais eficiente é:
1. Revisar only the essentials do que falta
2. Construir backend primeiro
3. Depois frontend
4. Depois painel público e real-time
5. Só no fim deploy e ajustes

A ideia é evitar o erro de ficar estudando meses sem tocar no projeto.

---

## 2. Ordem correta de aprendizado

### Bloco A — backend base
- FastAPI
- SQLAlchemy
- PostgreSQL básico
- JWT
- permissões por role

### Bloco B — frontend base
- HTML/CSS básico
- React + TypeScript
- consumo de API
- uso de token

### Bloco C — parte do sistema
- painel admin
- painel público
- WebSocket
- reconexão automática
- refresh de segurança

### Bloco D — produção
- environment variables
- deploy em VPS
- systemd
- ajustes finais

---

## 3. Material de apoio focado no assunto

### FastAPI
- Documentação oficial do FastAPI
- aulas focadas em: "FastAPI tutorial CRUD", "FastAPI JWT auth", "FastAPI SQLAlchemy PostgreSQL"
- estudo mínimo por dia: 30 a 60 minutos

### SQL / PostgreSQL
- aprender: SELECT, INSERT, UPDATE, DELETE, JOIN, relacionamento entre tabelas
- foco em: companies, destinations, platforms, trips, users

### React + TypeScript
- estudar: componentes, props, state, useEffect, useState, fetch/axios, localStorage
- foco em admin login e listagem

### HTML/CSS
- estudar: layout, flexbox, grid, cards, tabela, botão, form
- não precisa ser avançado, só o suficiente para montar páginas funcionais

### Git
- revisar commit, branch, pull, push
- usar sempre em pequenas etapas

---

## 4. Plano de 30 dias

## Dia 1 — FastAPI: ambiente e primeiro login
Objetivo:
- criar projeto FastAPI base
- configurar venv
- instalar dependências
- criar endpoint hello world
- estudar uma aula de FastAPI + login JWT

Entrega do dia:
- projeto rodando localmente
- endpoint /health
- endpoint /login com retorno simples de token (mockado ou primeira versão)

Material recomendado:
- documentação oficial do FastAPI
- vídeo de "FastAPI login JWT tutorial"

---

## Dia 2 — criar autenticação real com JWT
Objetivo:
- entender JWT
- criar usuários em memória
- validar login
- autenticar rotas protegidas

Entrega:
- POST /api/v1/auth/login
- rota protegida que retorna usuário autenticado
- estrutura de autenticação pronta

Tarefa principal:
- testar login com usuário admin

---

## Dia 3 — modelagem do banco e PostgreSQL
Objetivo:
- entender PostgreSQL
- criar banco local
- aprender SQLAlchemy no mínimo necessário

Entrega:
- banco PostgreSQL rodando localmente
- conexão com FastAPI
- tabela users pronta

Tarefa principal:
- inserir 1 usuário admin manualmente no banco

---

## Dia 4 — criar modelo de usuários e hash de senha
Objetivo:
- entender password hashing
- criar modelo User com senha criptografada
- revisar login real usando banco

Entrega:
- login autenticando usuário real do banco
- senha salva em hash

---

## Dia 5 — CRUD de empresas
Objetivo:
- criar tabela companies
- criar endpoints de listagem, criação, edição e remoção

Entrega:
- rotas de empresas funcionando
- endpoint GET/POST/PUT/DELETE

---

## Dia 6 — CRUD de destinos e plataformas
Objetivo:
- repetir o padrão para destinos e plataformas
- entender que o projeto tem entidades relacionadas

Entrega:
- endpoints de destinos e plataformas funcionando

---

## Dia 7 — CRUD de viagens (parte 1)
Objetivo:
- criar tabela trips
- entender campos fundamentais
- criar rotas básicas

Entrega:
- cadastro de viagens simples
- endpoints de listagem e criação

---

## Dia 8 — CRUD de viagens (parte 2)
Objetivo:
- finaliza edição, visualização e filtros
- testar status e horários

Entrega:
- viagens editáveis
- filtro por tipo (saída/chegada)

---

## Dia 9 — permissions por role
Objetivo:
- entender diferença entre admin e operador
- preparar rota restrita para mudança de horário

Entrega:
- admin consegue tudo
- operador só mexe no horário da viagem

---

## Dia 10 — revisar backend e limpar erros
Objetivo:
- testar endpoints principais
- corrigir bugs de validação
- garantir autenticação correta

Entrega:
- backend funcional e consistente
- endpoints principais testados com Postman ou curl

---

## Dia 11 — HTML/CSS: montar base visual do admin
Objetivo:
- revisar HTML/CSS básico
- criar layout simples para login e dashboard

Entrega:
- página de login visualmente funcional
- layout do dashboard inicial

---

## Dia 12 — React + Vite: ambiente inicial
Objetivo:
- criar app React + TypeScript
- entender estrutura básica
- rodar a primeira tela

Entrega:
- app React rodando localmente

---

## Dia 13 — React + TypeScript: login no frontend
Objetivo:
- consumir endpoint /login
- salvar token e redirecionar
- entender estado e localStorage

Entrega:
- login funcionando no frontend

---

## Dia 14 — dashboard admin base
Objetivo:
- montar layout de dashboard
- estruturar navegação

Entrega:
- tela inicial do admin com menu e área principal

---

## Dia 15 — frontend de empresas
Objetivo:
- listar empresas
- criar e editar empresa

Entrega:
- CRUD de empresas no frontend

---

## Dia 16 — frontend de destinos e plataformas
Objetivo:
- repetir padrão de CRUD

Entrega:
- telas funcionando para destinos e plataformas

---

## Dia 17 — frontend de viagens
Objetivo:
- listar viagens
- criar e editar viagem
- mostrar status

Entrega:
- painel admin com gestão de viagens

---

## Dia 18 — SQL básico para revisão prática
Objetivo:
- reforçar SELECT, JOIN, filtros, agrupamentos
- facilitar manutenção do banco e consultas

Entrega:
- queries de exemplo montadas
- entendimento de como consultar viagens e status

---

## Dia 19 — painel público base
Objetivo:
- criar layout de painel público
- mostrar relógio
- listar saídas e chegadas

Entrega:
- tela pública simples com tabela de viagens

---

## Dia 20 — painel público com dados reais
Objetivo:
- integrar frontend público com API
- mostrar dados do banco na tela
- formatar horários e status

Entrega:
- painel público funcionando com dados do backend

---

## Dia 21 — WebSocket no backend
Objetivo:
- entender WebSocket em FastAPI
- criar endpoint /ws/board
- mandar updates para o cliente

Entrega:
- WebSocket básico funcionando

---

## Dia 22 — WebSocket no frontend
Objetivo:
- conectar client-side ao WebSocket
- atualizar tela em tempo real
- tratar erros de conexão

Entrega:
- painel público atualiza sem dar refresh manual

---

## Dia 23 — reconexão automática e refresh de segurança
Objetivo:
- implementar lógica de reconexão
- definir política do refresh de página a cada 15 minutos

Entrega:
- painel continua funcionando mesmo sem conexão estável

---

## Dia 24 — destaque da próxima saída e avisos
Objetivo:
- destacar próxima viagem
- formatar visualmente horários importantes
- adicionar aviso de atraso/embarque

Entrega:
- painel mais parecido ao projeto final

---

## Dia 25 — limpar fluxo admin e operador
Objetivo:
- garantir que operador só altera horário
- revisar permissões por endpoint
- limpar inconsistências

Entrega:
- regras de acesso funcionando corretamente

---

## Dia 26 — ambiente de produção local
Objetivo:
- configurar variáveis de ambiente
- preparar .env
- rodar backend e frontend de forma mais realista

Entrega:
- ambiente previsível e configurável

---

## Dia 27 — deploy em VPS / Linux
Objetivo:
- estudar nginx ou reverse proxy
- entender systemd
- preparar processo de startup

Entrega:
- projeto disponível em servidor sem cair ao reiniciar

---

## Dia 28 — testes e correções finais
Objetivo:
- testar login
- testar CRUD
- testar painel público
- corrigir o que quebrar

Entrega:
- sistema estável em fluxo básico

---

## Dia 29 — polish e documentação
Objetivo:
- revisar UX
- ajustar telas com mais clareza
- documentar endpoints e uso do sistema

Entrega:
- sistema com aparência mais madura
- documentação simples do projeto

---

## Dia 30 — demo final e entrega
Objetivo:
- testar tudo em conjunto
- gravar demo
- preparar apresentação

Entrega:
- MVP funcionando
- apresentação pronta
- próximo passo definido

---

## 5. O que fazer quando você travar

Quando aparecer dúvida, siga esta ordem:
1. Tente resolver sozinho por 20 minutos
2. ler a documentação oficial do tema
3. assistir 1 vídeo focado
4. aplicar a solução no projeto imediatamente
5. depois seguir em frente

Não pare a construção por uma dúvida pequena. Isso é o caminho mais rápido.

---

## 6. Regra de ouro para não perder tempo

Você não precisa dominar tudo antes de entregar.

Tenha este mindset:
- entregar é prioridade
- aprender no caminho
- melhorar depois da primeira versão funcional

---

## 7. Checklist mínimo para MVP

Antes de considerar o projeto entregue, você precisa ter:
- [ ] login funcionando
- [ ] admin autenticado
- [ ] CRUD de viagens
- [ ] CRUD de empresas/destinos/plataformas
- [ ] operador restrito a mudança de horário
- [ ] painel público mostrando saídas e chegadas
- [ ] WebSocket atualizando em tempo real
- [ ] deploy funcionando localmente ou em VPS

Se isso estiver funcionando, você já tem um MVP real.

---

## 8. Sugestão final de execução

Se quiser manter foco e não se perder:
- 1 tarefa por dia
- 1 entrega por dia
- 1 estudo curto por dia
- prioridade para o que entrega valor real ao projeto

Esse é o melhor caminho para você terminar sem entrar em ciclo de estudo infinito.


## 2. Frontend: o que falta é o peso maior do projeto

- Backend do MVP está em ~50-60%.
- Frontend está em 0% e é ~60% do esforço restante.
- Foco do frontend: **primeiro o painel público** (o que o sogro vê na TV),
  depois o admin.

### Ordem de aprendizado sugerida

1. **HTML/CSS** — Gustavo Guanabara, "Curso em Vídeo" (HTML5 e CSS3, módulo 1)
   - base antes de React, não pular.
2. **React + TypeScript** — duas opções:
   - Matheus Battisti ("Hora de Codar"): curso completo de React gratuito no
     YouTube, em português, com projetos práticos (login, CRUDs).
   - Hashtag Treinamentos: mesmo canal do curso de FastAPI; verificar se têm
     playlist de React. É a didática já conhecida.
3. **Aplicar direto no BusBoard** — login no React, depois o painel.

### Dica que conecta ao projeto

Assim como o curso de FastAPI usa pizzaria, procurar um curso de React que
construa CRUD com login e trocar pizzaria por ônibus.

### Quando mexer em quê (no BusBoard)

- Dia 11/12 do plano: HTML/CSS + React + Vite + tela de login
- Dia 20: painel público precisa dos endpoints `/board/departures` e
  `/board/arrivals` — criar antes ou junto
- Depois: WebSocket (Dia 21-23 do plano)

---

## 3. Resumo: próximo passo concreto

1. Decidir a role (`commom` -> `operador` ou nova role)
2. Implementar `PATCH /trips/{id}/horario` com autorização `{adm, operador}`
3. Testar os 3 cenários da tabela acima
4. Aí sim: HTML/CSS -> React -> login no front