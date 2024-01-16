"""empty message

Revision ID: 3813da881dca
Revises: 307342330ba3
Create Date: 2023-12-22 06:19:55.642822

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3813da881dca'
down_revision = '307342330ba3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('score', sa.Float(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_answers', schema=None) as batch_op:
        batch_op.drop_column('score')

    # ### end Alembic commands ###
