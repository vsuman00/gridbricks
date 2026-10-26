"""Create raw lineage, observations, import journals and immutable membership."""

from alembic import op

from gridbricks.storage.models import metadata

revision = "0001_snapshots"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    metadata.create_all(op.get_bind())


def downgrade():
    metadata.drop_all(op.get_bind())
