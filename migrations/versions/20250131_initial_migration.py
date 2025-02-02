"""Initial migration

Revision ID: 20250131_initial
Create Date: 2025-01-31 21:13:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250131_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('side', sa.String(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('cost', sa.Float(), nullable=False),
        sa.Column('fee', sa.Float()),
        sa.Column('realized_pnl', sa.Float()),
        sa.Column('position_id', sa.Integer(), sa.ForeignKey('positions.id')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create positions table
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('entry_timestamp', sa.DateTime(), nullable=False),
        sa.Column('exit_timestamp', sa.DateTime()),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float()),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('leverage', sa.Float(), default=1.0),
        sa.Column('stop_loss', sa.Float()),
        sa.Column('take_profit', sa.Float()),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('pnl', sa.Float()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create risk_metrics table
    op.create_table(
        'risk_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('var', sa.Float()),
        sa.Column('sharpe', sa.Float()),
        sa.Column('max_drawdown', sa.Float()),
        sa.Column('volatility', sa.Float()),
        sa.Column('beta', sa.Float()),
        sa.Column('metrics_data', sa.String()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indices
    op.create_index('ix_trades_symbol', 'trades', ['symbol'])
    op.create_index('ix_trades_timestamp', 'trades', ['timestamp'])
    op.create_index('ix_positions_symbol', 'positions', ['symbol'])
    op.create_index('ix_positions_status', 'positions', ['status'])
    op.create_index('ix_risk_metrics_symbol', 'risk_metrics', ['symbol'])
    op.create_index('ix_risk_metrics_timestamp', 'risk_metrics', ['timestamp'])

def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('risk_metrics')
    op.drop_table('trades')
    op.drop_table('positions')
