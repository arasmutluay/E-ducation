"""empty message

Revision ID: fd17f86413a1
Revises: 6f0d0dba1ba1
Create Date: 2023-12-28 02:25:24.834682

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fd17f86413a1'
down_revision = '6f0d0dba1ba1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('quizzes', schema=None) as batch_op:
        batch_op.drop_column('overall_score')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('quizzes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('overall_score', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))

    # ### end Alembic commands ###
