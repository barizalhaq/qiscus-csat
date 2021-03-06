"""empty message

Revision ID: 2fba115c2de8
Revises: 118766cbd2c6
Create Date: 2021-08-05 09:30:26.066040

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2fba115c2de8'
down_revision = '118766cbd2c6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('configs', 'rating_total',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('configs', 'rating_type',
               existing_type=postgresql.ENUM('CUSTOM', 'EMOJI', 'NUMBER', 'STAR', name='ratingtype'),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('configs', 'rating_type',
               existing_type=postgresql.ENUM('CUSTOM', 'EMOJI', 'NUMBER', 'STAR', name='ratingtype'),
               nullable=False)
    op.alter_column('configs', 'rating_total',
               existing_type=sa.INTEGER(),
               nullable=False)
    # ### end Alembic commands ###
