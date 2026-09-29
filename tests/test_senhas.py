"""Senha: hash, verificação e a troca do passlib pelo bcrypt direto.

O passlib foi removido (não é mantido e não lia a versão do bcrypt 4.x). O
formato do hash é o mesmo, então quem já tinha conta continua entrando —
esses testes existem para garantir que isso não se quebre sem ninguém
perceber.
"""
import bcrypt
import pytest

from senhas import CUSTO, gerar_hash, verificar_senha


def test_gerar_hash_e_verificar():
    hash_ = gerar_hash("senha123")
    assert verificar_senha("senha123", hash_)
    assert not verificar_senha("senha_errada", hash_)


def test_hash_tem_formato_bcrypt_com_custo_12():
    """O formato é o mesmo do passlib: $2b$ + custo + 53 chars de hash."""
    hash_ = gerar_hash("senha123")
    assert hash_.startswith(f"$2b${CUSTO:02d}$")
    assert len(hash_) == 60


def test_sal_salva_hashes_iguais():
    """Duas contas com a mesma senha não podem ter o mesmo hash no banco."""
    assert gerar_hash("mesma") != gerar_hash("mesma")


def test_hash_antigo_do_passlib_continua_valendo():
    """Regressão do passlib: um hash no formato antigo precisa continuar válido.

    Se isso quebrar, todo usuário existente perde a senha na atualização — e
    só apareceria com ele na frente da tela de login.
    """
    hash_antigo = bcrypt.hashpw(b"senha-antiga-123", bcrypt.gensalt(CUSTO)).decode()
    assert verificar_senha("senha-antiga-123", hash_antigo)
    assert not verificar_senha("outra-coisa", hash_antigo)


def test_senha_acima_de_72_bytes_nao_e_truncada():
    """O bcrypt ignora o que passa de 72 bytes, sem avisar.

    Sem o pré-hash, "A"*72 e "A"*72 + qualquer coisa dariam o mesmo hash:
    alguém com a senha longa-plus entraria com a senha curta. Aqui os dois
    lados são conferidos para essa troca não voltar.
    """
    curta = "A" * 72
    longa = curta + "SUFIXO-IGNORADO"

    assert verificar_senha(curta, gerar_hash(longa)) is False
    assert verificar_senha(longa, gerar_hash(longa)) is True


def test_senha_longa_e_curta_com_prefixo_comum_nao_colidem():
    """Mesmo sem estourar 72 bytes, senhas parecidas precisam gerar hashes
    diferentes (o hash é do texto inteiro, não de um pedaço dele)."""
    base = "senha-comum-para-teste-"
    assert not verificar_senha(base + "a", gerar_hash(base + "b"))


@pytest.mark.parametrize(
    "senha, hash_guardado",
    [
        ("", "$2b$12$" + "x" * 53),
        ("senha", ""),
        ("senha", "isto-nao-e-um-hash"),
        ("senha", None),
    ],
    ids=["senha-vazia", "hash-vazio", "hash-corrompido", "hash-none"],
)
def test_entrada_invalida_devolve_false_sem_estourar(senha, hash_guardado):
    """Um erro aqui viraria 500 na tela de login, e o usuário veria uma
    mensagem de servidor quebrado em vez de 'senha incorreta'."""
    assert verificar_senha(senha, hash_guardado) is False


def test_hash_com_outro_formato_nao_estoura():
    """Hash de outro esquema (ex.: de um import antigo) não pode derrubar o login."""
    assert verificar_senha("senha", "$argon2id$v=19$m=65536$hashaqui") is False
