"""empty message

Revision ID: aca4d5680235
Revises: 5611fd404198
Create Date: 2024-01-02 03:48:02.949937

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aca4d5680235'
down_revision = '5611fd404198'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_answers', schema=None) as batch_op:
        batch_op.drop_column('overall_quiz_score')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('overall_quiz_score', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))

    # ### end Alembic commands ###
