"""Add index to User.role

Revision ID: 2aac3fbb2567
Revises: 2acf88b0c238
Create Date: 2026-09-26 18:01:49.945830

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2aac3fbb2567'
down_revision = '2acf88b0c238'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.create_index('ix_user_role', ['role'], unique=False)


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_index('ix_user_role')
