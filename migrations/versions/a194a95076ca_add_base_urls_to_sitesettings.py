"""Add base URLs to SiteSettings

Revision ID: a194a95076ca
Revises: 2aac3fbb2567
Create Date: 2026-09-27 11:18:50.270876

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a194a95076ca'
down_revision = '2aac3fbb2567'
branch_labels = None
depends_on = None


def upgrade():
    """Добавляем 3 URL-поля в SiteSettings."""
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'site_base_url',
            sa.String(length=200),
            nullable=False,
            server_default='http://192.168.2.18',
        ))
        batch_op.add_column(sa.Column(
            'cloud_base_url',
            sa.String(length=200),
            nullable=False,
            server_default='http://192.168.2.18:5001',
        ))
        batch_op.add_column(sa.Column(
            'mail_base_url',
            sa.String(length=200),
            nullable=False,
            server_default='http://192.168.2.18:5002',
        ))


def downgrade():
    with op.batch_alter_table('site_settings', schema=None) as batch_op:
        batch_op.drop_column('mail_base_url')
        batch_op.drop_column('cloud_base_url')
        batch_op.drop_column('site_base_url')
