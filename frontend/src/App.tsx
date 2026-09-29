import { useEffect, useMemo, useState } from 'react'
import {
  api,
  logout,
  getRole,
  saveSession,
  type Trip,
  type AppUser,
  type Company,
  type Destination,
  type Platform,
} from './api'
import {
  normalizeTrip,
  parseTime,
  readError,
  statusClassMap,
  type AdminTab,
  type Notification,
  type TripStatus,
  type View,
} from './comuns'
import AbaUsuarios from './admin/AbaUsuarios'
import AbaConvites from './admin/AbaConvites'
import AbaEmpresas from './admin/AbaEmpresas'
import AbaDestinos from './admin/AbaDestinos'
import AbaPlataformas from './admin/AbaPlataformas'
import AbaViagens from './admin/AbaViagens'
import './App.css'
import OperatorPanel from './OperatorPanel'

function App() {
  const [currentTime, setCurrentTime] = useState(new Date())
  const [view, setView] = useState<View>('login')
  const [adminTab, setAdminTab] = useState<AdminTab>('overview')
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [role, setRole] = useState<string | null>(getRole())
  const isOperator = isAuthenticated && role !== 'adm'
  const [notification, setNotification] = useState<Notification | null>(null)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState('')

  const [trips, setTrips] = useState<Trip[]>([])
  const [companies, setCompanies] = useState<Company[]>([])
  const [users, setUsers] = useState<AppUser[]>([])
  const [destinations, setDestinations] = useState<Destination[]>([])
  const [platforms, setPlatforms] = useState<Platform[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const showNotification = (kind: Notification['kind'], message: string) => {
    setNotification({ kind, message })
    window.setTimeout(() => setNotification(null), 3500)
  }

  const navigate = (nextView: View) => {
    setView(nextView)
    if (nextView === 'public') {
      setAdminTab('overview')
    }
    if (nextView === 'login') {
      setAdminTab('overview')
    }
    if (nextView === 'users') setAdminTab('users')
    if (nextView === 'companies') setAdminTab('companies')
    if (nextView === 'destinations') setAdminTab('destinations')
    if (nextView === 'platforms') setAdminTab('platforms')
    if (nextView === 'trips') setAdminTab('trips')
    if (nextView === 'operation') setAdminTab('operation')
  }

  const refreshAllAdminData = async () => {
    setLoading(true)
    await fetchAdminData()
  }

  useEffect(() => {
    const timer = window.setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => window.clearInterval(timer)
  }, [])

  async function fetchPublicData() {
    try {
      setError(null)
      const [depRes, arrRes] = await Promise.all([
        api.board.departures(),
        api.board.arrivals(),
      ])
      const allTrips = [
        ...depRes.saidas.map((t) => normalizeTrip({ ...t, trip_direction: 'SAIDA' })),
        ...arrRes.chegadas.map((t) => normalizeTrip({ ...t, trip_direction: 'CHEGADA' })),
      ]
      setTrips(allTrips)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro ao carregar painel')
    } finally {
      setLoading(false)
    }
  }

  async function fetchAdminData() {
    try {
      setError(null)
      const [tripsRes, compRes, destRes, platRes, usersRes] = await Promise.all([
        api.trips.list(),
        api.companies.list(),
        api.destinations.list(),
        api.platforms.list(),
        api.auth.listUsers().catch(() => ({ Usuarios: [] as AppUser[] })),
      ])
      setUsers(usersRes.Usuarios)
      setTrips(tripsRes.Viagens.map(normalizeTrip))
      setCompanies(compRes.Companhias)
      setDestinations(destRes.Destinos)
      setPlatforms(platRes.Plataformas)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro ao carregar dados admin')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (view === 'public') {
      fetchPublicData()
      const interval = setInterval(fetchPublicData, 30000)
      return () => clearInterval(interval)
    }

    if (isAuthenticated && role === 'adm') {
      fetchAdminData()
    }
  }, [view, isAuthenticated, role])

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token && !getRole()) {
      logout() // sessão antiga, sem função salva: pede login de novo
    } else if (token) {
      setIsAuthenticated(true)
      setView('users')
      setAdminTab('overview')
    }
  }, [])

  const departures = useMemo(
    () =>
      [...trips]
        .filter((trip) => trip.trip_direction === 'SAIDA')
        .sort((a, b) => parseTime(a.scheduled_time) - parseTime(b.scheduled_time)),
    [trips],
  )

  const arrivals = useMemo(
    () =>
      [...trips]
        .filter((trip) => trip.trip_direction === 'CHEGADA')
        .sort((a, b) => parseTime(a.scheduled_time) - parseTime(b.scheduled_time)),
    [trips],
  )

  const activeTrips = useMemo(
    () =>
      [...trips]
        .filter((trip) => ['EMBARQUE', 'NO HORARIO', 'ATRASADO', 'SAIU'].includes(trip.status))
        .sort((a, b) => parseTime(a.scheduled_time) - parseTime(b.scheduled_time)),
    [trips],
  )

  const nextDeparture = departures[0]

  async function handleLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoginError('')
    try {
      const res = await api.auth.login(email, password)
      if (!res.role) throw new Error('O servidor não informou a função do usuário. Atualize o login no backend.')
      saveSession(res.access_token, res.refresh_token, res.role)
      setRole(res.role)
      setIsAuthenticated(true)
      setView('users')
      setAdminTab('overview')
      showNotification('success', 'Login realizado com sucesso')
      if (res.role === 'adm') await refreshAllAdminData()
    } catch (e) {
      const message = readError(e, 'Credenciais inválidas')
      setLoginError(message)
      showNotification('error', message)
    }
  }

  function handleLogout() {
    logout()
    setRole(null)
    setIsAuthenticated(false)
    setView('login')
    setAdminTab('overview')
    setLoginError('')
    showNotification('success', 'Sessão encerrada')
  }

  const handleOpenAdminRoute = (target: AdminTab) => {
    setIsAuthenticated(true)
    setView(target === 'overview' ? 'users' : target)
    setAdminTab(target)
  }

  const renderAdminContent = () => {
    if (!isAuthenticated) {
      return (
        <div className="login-card admin-lock">
          <div className="login-header">
            <div>
              <p className="eyebrow">Acesso restrito</p>
              <h2>Login administrativo</h2>
            </div>
          </div>

          <form onSubmit={handleLogin} className="login-form">
            {loginError && <div className="login-error">{loginError}</div>}
            <label>
              E-mail
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="admin@busboard.com"
                required
              />
            </label>

            <label>
              Senha
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
                required
              />
            </label>

            <div className="form-actions">
              <button type="submit" className="primary-button">
                Entrar
              </button>
              <button type="button" className="ghost-button" onClick={() => { window.location.href = '/painel' }}>
                Ver painel da TV
              </button>
            </div>

            <p className="login-hint">
              Recebeu um convite para criar conta?{' '}
              <a href="/cadastro">Clique aqui</a>.
            </p>
          </form>
        </div>
      )
    }

    if (isOperator) return <OperatorPanel />

    return (
      <section className="admin-layout">
        <aside className="admin-sidebar">
          <button className={adminTab === 'overview' ? 'sidebar-link active' : 'sidebar-link'} onClick={() => setAdminTab('overview')}>
            Visão geral
          </button>
          <button className={adminTab === 'operation' ? 'sidebar-link active' : 'sidebar-link'} onClick={() => handleOpenAdminRoute('operation')}>
            Operação do dia
          </button>
          <button className={adminTab === 'users' ? 'sidebar-link active' : 'sidebar-link'} onClick={() => handleOpenAdminRoute('users')}>
            Usuários
          </button>
          <button className={adminTab === 'convites' ? 'sidebar-link active' : 'sidebar-link'} onClick={() => handleOpenAdminRoute('convites')}>
            Convites
          </button>
          <button className={adminTab === 'companies' ? 'sidebar-link active' : 'sidebar-link'} onClick={() => handleOpenAdminRoute('companies')}>
            Empresas
          </button>
          <button className={adminTab === 'destinations' ? 'sidebar-link active' : 'sidebar-link'} onClick={() => handleOpenAdminRoute('destinations')}>
            Destinos
          </button>
          <button className={adminTab === 'platforms' ? 'sidebar-link active' : 'sidebar-link'} onClick={() => handleOpenAdminRoute('platforms')}>
            Plataformas
          </button>
          <button className={adminTab === 'trips' ? 'sidebar-link active' : 'sidebar-link'} onClick={() => handleOpenAdminRoute('trips')}>
            Viagens
          </button>

          <div className="sidebar-card">
            <p>Conectado</p>
            <strong>Administrador</strong>
            <small>Rotas reais do sistema</small>
          </div>
        </aside>

        <div className="admin-main">
          <div className="admin-topline">
            <div>
              <p className="eyebrow">Painel administrativo</p>
              <h2>Gestão operacional do BusBoard</h2>
            </div>
            <div className="form-actions compact">
              <button type="button" className="ghost-button" onClick={() => window.open('/painel', '_blank')}>
                Ver painel da TV
              </button>
              <button type="button" className="ghost-button" onClick={handleLogout}>
                Sair
              </button>
            </div>
          </div>

          {error && <div className="error-banner">{error}</div>}
          {notification && <div className={`notice ${notification.kind}`}>{notification.message}</div>}
          {loading ? (
            <div className="loading">Carregando dados administrativos...</div>
          ) : (
            <>
              {adminTab === 'overview' && (
                <>
                  <div className="metrics-grid">
                    <div className="metric-card">
                      <span>Viagens ativas</span>
                      <strong>{activeTrips.length}</strong>
                    </div>
                    <div className="metric-card">
                      <span>Empresas</span>
                      <strong>{companies.length}</strong>
                    </div>
                    <div className="metric-card">
                      <span>Plataformas</span>
                      <strong>{platforms.length}</strong>
                    </div>
                    <div className="metric-card">
                      <span>Destinos</span>
                      <strong>{destinations.length}</strong>
                    </div>
                  </div>

                  <div className="panel-grid">
                    <div className="panel-card">
                      <div className="card-title-row">
                        <h3>Próximas alterações</h3>
                        <button type="button" className="ghost-button" onClick={() => setAdminTab('trips')}>
                          Novo registro
                        </button>
                      </div>

                      <ul className="list-card">
                        {trips.slice(0, 4).map((trip) => (
                          <li key={trip.trip_id ?? trip.id}>
                            <div>
                              <strong>{trip.company}</strong>
                              <small>
                                {trip.destination} • {trip.scheduled_time}
                              </small>
                            </div>
                            <span className={`status-badge ${statusClassMap[trip.status as TripStatus] || ''}`}>
                              {trip.status}
                            </span>
                          </li>
                        ))}
                        {trips.length === 0 && (
                          <li style={{ color: '#94a3b8', textAlign: 'center' }}>Nenhuma viagem cadastrada</li>
                        )}
                      </ul>
                    </div>

                    <div className="panel-card">
                      <div className="card-title-row">
                        <h3>Atalhos</h3>
                      </div>

                      <div className="quick-actions">
                        <button type="button" onClick={() => setAdminTab('users')}>+ Usuário</button>
                        <button type="button" onClick={() => setAdminTab('companies')}>+ Empresa</button>
                        <button type="button" onClick={() => setAdminTab('destinations')}>+ Destino</button>
                        <button type="button" onClick={() => setAdminTab('platforms')}>+ Plataforma</button>
                        <button type="button" onClick={() => setAdminTab('trips')}>+ Viagem</button>
                        <button type="button" onClick={() => refreshAllAdminData()}>Atualizar dados</button>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {adminTab === 'users' && (
                <AbaUsuarios
                  usuarios={users}
                  showNotification={showNotification}
                  refreshAllAdminData={refreshAllAdminData}
                />
              )}

              {adminTab === 'convites' && (
                <AbaConvites
                  showNotification={showNotification}
                  refreshAllAdminData={refreshAllAdminData}
                />
              )}

              {adminTab === 'companies' && (
                <AbaEmpresas
                  empresas={companies}
                  showNotification={showNotification}
                  refreshAllAdminData={refreshAllAdminData}
                />
              )}

              {adminTab === 'destinations' && (
                <AbaDestinos
                  destinos={destinations}
                  showNotification={showNotification}
                  refreshAllAdminData={refreshAllAdminData}
                />
              )}

              {adminTab === 'platforms' && (
                <AbaPlataformas
                  plataformas={platforms}
                  showNotification={showNotification}
                  refreshAllAdminData={refreshAllAdminData}
                />
              )}

              {adminTab === 'operation' && <OperatorPanel embedded />}

              {adminTab === 'trips' && (
                <AbaViagens
                  viagens={trips}
                  empresas={companies}
                  destinos={destinations}
                  plataformas={platforms}
                  showNotification={showNotification}
                  refreshAllAdminData={refreshAllAdminData}
                />
              )}
            </>
          )}
        </div>
      </section>
    )
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Painel digital de rodoviária</p>
          <h1>BusBoard</h1>
        </div>

        <div className="header-actions">
          <div className="clock-box">
            <span>{currentTime.toLocaleDateString('pt-BR', { weekday: 'short' })}</span>
            <strong>
              {currentTime.toLocaleTimeString('pt-BR', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })}
            </strong>
          </div>
          {isAuthenticated && view !== 'public' && (
            <button onClick={handleLogout} className="ghost-button">
              Sair
            </button>
          )}
        </div>
      </header>

      <main className="content-area">
        {view === 'public' && (
          <>
            {error && <div className="error-banner">{error}</div>}
            {loading ? (
              <div className="loading">Carregando painel...</div>
            ) : (
              <>
                <section className="summary-bar">
                  <div className="summary-item highlight">
                    <span>Próxima saída</span>
                    <strong>
                      {nextDeparture
                        ? `${nextDeparture.destination} • ${nextDeparture.scheduled_time}`
                        : 'Sem viagens'}
                    </strong>
                  </div>
                  <div className="summary-item">
                    <span>Saídas hoje</span>
                    <strong>{departures.length}</strong>
                  </div>
                  <div className="summary-item">
                    <span>Chegadas hoje</span>
                    <strong>{arrivals.length}</strong>
                  </div>
                </section>

                <section className="board-grid">
                  <div className="board-card">
                    <div className="board-header">
                      <h2>Saídas</h2>
                      <span className="board-tag">Terminal 1</span>
                    </div>

                    <table>
                      <thead>
                        <tr>
                          <th>Horário</th>
                          <th>Destino</th>
                          <th>Empresa</th>
                          <th>Plataforma</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {departures.map((trip) => (
                          <tr key={trip.trip_id ?? trip.id}>
                            <td>{trip.scheduled_time}</td>
                            <td>{trip.destination}</td>
                            <td>{trip.company}</td>
                            <td>{trip.platform}</td>
                            <td>
                              <span className={`status-badge ${statusClassMap[trip.status as TripStatus] || ''}`}>
                                {trip.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                        {departures.length === 0 && (
                          <tr>
                            <td colSpan={5} style={{ textAlign: 'center', color: '#666' }}>
                              Nenhuma saída programada
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  <div className="board-card">
                    <div className="board-header">
                      <h2>Chegadas</h2>
                      <span className="board-tag">Terminal 2</span>
                    </div>

                    <table>
                      <thead>
                        <tr>
                          <th>Horário</th>
                          <th>Origem</th>
                          <th>Empresa</th>
                          <th>Plataforma</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {arrivals.map((trip) => (
                          <tr key={trip.trip_id ?? trip.id}>
                            <td>{trip.scheduled_time}</td>
                            <td>{trip.destination}</td>
                            <td>{trip.company}</td>
                            <td>{trip.platform}</td>
                            <td>
                              <span className={`status-badge ${statusClassMap[trip.status as TripStatus] || ''}`}>
                                {trip.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                        {arrivals.length === 0 && (
                          <tr>
                            <td colSpan={5} style={{ textAlign: 'center', color: '#666' }}>
                              Nenhuma chegada programada
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </section>

                <section className="panel-grid public-cta-grid">
                  <div className="panel-card hero-card">
                    <p className="eyebrow">Operação em tempo real</p>
                    <h3>Entre no painel administrativo para cadastrar usuários, viagens e estruturas da rodoviária.</h3>
                    <div className="form-actions">
                      <button className="primary-button" type="button" onClick={() => navigate('login')}>
                        Acessar administração
                      </button>
                      <button className="ghost-button" type="button" onClick={() => navigate('users')}>
                        Criar usuário
                      </button>
                    </div>
                  </div>

                  <div className="panel-card hero-card secondary">
                    <p className="eyebrow">Resumo operacional</p>
                    <h3>{activeTrips.length} viagens com status em andamento</h3>
                    <small>Dados atualizados a cada 30 segundos no painel público.</small>
                  </div>
                </section>
              </>
            )}
          </>
        )}

        {view !== 'public' && renderAdminContent()}
      </main>
    </div>
  )
}

export default App