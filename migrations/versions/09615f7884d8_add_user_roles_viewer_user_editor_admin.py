"""Add user roles (viewer/user/editor/admin)

Revision ID: 09615f7884d8
Revises: f4a4b38fec06
Create Date: 2026-09-26 08:22:57.375814

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '09615f7884d8'
down_revision = 'f4a4b38fec06'
branch_labels = None
depends_on = None


def upgrade():
    """
    Добавляем role, переносим данные, делаем NOT NULL, удаляем is_admin.
    """

    # === ШАГ 1: Добавляем колонку role как NULLABLE ===
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('role', sa.String(length=20), nullable=True)
        )

    # === ШАГ 2: Заполняем role данными из is_admin (вне batch) ===
    op.execute(
        "UPDATE user SET role = 'admin' WHERE is_admin = 1"
    )
    op.execute(
        "UPDATE user SET role = 'user' WHERE is_admin = 0 OR is_admin IS NULL"
    )

    # === ШАГ 3: Делаем role NOT NULL и удаляем is_admin (ОДИН batch) ===
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column(
            'role',
            existing_type=sa.String(length=20),
            nullable=False,
        )
        batch_op.drop_column('is_admin')


def downgrade():
    """Обратная операция."""
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('is_admin', sa.Boolean(), nullable=True)
        )

    op.execute("UPDATE user SET is_admin = 1 WHERE role = 'admin'")
    op.execute("UPDATE user SET is_admin = 0 WHERE role != 'admin'")

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column(
            'is_admin',
            existing_type=sa.Boolean(),
            nullable=False,
        )
        batch_op.drop_column('role')