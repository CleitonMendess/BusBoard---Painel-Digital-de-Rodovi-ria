# senhas.py → hash e verificação de senha
#
# Usa o bcrypt direto, sem o passlib: o passlib 1.7.4 não é mantido há anos e
# não consegue ler a versão do bcrypt 4.x (ele procura um atributo que não
# existe mais), o que faz ele reclamar a cada senha criada ou conferida.
#
# Detalhe que importa: o bcrypt ignora tudo que passa de 72 bytes, sem avisar.
# "senha longa" e "senha longa com um sufixo" dariam o mesmo hash. Aqui a senha
# passa por um SHA-256 antes, que é o que resolve isso (é o mesmo caminho que
# o passlib usava, então os hashes antigos continuam válidos).
import base64
import hashlib

import bcrypt

# Custo 12: ~250 ms por hash. Lento o bastante para atrapalhar ataque de
# força bruta, rápido o bastante para o login não parecer travado.
CUSTO = 12
TAMANHO_MAXIMO = 72


def _preparar(senha: str) -> bytes:
    """Reduz a senha a 72 bytes sem perder informação.

    base64 do SHA-256 tem 44 bytes, então sempre cabe, e duas senhas diferentes
    nunca viram a mesma coisa por corte.
    """
    if len(senha.encode("utf-8")) <= TAMANHO_MAXIMO:
        return senha.encode("utf-8")
    digest = hashlib.sha256(senha.encode("utf-8")).digest()
    return base64.b64encode(digest)


def gerar_hash(senha: str) -> str:
    """Devolve o hash no mesmo formato do passlib ($2b$...), então quem já
    tinha conta continua entrando sem trocar a senha."""
    return bcrypt.hashpw(_preparar(senha), bcrypt.gensalt(CUSTO)).decode("utf-8")


def verificar_senha(senha: str, hash_guardado: str) -> bool:
    """Confere a senha. Hash inválido ou corrompido é só False, sem estourar:
    um erro aqui viraria resposta 500 na tela de login."""
    if not senha or not hash_guardado:
        return False
    try:
        return bcrypt.checkpw(_preparar(senha), hash_guardado.encode("utf-8"))
    except (ValueError, TypeError):
        return False
