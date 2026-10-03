"""Add page_id to MenuItem

Revision ID: 1035e8403b1a
Revises: cd0871c45153
Create Date: 2026-09-29 16:37:22.625393

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1035e8403b1a'
down_revision = 'cd0871c45153'
branch_labels = None
depends_on = None


def upgrade():
    """Добавляем колонку page_id в menu_item."""
    with op.batch_alter_table('menu_item', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('page_id', sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_menu_item_page_id',
            'page',
            ['page_id'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_unique_constraint(
            'uq_menu_item_page_id',
            ['page_id'],
        )


def downgrade():
    with op.batch_alter_table('menu_item', schema=None) as batch_op:
        batch_op.drop_constraint('uq_menu_item_page_id', type_='unique')
        batch_op.drop_constraint('fk_menu_item_page_id', type_='foreignkey')
        batch_op.drop_column('page_id')
