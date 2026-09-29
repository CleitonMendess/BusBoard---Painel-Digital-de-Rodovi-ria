import { useEffect, useMemo, useState } from 'react'
import {
  api,
  logout,
  type Trip,
  type Company,
  type Destination,
  type Platform,
} from './api'
import './App.css'

type TripDirection = 'SAIDA' | 'CHEGADA'
type TripStatus =
  | 'AGENDADO'
  | 'NO HORARIO'
  | 'EMBARQUE'
  | 'ATRASADO'
  | 'CANCELADO'
  | 'SAIU'
  | 'CHEGOU'

type View = 'public' | 'login' | 'users' | 'companies' | 'destinations' | 'platforms' | 'trips'
type AdminTab = 'overview' | 'users' | 'companies' | 'destinations' | 'platforms' | 'trips'

type Notification = {
  kind: 'success' | 'error'
  message: string
}

const statusClassMap: Record<TripStatus, string> = {
  AGENDADO: 'status-agendado',
  'NO HORARIO': 'status-no-horario',
  EMBARQUE: 'status-embarque',
  ATRASADO: 'status-atrasado',
  CANCELADO: 'status-cancelado',
  SAIU: 'status-saiu',
  CHEGOU: 'status-chegou',
}

const statusOptions: TripStatus[] = [
  'AGENDADO',
  'NO HORARIO',
  'EMBARQUE',
  'ATRASADO',
  'CANCELADO',
  'SAIU',
  'CHEGOU',
]

const directionOptions: TripDirection[] = ['SAIDA', 'CHEGADA']

const parseTime = (time: string) => {
  if (!time) return Number.POSITIVE_INFINITY
  const [hours, minutes] = time.split(':').map(Number)
  return hours * 60 + minutes
}

const formatTime = (time: string | null | undefined) => time || '-'

function normalizeTrip(t: Trip): Trip & { trip_direction: TripDirection } {
  return {
    ...t,
    trip_direction: (t.trip_direction as TripDirection) || 'SAIDA',
    estimated_time: t.estimated_time ?? null,
  }
}

function readError(error: unknown, fallback: string) {
  if (error instanceof Error) return error.message
  return fallback
}

function App() {
  const [currentTime, setCurrentTime] = useState(new Date())
  const [view, setView] = useState<View>('public')
  const [adminTab, setAdminTab] = useState<AdminTab>('overview')
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [notification, setNotification] = useState<Notification | null>(null)

  const [email, setEmail] = useState('admin@busboard.com')
  const [password, setPassword] = useState('123456')
  const [loginError, setLoginError] = useState('')

  const [userForm, setUserForm] = useState({
    name: '',
    email: '',
    password: '',
    role: 'operador',
    active: true,
  })
  const [companyName, setCompanyName] = useState('')
  const [destinationForm, setDestinationForm] = useState({
    city: '',
    state: '',
    active: true,
  })
  const [platformNumber, setPlatformNumber] = useState('')
  const [tripForm, setTripForm] = useState({
    type: 'INTERESTADUAL',
    trip_direction: 'SAIDA' as TripDirection,
    scheduled_time: '',
    estimated_time: '',
    status: 'AGENDADO' as TripStatus,
    company_id: '',
    destination_id: '',
    platform_id: '',
  })

  const [trips, setTrips] = useState<Trip[]>([])
  const [companies, setCompanies] = useState<Company[]>([])
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
        ...depRes.saidas.map(normalizeTrip),
        ...arrRes.chegadas.map(normalizeTrip),
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
      const [tripsRes, compRes, destRes, platRes] = await Promise.all([
        api.trips.list(),
        api.companies.list(),
        api.destinations.list(),
        api.platforms.list(),
      ])
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

    if (isAuthenticated) {
      fetchAdminData()
    }
  }, [view, isAuthenticated])

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
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
      localStorage.setItem('access_token', res.access_token)
      setIsAuthenticated(true)
      setView('users')
      setAdminTab('overview')
      showNotification('success', 'Login realizado com sucesso')
      await refreshAllAdminData()
    } catch (e) {
      const message = readError(e, 'Credenciais inválidas')
      setLoginError(message)
      showNotification('error', message)
    }
  }

  function handleLogout() {
    logout()
    setIsAuthenticated(false)
    setView('public')
    setAdminTab('overview')
    setLoginError('')
    showNotification('success', 'Sessão encerrada')
  }

  async function handleCreateUser(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      const result = await api.auth.createUser({
        name: userForm.name,
        email: userForm.email,
        password: userForm.password,
        role: userForm.role,
        active: userForm.active,
      })
      showNotification('success', result.mensagem)
      setUserForm({ name: '', email: '', password: '', role: 'operador', active: true })
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao criar usuário'))
    }
  }

  async function handleCreateCompany(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      const result = await api.companies.create({ name: companyName, active: true })
      showNotification('success', result.mensagem)
      setCompanyName('')
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao criar empresa'))
    }
  }

  async function handleCreateDestination(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      const result = await api.destinations.create(destinationForm)
      showNotification('success', result.mensagem)
      setDestinationForm({ city: '', state: '', active: true })
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao criar destino'))
    }
  }

  async function handleCreatePlatform(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      const result = await api.platforms.create({ number: Number(platformNumber), active: true })
      showNotification('success', result.mensagem)
      setPlatformNumber('')
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao criar plataforma'))
    }
  }

  async function handleCreateTrip(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      const result = await api.trips.create({
        type: tripForm.type,
        trip_direction: tripForm.trip_direction,
        scheduled_time: tripForm.scheduled_time,
        estimated_time: tripForm.estimated_time || undefined,
        status: tripForm.status,
        company_id: Number(tripForm.company_id),
        destination_id: Number(tripForm.destination_id),
        platform_id: Number(tripForm.platform_id),
      })
      showNotification('success', result.mensagem)
      setTripForm({
        type: 'INTERESTADUAL',
        trip_direction: 'SAIDA',
        scheduled_time: '',
        estimated_time: '',
        status: 'AGENDADO',
        company_id: '',
        destination_id: '',
        platform_id: '',
      })
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao criar viagem'))
    }
  }

  async function handleChangeTripStatus(tripId: number, status: TripStatus) {
    try {
      const result = await api.trips.updateStatus(tripId, status)
      showNotification('success', result.mensagem)
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao atualizar status'))
    }
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
              <button type="button" className="ghost-button" onClick={() => navigate('public')}>
                Voltar ao painel público
              </button>
            </div>
          </form>
        </div>
      )
    }

    return (
      <section className="admin-layout">
        <aside className="admin-sidebar">
          <button className={adminTab === 'overview' ? 'sidebar-link active' : 'sidebar-link'} onClick={() => setAdminTab('overview')}>
            Visão geral
          </button>
          <button className={adminTab === 'users' ? 'sidebar-link active' : 'sidebar-link'} onClick={() => handleOpenAdminRoute('users')}>
            Usuários
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
              <button type="button" className="ghost-button" onClick={() => navigate('public')}>
                Ver painel público
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
                <div className="route-grid">
                  <form className="route-card form-card" onSubmit={handleCreateUser}>
                    <div className="card-title-row">
                      <h3>Criar usuário</h3>
                    </div>

                    <label>
                      Nome
                      <input value={userForm.name} onChange={(event) => setUserForm({ ...userForm, name: event.target.value })} required />
                    </label>
                    <label>
                      E-mail
                      <input type="email" value={userForm.email} onChange={(event) => setUserForm({ ...userForm, email: event.target.value })} required />
                    </label>
                    <label>
                      Senha
                      <input type="password" value={userForm.password} onChange={(event) => setUserForm({ ...userForm, password: event.target.value })} required />
                    </label>
                    <label>
                      Função
                      <select value={userForm.role} onChange={(event) => setUserForm({ ...userForm, role: event.target.value })}>
                        <option value="operador">Operador</option>
                        <option value="adm">Administrador</option>
                      </select>
                    </label>

                    <label className="switch-row">
                      <input
                        type="checkbox"
                        checked={userForm.active}
                        onChange={(event) => setUserForm({ ...userForm, active: event.target.checked })}
                      />
                      Usuário ativo
                    </label>

                    <button className="primary-button" type="submit">Salvar usuário</button>
                  </form>

                  <div className="route-card info-card">
                    <h3>Regras do cadastro</h3>
                    <p>O backend permite criar administradores apenas quando você já estiver autenticado como adm.</p>
                    <div className="data-list">
                      <span>Total de usuários visíveis</span>
                      <strong>Gerenciado pelo backend</strong>
                    </div>
                  </div>
                </div>
              )}

              {adminTab === 'companies' && (
                <div className="route-grid">
                  <form className="route-card form-card" onSubmit={handleCreateCompany}>
                    <div className="card-title-row">
                      <h3>Criar empresa</h3>
                    </div>
                    <label>
                      Nome da empresa
                      <input value={companyName} onChange={(event) => setCompanyName(event.target.value)} required />
                    </label>
                    <button className="primary-button" type="submit">Salvar empresa</button>
                  </form>

                  <div className="route-card table-wrap">
                    <div className="card-title-row">
                      <h3>Empresas cadastradas</h3>
                    </div>
                    <table>
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Nome</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {companies.map((company) => (
                          <tr key={company.id}>
                            <td>{company.id}</td>
                            <td>{company.name}</td>
                            <td>{company.active ? 'Ativa' : 'Inativa'}</td>
                          </tr>
                        ))}
                        {companies.length === 0 && (
                          <tr><td colSpan={3}>Nenhuma empresa cadastrada</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {adminTab === 'destinations' && (
                <div className="route-grid">
                  <form className="route-card form-card" onSubmit={handleCreateDestination}>
                    <div className="card-title-row">
                      <h3>Criar destino</h3>
                    </div>
                    <label>
                      Cidade
                      <input value={destinationForm.city} onChange={(event) => setDestinationForm({ ...destinationForm, city: event.target.value })} required />
                    </label>
                    <label>
                      Estado
                      <input value={destinationForm.state} onChange={(event) => setDestinationForm({ ...destinationForm, state: event.target.value })} required />
                    </label>
                    <label className="switch-row">
                      <input
                        type="checkbox"
                        checked={destinationForm.active}
                        onChange={(event) => setDestinationForm({ ...destinationForm, active: event.target.checked })}
                      />
                      Destino ativo
                    </label>
                    <button className="primary-button" type="submit">Salvar destino</button>
                  </form>

                  <div className="route-card table-wrap">
                    <div className="card-title-row">
                      <h3>Destinos cadastrados</h3>
                    </div>
                    <table>
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Cidade</th>
                          <th>Estado</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {destinations.map((destination) => (
                          <tr key={destination.id}>
                            <td>{destination.id}</td>
                            <td>{destination.city}</td>
                            <td>{destination.state}</td>
                            <td>{destination.active ? 'Ativo' : 'Inativo'}</td>
                          </tr>
                        ))}
                        {destinations.length === 0 && (
                          <tr><td colSpan={4}>Nenhum destino cadastrado</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {adminTab === 'platforms' && (
                <div className="route-grid">
                  <form className="route-card form-card" onSubmit={handleCreatePlatform}>
                    <div className="card-title-row">
                      <h3>Criar plataforma</h3>
                    </div>
                    <label>
                      Número
                      <input type="number" min="1" value={platformNumber} onChange={(event) => setPlatformNumber(event.target.value)} required />
                    </label>
                    <button className="primary-button" type="submit">Salvar plataforma</button>
                  </form>

                  <div className="route-card table-wrap">
                    <div className="card-title-row">
                      <h3>Plataformas cadastradas</h3>
                    </div>
                    <table>
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Número</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {platforms.map((platform) => (
                          <tr key={platform.id}>
                            <td>{platform.id}</td>
                            <td>{platform.number}</td>
                            <td>{platform.active ? 'Ativa' : 'Inativa'}</td>
                          </tr>
                        ))}
                        {platforms.length === 0 && (
                          <tr><td colSpan={3}>Nenhuma plataforma cadastrada</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {adminTab === 'trips' && (
                <div className="route-grid trips-layout">
                  <form className="route-card form-card" onSubmit={handleCreateTrip}>
                    <div className="card-title-row">
                      <h3>Criar viagem</h3>
                    </div>
                    <label>
                      Tipo
                      <input
                        value={tripForm.type}
                        onChange={(event) => setTripForm({ ...tripForm, type: event.target.value })}
                        required
                      />
                    </label>
                    <label>
                      Direção
                      <select
                        value={tripForm.trip_direction}
                        onChange={(event) => setTripForm({ ...tripForm, trip_direction: event.target.value as TripDirection })}
                      >
                        {directionOptions.map((direction) => (
                          <option key={direction} value={direction}>{direction}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Horário
                      <input type="time" value={tripForm.scheduled_time} onChange={(event) => setTripForm({ ...tripForm, scheduled_time: event.target.value })} required />
                    </label>
                    <label>
                      Previsão
                      <input type="time" value={tripForm.estimated_time} onChange={(event) => setTripForm({ ...tripForm, estimated_time: event.target.value })} />
                    </label>
                    <label>
                      Status
                      <select value={tripForm.status} onChange={(event) => setTripForm({ ...tripForm, status: event.target.value as TripStatus })}>
                        {statusOptions.map((status) => (
                          <option key={status} value={status}>{status}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Empresa
                      <select value={tripForm.company_id} onChange={(event) => setTripForm({ ...tripForm, company_id: event.target.value })} required>
                        <option value="">Selecione</option>
                        {companies.map((company) => (
                          <option key={company.id} value={company.id}>{company.name}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Destino
                      <select value={tripForm.destination_id} onChange={(event) => setTripForm({ ...tripForm, destination_id: event.target.value })} required>
                        <option value="">Selecione</option>
                        {destinations.map((destination) => (
                          <option key={destination.id} value={destination.id}>{destination.city}/{destination.state}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Plataforma
                      <select value={tripForm.platform_id} onChange={(event) => setTripForm({ ...tripForm, platform_id: event.target.value })} required>
                        <option value="">Selecione</option>
                        {platforms.map((platform) => (
                          <option key={platform.id} value={platform.id}>{platform.number}</option>
                        ))}
                      </select>
                    </label>

                    <button className="primary-button" type="submit">Salvar viagem</button>
                  </form>

                  <div className="route-card table-wrap trip-table-card">
                    <div className="card-title-row">
                      <h3>Viagens cadastradas</h3>
                    </div>
                    <table>
                      <thead>
                        <tr>
                          <th>Tipo</th>
                          <th>Horário</th>
                          <th>Destino</th>
                          <th>Plataforma</th>
                          <th>Status</th>
                          <th>Ação</th>
                        </tr>
                      </thead>
                      <tbody>
                        {trips.map((trip) => (
                          <tr key={trip.trip_id ?? trip.id}>
                            <td>{trip.type || '-'}</td>
                            <td>{formatTime(trip.scheduled_time)}</td>
                            <td>{trip.destination}</td>
                            <td>{trip.platform}</td>
                            <td>
                              <span className={`status-badge ${statusClassMap[trip.status as TripStatus] || ''}`}>
                                {trip.status}
                              </span>
                            </td>
                            <td>
                              <select
                                defaultValue={trip.status}
                                onChange={(event) => handleChangeTripStatus(trip.trip_id ?? trip.id ?? 0, event.target.value as TripStatus)}
                              >
                                {statusOptions.map((status) => (
                                  <option key={status} value={status}>{status}</option>
                                ))}
                              </select>
                            </td>
                          </tr>
                        ))}
                        {trips.length === 0 && (
                          <tr><td colSpan={6}>Nenhuma viagem cadastrada</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
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

      <nav className="tab-nav" aria-label="Navegação principal">
        <button
          type="button"
          className={view === 'public' ? 'tab-button active' : 'tab-button'}
          onClick={() => navigate('public')}
        >
          Painel público
        </button>
        <button
          type="button"
          className={view !== 'public' ? 'tab-button active' : 'tab-button'}
          onClick={() => navigate(isAuthenticated ? 'users' : 'login')}
        >
          Painel admin
        </button>
        <button type="button" className={view === 'users' ? 'tab-button active' : 'tab-button'} onClick={() => navigate(isAuthenticated ? 'users' : 'login')}>
          Criar usuário
        </button>
        <button type="button" className={view === 'companies' ? 'tab-button active' : 'tab-button'} onClick={() => navigate(isAuthenticated ? 'companies' : 'login')}>
          Empresas
        </button>
        <button type="button" className={view === 'destinations' ? 'tab-button active' : 'tab-button'} onClick={() => navigate(isAuthenticated ? 'destinations' : 'login')}>
          Destinos
        </button>
        <button type="button" className={view === 'platforms' ? 'tab-button active' : 'tab-button'} onClick={() => navigate(isAuthenticated ? 'platforms' : 'login')}>
          Plataformas
        </button>
        <button type="button" className={view === 'trips' ? 'tab-button active' : 'tab-button'} onClick={() => navigate(isAuthenticated ? 'trips' : 'login')}>
          Viagens
        </button>
      </nav>

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