"""typeの追加

Revision ID: b785ba3a2637
Revises: 5dcb60747449
Create Date: 2024-05-05 09:47:49.102491

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b785ba3a2637'
down_revision = '5dcb60747449'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('groups', sa.Column('type', sa.VARCHAR(length=255), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('groups', 'type')
    # ### end Alembic commands ###
