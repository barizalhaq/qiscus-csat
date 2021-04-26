"""empty message

Revision ID: 7a1ffe35f0d0
Revises: 
Create Date: 2021-04-21 21:34:03.280708

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a1ffe35f0d0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('configs', sa.Column('csat_page', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('configs', 'csat_page')
    # ### end Alembic commands ###
