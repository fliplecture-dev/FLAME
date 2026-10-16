"""Authorized delivery of a selected self-contained catalogue simulation."""
from app.contracts.catalogue import suitable_for
from app.core.domain_errors import fail
from app.modules.functional.curriculum.public_paths import describe_browse_path
from app.modules.functional.resources.candidates import eligible_candidates
from app.modules.functional.resources.interactive import interactive_data
from app.modules.functional.resources.models import Resource
from app.modules.functional.resources.storage import ResourceStorage


def open_simulation(db, config, resource_id, *, topic_id, subtopic_id, revision, version, language=None):
    path = describe_browse_path(db, topic_id, subtopic_id)
    if path["curriculum_revision"] != revision:
        fail(409, "curriculum_revision_changed")
    selected = next((item for item in eligible_candidates(db, topic_id, subtopic_id, config)
                     if item.id == resource_id and suitable_for(item, path["grade"], language)), None)
    if selected is None or selected.type != "interactive" or selected.mime_type != "text/html":
        fail(404, "interactive_document_unavailable")
    if selected.version != version:
        fail(409, "explore_version_changed")
    data = interactive_data(db.get(Resource, resource_id), ResourceStorage(config))
    return {"status": "resource", "resource_id": str(resource_id), "title": selected.title,
            "version": selected.version, "html_document": data["html_document"]}
