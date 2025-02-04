"""Initial database migration

Revision ID: 001
Revises: 
Create Date: 2025-02-03 21:21:30.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token_address', sa.String(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('position_size', sa.Float(), nullable=False),
        sa.Column('entry_time', sa.DateTime(), nullable=False),
        sa.Column('exit_time', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create tokens table
    op.create_table(
        'tokens',
        sa.Column('address', sa.String(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('decimals', sa.Integer(), nullable=True),
        sa.Column('last_price', sa.Float(), nullable=True),
        sa.Column('liquidity_usd', sa.Float(), nullable=True),
        sa.Column('market_cap', sa.Float(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('address')
    )
    
    # Create monitoring table
    op.create_table(
        'monitoring',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('monitoring')
    op.drop_table('tokens')
    op.drop_table('trades')
