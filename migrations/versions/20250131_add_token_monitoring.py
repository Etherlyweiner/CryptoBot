"""Add token monitoring tables

Revision ID: 20250131_add_token_monitoring
Revises: None
Create Date: 2025-01-31 22:30:40.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '20250131_add_token_monitoring'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create new_tokens table
    op.create_table(
        'new_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('initial_price', sa.Float(), nullable=True),
        sa.Column('initial_market_cap', sa.Float(), nullable=True),
        sa.Column('chain', sa.String(length=50), nullable=True),
        sa.Column('contract_address', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('website', sa.String(length=200), nullable=True),
        sa.Column('social_links', sqlite.JSON(), nullable=True),
        sa.Column('launch_date', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes for new_tokens
    op.create_index('ix_new_tokens_symbol', 'new_tokens', ['symbol'])
    op.create_index('ix_new_tokens_timestamp', 'new_tokens', ['timestamp'])
    op.create_index('ix_new_tokens_source', 'new_tokens', ['source'])
    op.create_unique_constraint('uq_new_tokens_symbol_source', 'new_tokens', ['symbol', 'source'])

    # Create token_analysis table
    op.create_table(
        'token_analysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('initial_momentum', sa.Float(), nullable=True),
        sa.Column('social_score', sa.Float(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('opportunity_score', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['symbol'], ['new_tokens.symbol'], ondelete='CASCADE')
    )
    
    # Add indexes for token_analysis
    op.create_index('ix_token_analysis_symbol', 'token_analysis', ['symbol'])
    op.create_index('ix_token_analysis_timestamp', 'token_analysis', ['timestamp'])
    op.create_index('ix_token_analysis_opportunity_score', 'token_analysis', ['opportunity_score'])

    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('opportunity_score', sa.Float(), nullable=True),
        sa.Column('momentum_score', sa.Float(), nullable=True),
        sa.Column('social_score', sa.Float(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('alert_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['symbol'], ['new_tokens.symbol'], ondelete='CASCADE')
    )
    
    # Add indexes for alerts
    op.create_index('ix_alerts_symbol', 'alerts', ['symbol'])
    op.create_index('ix_alerts_timestamp', 'alerts', ['timestamp'])
    op.create_index('ix_alerts_opportunity_score', 'alerts', ['opportunity_score'])

def downgrade():
    # Drop tables in reverse order
    op.drop_table('alerts')
    op.drop_table('token_analysis')
    op.drop_table('new_tokens')
