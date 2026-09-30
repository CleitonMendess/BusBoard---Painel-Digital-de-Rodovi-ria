"""trips.trip_direction passa a ser NOT NULL

O banco foi criado antes de a coluna existir, como "direction"/outro nome, e a
migration inicial (30bfeefb6549) desenhou trip_direction ja como NOT NULL. Só
que a tabela real ja existia: o Alembic marcou a revision como aplicada sem
reconstruir a tabela, então a coluna ficou nullable no banco e NOT NULL no
model. As duas coisas discordam desde o começo.

Consequencia: pelo banco, uma viagem sem direção entraria; pelo model, nao.
Como o schema é responsabilidade do Alembic, quem decide é esta migration.

SQLite nao altera uma coluna no lugar: unsupported só com batch, o
batch_alter_table recria a tabela (copia, apaga, recria com o schema novo e
devolve os dados). Os dados vem primeiro, e so depois a constraint.

Revision ID: 7a1c4e8b2f30
Revises: c652b4563588
Create Date: 2026-09-29 20:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a1c4e8b2f30'
down_revision: Union[str, None] = 'c652b4563588'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ligacao = op.get_bind()

    # O model e a migration exigem NOT NULL, mas banco nenhum deveria aceitar
    # NULL aqui: quem não sabe a direção da viagem é o frontend, que manda
    # "SAIDA" ou "CHEGADA" e o schema já recusa o resto. Se um dia aparecer
    # uma linha vazia (edição manual, import), melhor travar aqui do que
    # devolver viagem sem sentido no painel. Contagem primeiro para a migration
    # avisar se precisar de decisão, em vez de apagar dado na cara dura.
    nulos = ligacao.execute(
        sa.text(
            "SELECT COUNT(*) FROM trips "
            "WHERE trip_direction IS NULL OR TRIM(trip_direction) = ''"
        )
    ).scalar_one()
    if nulos:
        raise RuntimeError(
            f"{nulos} viagem(ns) com trip_direction vazio: resolver antes de rodar esta migration"
        )

    with op.batch_alter_table("trips") as tabela:
        tabela.alter_column(
            "trip_direction",
            existing_type=sa.String(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("trips") as tabela:
        tabela.alter_column(
            "trip_direction",
            existing_type=sa.String(),
            nullable=True,
        )
