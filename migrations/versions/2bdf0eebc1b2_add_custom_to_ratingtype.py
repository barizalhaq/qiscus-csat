"""Add CUSTOM to RatingType

Revision ID: 2bdf0eebc1b2
Revises: 7a1ffe35f0d0
Create Date: 2021-04-21 21:42:36.192354

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2bdf0eebc1b2'
down_revision = '7a1ffe35f0d0'
branch_labels = None
depends_on = None

# Enum 'type' for PostgreSQL
enum_name = 'ratingtype'
# Set temporary enum 'type' for PostgreSQL
tmp_enum_name = 'tmp_' + enum_name

# Options for Enum
old_options = ('STAR', 'NUMBER')
new_options = sorted(old_options + ('CUSTOM',))

# Create enum fields
old_type = sa.Enum(*old_options, name=enum_name)
new_type = sa.Enum(*new_options, name=enum_name)

def upgrade():
    # Rename current enum type to tmp_
    op.execute('ALTER TYPE ' + enum_name + ' RENAME TO ' + tmp_enum_name)
    # Create new enum type in db
    new_type.create(op.get_bind())
    # Update column to use new enum type
    op.execute('ALTER TABLE configs ALTER COLUMN rating_type TYPE ' + enum_name + ' USING rating_type::text::' + enum_name)
    # Drop old enum type
    op.execute('DROP TYPE ' + tmp_enum_name)
    pass


def downgrade():
    # Rename current enum type to tmp_
    op.execute('ALTER TYPE ' + enum_name + ' RENAME TO ' + tmp_enum_name)
    # Create new enum type in db
    old_type.create(op.get_bind())
    # Update column to use new enum type
    op.execute(
        'ALTER TABLE configs ALTER COLUMN rating_type TYPE ' + enum_name + ' USING rating_type::text::' + enum_name)
    # Drop old enum type
    op.execute('DROP TYPE ' + tmp_enum_name)
    pass
