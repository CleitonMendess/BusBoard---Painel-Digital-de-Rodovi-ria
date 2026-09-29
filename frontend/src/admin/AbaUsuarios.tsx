// Aba de usuários: criar, mudar função, ativar/desativar e excluir.
import { useState } from 'react'
import { api, type AppUser } from '../api'
import { readError, type AbaProps } from '../comuns'

type AbaUsuariosProps = AbaProps & {
  usuarios: AppUser[]
}

const FORM_VAZIO = {
  name: '',
  email: '',
  password: '',
  role: 'operador',
  active: true,
}

export default function AbaUsuarios({ usuarios, showNotification, refreshAllAdminData }: AbaUsuariosProps) {
  const [userForm, setUserForm] = useState(FORM_VAZIO)

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
      setUserForm(FORM_VAZIO)
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao criar usuário'))
    }
  }

  async function handleChangeRole(user: AppUser, newRole: string) {
    const label = newRole === 'adm' ? 'Administrador' : 'Operador'
    if (!window.confirm(`Mudar a função de ${user.name} para ${label}?`)) return
    try {
      const result = await api.auth.changeRole(user.id, newRole)
      showNotification('success', result.mensagem)
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao mudar função'))
    }
  }

  async function handleToggleUserActive(user: AppUser) {
    try {
      const result = await api.auth.changeActive(user.id, !user.active)
      showNotification('success', result.mensagem)
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao alterar usuário'))
    }
  }

  async function handleDeleteUser(user: AppUser) {
    if (!window.confirm(`Excluir o usuário "${user.name}"? O histórico de alterações das viagens é mantido, mas ele não consegue mais entrar no sistema.`)) return
    try {
      const result = await api.auth.delete(user.id)
      showNotification('success', result.mensagem)
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao excluir usuário'))
    }
  }

  return (
    <div className="route-grid users-layout">
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

      <div className="route-card table-wrap">
        <div className="card-title-row">
          <h3>Usuários cadastrados</h3>
        </div>
        <table>
          <thead>
            <tr>
              <th>Nome</th>
              <th>E-mail</th>
              <th>Função</th>
              <th>Status</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map((user) => (
              <tr key={user.id} className={user.active ? '' : 'row-inactive'}>
                <td>{user.name}</td>
                <td>{user.email}</td>
                <td>
                  <select value={user.role} onChange={(event) => handleChangeRole(user, event.target.value)}>
                    <option value="operador">Operador</option>
                    <option value="adm">Administrador</option>
                  </select>
                </td>
                <td>{user.active ? 'Ativo' : 'Inativo'}</td>
                <td>
                  <div className="row-actions">
                    <button type="button" className="mini-button" onClick={() => handleToggleUserActive(user)}>
                      {user.active ? 'Desativar' : 'Ativar'}
                    </button>
                    <button type="button" className="mini-button danger" onClick={() => handleDeleteUser(user)}>Excluir</button>
                  </div>
                </td>
              </tr>
            ))}
            {usuarios.length === 0 && (
              <tr><td colSpan={5}>Nenhum usuário listado</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
