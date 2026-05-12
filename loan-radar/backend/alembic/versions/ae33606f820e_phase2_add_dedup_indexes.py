"""phase2_add_dedup_indexes

Revision ID: ae33606f820e
Revises: ad6e8a3770d0
Create Date: 2026-05-12 10:00:00.000000

添加去重索引：
- posts (platform, post_id) 复合唯一索引
- comments (platform, comment_id) 复合唯一索引
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ae33606f820e'
down_revision: Union[str, None] = 'ad6e8a3770d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 posts 表的复合唯一索引
    op.create_index(
        'ix_posts_platform_post_id_unique',
        'posts',
        ['platform', 'post_id'],
        unique=True,
    )
    
    # 添加 comments 表的复合唯一索引
    op.create_index(
        'ix_comments_platform_comment_id_unique',
        'comments',
        ['platform', 'comment_id'],
        unique=True,
    )


def downgrade() -> None:
    # 删除复合唯一索引
    op.drop_index('ix_comments_platform_comment_id_unique', table_name='comments')
    op.drop_index('ix_posts_platform_post_id_unique', table_name='posts')
