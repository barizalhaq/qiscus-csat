"""Add EMOJI to RatingType

Revision ID: 118766cbd2c6
Revises: 438ede29d913
Create Date: 2021-05-06 13:54:45.231087

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '118766cbd2c6'
down_revision = '438ede29d913'
branch_labels = None
depends_on = None

enum_name = 'ratingtype'
tmp_enum_name = 'tmp'+enum_name

old_options = ('STAR', 'NUMBER', 'CUSTOM')
new_options = sorted(old_options + ('EMOJI',))

old_type = sa.Enum(*old_options, name=enum_name)
new_type = sa.Enum(*new_options, name=enum_name)


def upgrade():
    op.execute('ALTER TYPE ' + enum_name + ' RENAME TO ' + tmp_enum_name)
    new_type.create(op.get_bind())
    op.execute(
        'ALTER TABLE configs ALTER COLUMN rating_type TYPE ' + enum_name + ' USING rating_type::text::' + enum_name)
    op.execute('DROP TYPE ' + tmp_enum_name)
    pass


def downgrade():
    op.execute('ALTER TYPE ' + enum_name + ' RENAME TO ' + tmp_enum_name)
    old_type.create(op.get_bind())
    op.execute(
        'ALTER TABLE configs ALTER COLUMN rating_type TYPE ' + enum_name + ' USING rating_type::text::' + enum_name)
    op.execute('DROP TYPE ' + tmp_enum_name)
    pass
