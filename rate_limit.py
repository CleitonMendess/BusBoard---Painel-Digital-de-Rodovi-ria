"""Trava de tentativas de login.

Sem isso, dá para ficar chutando senha do administrador em loop. A ideia é
simples: contar as falhas de uma mesma chave (ip + e-mail) e, ao passar do
limite, recusar de vez por um tempo.

Configuração opcional no .env:
   LOGIN_MAX_TENTATIVAS=5     falhas antes de travar. Padrão: 5
   LOGIN_JANELA_SEGUNDOS=300   em quantos segundos as falhas somem. Padrão: 300
   LOGIN_BLOQUEIO_SEGUNDOS=60  quanto tempo fica travado. Padrão: 60

O contador fica na memória do processo: some quando o servidor reinicia e não
é compartilhado entre workers. Para uma rodoviária com um servidor só, basta.
Se um dia rodar com várias instâncias, o lugar certo é o banco ou o Redis.
"""
import os
import threading
import time

MAX_TENTATIVAS = int(os.getenv("LOGIN_MAX_TENTATIVAS", "5"))
JANELA_SEGUNDOS = int(os.getenv("LOGIN_JANELA_SEGUNDOS", "300"))
BLOQUEIO_SEGUNDOS = int(os.getenv("LOGIN_BLOQUEIO_SEGUNDOS", "60"))

_tentativas: dict[str, list[float]] = {}
_bloqueios: dict[str, float] = {}
_lock = threading.Lock()


def chave_login(email: str, ip: str) -> str:
    """Ip + e-mail: não trava o terminal inteiro por causa de um e-mail só."""
    return f"{ip or 'desconhecido'}|{(email or '').strip().lower()}"


def _limpar(chave: str, agora: float) -> None:
    _tentativas.pop(chave, None)
    _bloqueios.pop(chave, None)


def segundos_ate_liberar(chave: str) -> int:
    """Quantos segundos faltam para a chave destravar (0 se já está livre)."""
    agora = time.monotonic()
    with _lock:
        fim = _bloqueios.get(chave)
        if fim is None:
            return 0
        restante = int(round(fim - agora))
        if restante <= 0:
            _limpar(chave, agora)
            return 0
        return restante


def registrar_falha(chave: str) -> int:
    """Conta uma tentativa errada. Devolve quantas falhas estão na janela."""
    agora = time.monotonic()
    with _lock:
        if _bloqueios.get(chave, 0) > agora:
            # já está travada: não faz sentido acumular mais
            return len(_tentativas.get(chave, []))

        # descarta as falhas que já caíram fora da janela
        _tentativas[chave] = [
            momento for momento in _tentativas.get(chave, []) if agora - momento < JANELA_SEGUNDOS
        ]
        _tentativas[chave].append(agora)

        if len(_tentativas[chave]) >= MAX_TENTATIVAS:
            _bloqueios[chave] = agora + BLOQUEIO_SEGUNDOS
        return len(_tentativas[chave])


def registrar_sucesso(chave: str) -> None:
    """Entrou com a senha certa: limpa o histórico da chave."""
    with _lock:
        _limpar(chave, time.monotonic())


def tentar_login(chave: str) -> int:
    """Porta de entrada do login. Devolve 0 se pode seguir, ou os segundos de espera."""
    return segundos_ate_liberar(chave)


def zerar() -> None:
    """Limpa tudo (usado nos testes e quando o admin quer destravar na mão)."""
    with _lock:
        _tentativas.clear()
        _bloqueios.clear()
