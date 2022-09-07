"""empty message

Revision ID: c30b19286ffc
Revises: 
Create Date: 2022-09-03 20:25:01.123189

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c30b19286ffc'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('groups',
    sa.Column('id', sa.VARCHAR(length=255), nullable=False),
    sa.Column('groupname', sa.VARCHAR(length=255), nullable=False),
    sa.Column('title', sa.VARCHAR(length=255), nullable=True),
    sa.Column('description', sa.VARCHAR(length=255), nullable=True),
    sa.Column('page_content', sa.TEXT(length=16383), nullable=True),
    sa.Column('enable_vote', sa.Boolean(), nullable=True),
    sa.Column('twitter_url', sa.VARCHAR(length=255), nullable=True),
    sa.Column('instagram_url', sa.VARCHAR(length=255), nullable=True),
    sa.Column('stream_url', sa.VARCHAR(length=255), nullable=True),
    sa.Column('thumbnail_image_url', sa.VARCHAR(length=255), nullable=True),
    sa.Column('cover_image_url', sa.VARCHAR(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_groups_groupname'), 'groups', ['groupname'], unique=False)
    op.create_index(op.f('ix_groups_id'), 'groups', ['id'], unique=True)
    op.create_table('tags',
    sa.Column('id', sa.VARCHAR(length=255), nullable=False),
    sa.Column('tagname', sa.VARCHAR(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tagname')
    )
    op.create_index(op.f('ix_tags_id'), 'tags', ['id'], unique=True)
    op.create_table('timetable',
    sa.Column('id', sa.VARCHAR(length=255), nullable=False),
    sa.Column('timetablename', sa.VARCHAR(length=255), nullable=True),
    sa.Column('sell_at', sa.DateTime(), nullable=False),
    sa.Column('sell_ends', sa.DateTime(), nullable=False),
    sa.Column('starts_at', sa.DateTime(), nullable=False),
    sa.Column('ends_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_timetable_id'), 'timetable', ['id'], unique=True)
    op.create_table('users',
    sa.Column('id', sa.VARCHAR(length=255), nullable=False),
    sa.Column('username', sa.VARCHAR(length=25), nullable=True),
    sa.Column('hashed_password', sa.VARCHAR(length=255), nullable=True),
    sa.Column('is_student', sa.Boolean(), nullable=True),
    sa.Column('is_family', sa.Boolean(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('password_expired', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_table('admin',
    sa.Column('user_id', sa.VARCHAR(length=255), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_table('authority',
    sa.Column('user_id', sa.VARCHAR(length=255), nullable=False),
    sa.Column('group_id', sa.VARCHAR(length=255), nullable=False),
    sa.Column('role', sa.VARCHAR(length=255), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'group_id', 'role'),
    sa.UniqueConstraint('user_id', 'group_id', 'role', name='unique_idx_groupid_tagid')
    )
    op.create_table('entry',
    sa.Column('user_id', sa.VARCHAR(length=255), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_table('events',
    sa.Column('id', sa.VARCHAR(length=255), nullable=False),
    sa.Column('timetable_id', sa.VARCHAR(length=255), nullable=False),
    sa.Column('ticket_stock', sa.Integer(), nullable=False),
    sa.Column('lottery', sa.Boolean(), nullable=True),
    sa.Column('group_id', sa.VARCHAR(length=255), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
    sa.ForeignKeyConstraint(['timetable_id'], ['timetable.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_id'), 'events', ['id'], unique=True)
    op.create_table('grouptag',
    sa.Column('group_id', sa.VARCHAR(length=255), nullable=False),
    sa.Column('tag_id', sa.VARCHAR(length=255), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
    sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ),
    sa.PrimaryKeyConstraint('group_id', 'tag_id'),
    sa.UniqueConstraint('group_id', 'tag_id', name='unique_idx_groupid_tagid')
    )
    op.create_table('votes',
    sa.Column('group_id', sa.VARCHAR(length=255), nullable=False),
    sa.Column('user_id', sa.VARCHAR(length=255), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('tickets',
    sa.Column('id', sa.VARCHAR(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.Column('group_id', sa.VARCHAR(length=255), nullable=True),
    sa.Column('event_id', sa.VARCHAR(length=255), nullable=True),
    sa.Column('owner_id', sa.VARCHAR(length=255), nullable=True),
    sa.Column('person', sa.Integer(), nullable=True),
    sa.Column('is_family_ticket', sa.Boolean(), nullable=True),
    sa.Column('is_used', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tickets_id'), 'tickets', ['id'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_tickets_id'), table_name='tickets')
    op.drop_table('tickets')
    op.drop_table('votes')
    op.drop_table('grouptag')
    op.drop_index(op.f('ix_events_id'), table_name='events')
    op.drop_table('events')
    op.drop_table('entry')
    op.drop_table('authority')
    op.drop_table('admin')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_timetable_id'), table_name='timetable')
    op.drop_table('timetable')
    op.drop_index(op.f('ix_tags_id'), table_name='tags')
    op.drop_table('tags')
    op.drop_index(op.f('ix_groups_id'), table_name='groups')
    op.drop_index(op.f('ix_groups_groupname'), table_name='groups')
    op.drop_table('groups')
    # ### end Alembic commands ###
