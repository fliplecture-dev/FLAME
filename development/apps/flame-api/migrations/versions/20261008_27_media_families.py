"""Three active media families; retain original classifications for rollback."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = "20261008_27"
down_revision = "20261007_26"
branch_labels = depends_on = None


def upgrade():
    op.add_column("resources", sa.Column("legacy_media", JSONB()), schema="flame")
    op.execute("""UPDATE flame.resources SET legacy_media = jsonb_build_object(
        'type', type, 'published', published, 'availability', availability)
        WHERE type IN ('diagram', 'animation', 'external_video', 'audio')""")
    op.execute("UPDATE flame.resources SET type = 'image' WHERE type = 'diagram'")
    op.execute("UPDATE flame.resources SET type = 'video' WHERE type IN ('animation', 'external_video')")
    # Retain historical audio IDs, files and mappings; no new audio publication.
    op.execute("UPDATE flame.resources SET published = false, availability = 'unavailable' WHERE type = 'audio'")
    op.execute("UPDATE flame.resource_uploads SET media_type = 'video' WHERE media_type = 'animation'")
    op.create_check_constraint(op.f("ck_resources_media_family"), "resources",
        "type IN ('image', 'video', 'interactive') OR (type = 'audio' AND legacy_media IS NOT NULL AND NOT published AND availability = 'unavailable')", schema="flame")


def downgrade():
    op.drop_constraint(op.f("ck_resources_media_family"), "resources", type_="check", schema="flame")
    # Preserve edits made after upgrade; restore classifications from current source.
    op.execute("UPDATE flame.resources SET type = 'external_video' WHERE type = 'video' AND external_video IS NOT NULL")
    op.execute("UPDATE flame.resources SET type = 'animation' WHERE type = 'video' AND (mime_type = 'image/gif' OR legacy_media->>'type' = 'animation')")
    op.execute("UPDATE flame.resources SET type = 'diagram' WHERE type = 'image' AND legacy_media->>'type' = 'diagram'")
    op.execute("""UPDATE flame.resources SET published = (legacy_media->>'published')::boolean,
        availability = legacy_media->>'availability' WHERE type = 'audio' AND legacy_media IS NOT NULL AND deleted_at IS NULL""")
    op.execute("UPDATE flame.resource_uploads SET media_type = 'animation' WHERE mime_type = 'image/gif'")
    op.drop_column("resources", "legacy_media", schema="flame")
