// Aba de empresas: criar, editar, ativar/desativar e excluir.
import { useState } from 'react'
import { api, type Company } from '../api'
import { readError, scrollToTop, type AbaProps } from '../comuns'

type AbaEmpresasProps = AbaProps & {
  empresas: Company[]
}

export default function AbaEmpresas({ empresas, showNotification, refreshAllAdminData }: AbaEmpresasProps) {
  const [companyName, setCompanyName] = useState('')
  const [editingCompanyId, setEditingCompanyId] = useState<number | null>(null)

  function startEditCompany(company: Company) {
    setEditingCompanyId(company.id)
    setCompanyName(company.name)
    scrollToTop()
  }

  function cancelEditCompany() {
    setEditingCompanyId(null)
    setCompanyName('')
  }

  async function handleSaveCompany(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      const result =
        editingCompanyId === null
          ? await api.companies.create({ name: companyName, active: true })
          : await api.companies.update(editingCompanyId, { name: companyName })
      showNotification('success', result.mensagem)
      cancelEditCompany()
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao salvar empresa'))
    }
  }

  async function handleToggleCompany(company: Company) {
    try {
      const result = await api.companies.update(company.id, { active: !company.active })
      showNotification('success', result.mensagem)
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao alterar empresa'))
    }
  }

  async function handleDeleteCompany(company: Company) {
    if (!window.confirm(`Excluir a empresa "${company.name}"? Isso não pode ser desfeito.`)) return
    try {
      const result = await api.companies.delete(company.id)
      showNotification('success', result.mensagem)
      if (editingCompanyId === company.id) cancelEditCompany()
      await refreshAllAdminData()
    } catch (e) {
      showNotification('error', readError(e, 'Falha ao excluir empresa'))
    }
  }

  return (
    <div className="route-grid">
      <form className="route-card form-card" onSubmit={handleSaveCompany}>
        <div className="card-title-row">
          <h3>{editingCompanyId === null ? 'Criar empresa' : 'Editar empresa'}</h3>
        </div>
        <label>
          Nome da empresa
          <input value={companyName} onChange={(event) => setCompanyName(event.target.value)} required />
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit">
            {editingCompanyId === null ? 'Salvar empresa' : 'Salvar alterações'}
          </button>
          {editingCompanyId !== null && (
            <button className="ghost-button" type="button" onClick={cancelEditCompany}>Cancelar</button>
          )}
        </div>
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
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {empresas.map((company) => (
              <tr key={company.id} className={company.active ? '' : 'row-inactive'}>
                <td>{company.id}</td>
                <td>{company.name}</td>
                <td>{company.active ? 'Ativa' : 'Inativa'}</td>
                <td>
                  <div className="row-actions">
                    <button type="button" className="mini-button" onClick={() => startEditCompany(company)}>Editar</button>
                    <button type="button" className="mini-button" onClick={() => handleToggleCompany(company)}>
                      {company.active ? 'Desativar' : 'Ativar'}
                    </button>
                    <button type="button" className="mini-button danger" onClick={() => handleDeleteCompany(company)}>Excluir</button>
                  </div>
                </td>
              </tr>
            ))}
            {empresas.length === 0 && (
              <tr><td colSpan={4}>Nenhuma empresa cadastrada</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
