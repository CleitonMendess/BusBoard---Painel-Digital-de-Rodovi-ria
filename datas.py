# datas.py → o "agora" do sistema, em um lugar só
#
# Python 3.12 depreciou datetime.utcnow() e o 3.13 avisa a cada uso; some no
# futuro. A troca óbvia, datetime.now(timezone.utc), devolve data *com fuso*,
# e aqui isso quebraria: o SQLite não guarda fuso — nem mesmo com
# DateTime(timezone=True), o SQLAlchemy devolve a data sem tzinfo. Aí o
# código passaria a comparar uma data com fuso (vinda do now()) contra uma
# sem (vinda do banco), e datetime.now() > valor_do_banco levanta
# "can't compare offset-naive and offset-aware datetimes". Foi o que aconteceu
# ao medir as duas estratégias.
#
# Então a regra do projeto é: **toda data gravada é UTC sem fuso, e
# agora_utc() é a única forma de obter "agora"**. O formato não muda em nada
# (2026-09-30 04:11:07.916043 continua igual), então:
#   - não precisa migration;
#   - o banco continua lendo igual;
#   - o frontend continua interpretando como UTC (AbaConvites já acrescenta
#     o "Z" quando a string não tem);
#   - as comparações de data com data seguem funcionando.
#
# O que não se deve fazer: usar datetime.now() sem fuso em código que grava
# no banco (aí entraria hora local, 3 horas atrás de Brasília, e as viagens
# apareceriam com o horário errado).
from datetime import datetime, timezone


def agora_utc() -> datetime:
    """"Agora" em UTC, sem tzinfo — o mesmo formato que o utcnow() gravava.

    Use para default de coluna, created_at, expires_at, e para comparar com
    data lida do banco.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
