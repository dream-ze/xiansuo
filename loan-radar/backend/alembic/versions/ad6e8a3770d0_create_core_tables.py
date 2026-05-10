"""create_core_tables

Revision ID: ad6e8a3770d0
Revises: ae22605e776e
Create Date: 2026-05-10 15:17:08.827008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ad6e8a3770d0'
down_revision: Union[str, None] = 'ae22605e776e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('post_id', sa.String(length=255), nullable=False),
        sa.Column('comment_id', sa.String(length=255), nullable=False),
        sa.Column('user_name', sa.String(length=255), nullable=True),
        sa.Column('user_profile_url', sa.String(length=1000), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('like_count', sa.Integer(), nullable=False),
        sa.Column('publish_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_suspected_demand', sa.Boolean(), nullable=False),
        sa.Column('demand_type', sa.String(length=100), nullable=True),
        sa.Column('risk_level', sa.String(length=50), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_comments_comment_id'), 'comments', ['comment_id'], unique=False)
    op.create_index(op.f('ix_comments_demand_type'), 'comments', ['demand_type'], unique=False)
    op.create_index(op.f('ix_comments_id'), 'comments', ['id'], unique=False)
    op.create_index(op.f('ix_comments_is_suspected_demand'), 'comments', ['is_suspected_demand'], unique=False)
    op.create_index(op.f('ix_comments_platform'), 'comments', ['platform'], unique=False)
    op.create_index(op.f('ix_comments_post_id'), 'comments', ['post_id'], unique=False)
    op.create_index(op.f('ix_comments_publish_time'), 'comments', ['publish_time'], unique=False)
    op.create_index(op.f('ix_comments_risk_level'), 'comments', ['risk_level'], unique=False)
    op.create_index(op.f('ix_comments_user_name'), 'comments', ['user_name'], unique=False)
    op.create_table(
        'crawl_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('post_count', sa.Integer(), nullable=False),
        sa.Column('comment_count', sa.Integer(), nullable=False),
        sa.Column('lead_count', sa.Integer(), nullable=False),
        sa.Column('discovered_competitor_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_crawl_tasks_id'), 'crawl_tasks', ['id'], unique=False)
    op.create_index(op.f('ix_crawl_tasks_platform'), 'crawl_tasks', ['platform'], unique=False)
    op.create_index(op.f('ix_crawl_tasks_source_id'), 'crawl_tasks', ['source_id'], unique=False)
    op.create_index(op.f('ix_crawl_tasks_source_type'), 'crawl_tasks', ['source_type'], unique=False)
    op.create_index(op.f('ix_crawl_tasks_status'), 'crawl_tasks', ['status'], unique=False)
    op.create_table(
        'daily_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('source_count', sa.Integer(), nullable=False),
        sa.Column('post_count', sa.Integer(), nullable=False),
        sa.Column('comment_count', sa.Integer(), nullable=False),
        sa.Column('lead_count', sa.Integer(), nullable=False),
        sa.Column('a_lead_count', sa.Integer(), nullable=False),
        sa.Column('b_lead_count', sa.Integer(), nullable=False),
        sa.Column('c_lead_count', sa.Integer(), nullable=False),
        sa.Column('d_lead_count', sa.Integer(), nullable=False),
        sa.Column('top_demands', sa.JSON(), nullable=True),
        sa.Column('top_keywords', sa.JSON(), nullable=True),
        sa.Column('hot_posts', sa.JSON(), nullable=True),
        sa.Column('content_suggestions', sa.JSON(), nullable=True),
        sa.Column('follow_up_suggestions', sa.JSON(), nullable=True),
        sa.Column('risk_warnings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_daily_reports_id'), 'daily_reports', ['id'], unique=False)
    op.create_index(op.f('ix_daily_reports_platform'), 'daily_reports', ['platform'], unique=False)
    op.create_index(op.f('ix_daily_reports_report_date'), 'daily_reports', ['report_date'], unique=False)
    op.create_table(
        'leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_post_id', sa.Integer(), nullable=True),
        sa.Column('source_comment_id', sa.Integer(), nullable=True),
        sa.Column('user_name', sa.String(length=255), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('lead_level', sa.String(length=10), nullable=False),
        sa.Column('lead_score', sa.Float(), nullable=False),
        sa.Column('demand_type', sa.String(length=100), nullable=True),
        sa.Column('risk_level', sa.String(length=50), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('follow_up_script', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_leads_demand_type'), 'leads', ['demand_type'], unique=False)
    op.create_index(op.f('ix_leads_id'), 'leads', ['id'], unique=False)
    op.create_index(op.f('ix_leads_lead_level'), 'leads', ['lead_level'], unique=False)
    op.create_index(op.f('ix_leads_platform'), 'leads', ['platform'], unique=False)
    op.create_index(op.f('ix_leads_risk_level'), 'leads', ['risk_level'], unique=False)
    op.create_index(op.f('ix_leads_source_comment_id'), 'leads', ['source_comment_id'], unique=False)
    op.create_index(op.f('ix_leads_source_id'), 'leads', ['source_id'], unique=False)
    op.create_index(op.f('ix_leads_source_post_id'), 'leads', ['source_post_id'], unique=False)
    op.create_index(op.f('ix_leads_source_type'), 'leads', ['source_type'], unique=False)
    op.create_index(op.f('ix_leads_status'), 'leads', ['status'], unique=False)
    op.create_index(op.f('ix_leads_user_name'), 'leads', ['user_name'], unique=False)
    op.create_table(
        'monitor_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('value', sa.String(length=1000), nullable=False),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('last_crawled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_monitor_sources_enabled'), 'monitor_sources', ['enabled'], unique=False)
    op.create_index(op.f('ix_monitor_sources_id'), 'monitor_sources', ['id'], unique=False)
    op.create_index(op.f('ix_monitor_sources_platform'), 'monitor_sources', ['platform'], unique=False)
    op.create_index(op.f('ix_monitor_sources_source_type'), 'monitor_sources', ['source_type'], unique=False)
    op.create_table(
        'pending_competitor_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('account_name', sa.String(length=255), nullable=False),
        sa.Column('profile_url', sa.String(length=1000), nullable=False),
        sa.Column('source_keyword', sa.String(length=255), nullable=True),
        sa.Column('source_post_id', sa.Integer(), nullable=True),
        sa.Column('discover_reason', sa.String(length=1000), nullable=True),
        sa.Column('competitor_score', sa.Float(), nullable=False),
        sa.Column('content_relevance_score', sa.Float(), nullable=False),
        sa.Column('interaction_score', sa.Float(), nullable=False),
        sa.Column('lead_potential_score', sa.Float(), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('recent_post_count', sa.Integer(), nullable=False),
        sa.Column('recent_comment_count', sa.Integer(), nullable=False),
        sa.Column('suspected_lead_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_pending_competitor_accounts_id'), 'pending_competitor_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_pending_competitor_accounts_platform'), 'pending_competitor_accounts', ['platform'], unique=False)
    op.create_index(op.f('ix_pending_competitor_accounts_source_keyword'), 'pending_competitor_accounts', ['source_keyword'], unique=False)
    op.create_index(op.f('ix_pending_competitor_accounts_source_post_id'), 'pending_competitor_accounts', ['source_post_id'], unique=False)
    op.create_index(op.f('ix_pending_competitor_accounts_status'), 'pending_competitor_accounts', ['status'], unique=False)
    op.create_table(
        'posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('post_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('post_url', sa.String(length=1000), nullable=True),
        sa.Column('author_name', sa.String(length=255), nullable=True),
        sa.Column('author_profile_url', sa.String(length=1000), nullable=True),
        sa.Column('like_count', sa.Integer(), nullable=False),
        sa.Column('comment_count', sa.Integer(), nullable=False),
        sa.Column('collect_count', sa.Integer(), nullable=False),
        sa.Column('publish_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_hot', sa.Boolean(), nullable=False),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_posts_author_name'), 'posts', ['author_name'], unique=False)
    op.create_index(op.f('ix_posts_id'), 'posts', ['id'], unique=False)
    op.create_index(op.f('ix_posts_is_hot'), 'posts', ['is_hot'], unique=False)
    op.create_index(op.f('ix_posts_platform'), 'posts', ['platform'], unique=False)
    op.create_index(op.f('ix_posts_post_id'), 'posts', ['post_id'], unique=False)
    op.create_index(op.f('ix_posts_publish_time'), 'posts', ['publish_time'], unique=False)
    op.create_index(op.f('ix_posts_source_id'), 'posts', ['source_id'], unique=False)
    op.create_index(op.f('ix_posts_source_type'), 'posts', ['source_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_posts_source_type'), table_name='posts')
    op.drop_index(op.f('ix_posts_source_id'), table_name='posts')
    op.drop_index(op.f('ix_posts_publish_time'), table_name='posts')
    op.drop_index(op.f('ix_posts_post_id'), table_name='posts')
    op.drop_index(op.f('ix_posts_platform'), table_name='posts')
    op.drop_index(op.f('ix_posts_is_hot'), table_name='posts')
    op.drop_index(op.f('ix_posts_id'), table_name='posts')
    op.drop_index(op.f('ix_posts_author_name'), table_name='posts')
    op.drop_table('posts')
    op.drop_index(op.f('ix_pending_competitor_accounts_status'), table_name='pending_competitor_accounts')
    op.drop_index(op.f('ix_pending_competitor_accounts_source_post_id'), table_name='pending_competitor_accounts')
    op.drop_index(op.f('ix_pending_competitor_accounts_source_keyword'), table_name='pending_competitor_accounts')
    op.drop_index(op.f('ix_pending_competitor_accounts_platform'), table_name='pending_competitor_accounts')
    op.drop_index(op.f('ix_pending_competitor_accounts_id'), table_name='pending_competitor_accounts')
    op.drop_table('pending_competitor_accounts')
    op.drop_index(op.f('ix_monitor_sources_source_type'), table_name='monitor_sources')
    op.drop_index(op.f('ix_monitor_sources_platform'), table_name='monitor_sources')
    op.drop_index(op.f('ix_monitor_sources_id'), table_name='monitor_sources')
    op.drop_index(op.f('ix_monitor_sources_enabled'), table_name='monitor_sources')
    op.drop_table('monitor_sources')
    op.drop_index(op.f('ix_leads_user_name'), table_name='leads')
    op.drop_index(op.f('ix_leads_status'), table_name='leads')
    op.drop_index(op.f('ix_leads_source_type'), table_name='leads')
    op.drop_index(op.f('ix_leads_source_post_id'), table_name='leads')
    op.drop_index(op.f('ix_leads_source_id'), table_name='leads')
    op.drop_index(op.f('ix_leads_source_comment_id'), table_name='leads')
    op.drop_index(op.f('ix_leads_risk_level'), table_name='leads')
    op.drop_index(op.f('ix_leads_platform'), table_name='leads')
    op.drop_index(op.f('ix_leads_lead_level'), table_name='leads')
    op.drop_index(op.f('ix_leads_id'), table_name='leads')
    op.drop_index(op.f('ix_leads_demand_type'), table_name='leads')
    op.drop_table('leads')
    op.drop_index(op.f('ix_daily_reports_report_date'), table_name='daily_reports')
    op.drop_index(op.f('ix_daily_reports_platform'), table_name='daily_reports')
    op.drop_index(op.f('ix_daily_reports_id'), table_name='daily_reports')
    op.drop_table('daily_reports')
    op.drop_index(op.f('ix_crawl_tasks_status'), table_name='crawl_tasks')
    op.drop_index(op.f('ix_crawl_tasks_source_type'), table_name='crawl_tasks')
    op.drop_index(op.f('ix_crawl_tasks_source_id'), table_name='crawl_tasks')
    op.drop_index(op.f('ix_crawl_tasks_platform'), table_name='crawl_tasks')
    op.drop_index(op.f('ix_crawl_tasks_id'), table_name='crawl_tasks')
    op.drop_table('crawl_tasks')
    op.drop_index(op.f('ix_comments_user_name'), table_name='comments')
    op.drop_index(op.f('ix_comments_risk_level'), table_name='comments')
    op.drop_index(op.f('ix_comments_publish_time'), table_name='comments')
    op.drop_index(op.f('ix_comments_post_id'), table_name='comments')
    op.drop_index(op.f('ix_comments_platform'), table_name='comments')
    op.drop_index(op.f('ix_comments_is_suspected_demand'), table_name='comments')
    op.drop_index(op.f('ix_comments_id'), table_name='comments')
    op.drop_index(op.f('ix_comments_demand_type'), table_name='comments')
    op.drop_index(op.f('ix_comments_comment_id'), table_name='comments')
    op.drop_table('comments')
