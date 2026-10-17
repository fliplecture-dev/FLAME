"""SQL-paged independent browsing; no model calls or teaching-topic requirement."""
from sqlalchemy import String, case, cast, func, literal, or_, select
from app.core.domain_errors import fail
from app.modules.functional.discovery.models import CatalogueEntry
from app.modules.functional.teachers.models import Teacher, TeacherExpertise
from app.modules.functional.activity_kits.models import ActivityKit, KitTopic
from app.modules.functional.curriculum.models import Subject, Domain, Topic, Level, Curriculum

FACETS = ("category", "subject", "level", "language", "format", "author", "location")
CATEGORIES = {"books": ["Academic", "Reference", "Storybooks", "Activity books"],
              "classes": ["Academic", "Languages", "Creative", "Technology"]}


def subjects_for(kind):
    if kind == "teachers":
        query = select(TeacherExpertise.teacher_id.label("owner_id"), Subject.name.label("subject")).join(Subject, Subject.id == TeacherExpertise.subject_id)
    else:
        query = select(KitTopic.kit_id.label("owner_id"), Subject.name.label("subject")).join(Topic, Topic.id == KitTopic.topic_id).join(Domain, Domain.id == Topic.domain_id).join(Subject, Subject.id == Domain.subject_id).where(Topic.archived.is_(False), Domain.archived.is_(False))
    return query.join(Level, Level.id == Subject.level_id).join(Curriculum, Curriculum.id == Level.curriculum_id).where(Subject.archived.is_(False), Level.archived.is_(False), Curriculum.state == "published").subquery()


def source(kind):
    if kind not in ("books", "classes", "teachers", "kits"):
        fail(422, "invalid_catalogue_kind")
    if kind in ("books", "classes"):
        model = CatalogueEntry
        columns = {name: getattr(model, name) for name in FACETS}
        title, description, price, currency = model.title, model.description, model.price, model.currency
        languages = None
    else:
        model = Teacher if kind == "teachers" else ActivityKit
        metadata = model.learning_metadata
        languages = model.languages if kind == "teachers" else metadata["languages"]
        columns = {name: literal(None, String) for name in FACETS}
        columns.update(category=metadata["topic_labels"][0].astext,
                       language=languages[0].astext)
        subjects = subjects_for(kind)
        columns["subject"] = select(func.string_agg(func.distinct(subjects.c.subject), ", ")).where(subjects.c.owner_id == model.id).correlate(model).scalar_subquery()
        grade_min, grade_max = metadata["grade_min"].astext, metadata["grade_max"].astext
        columns["level"] = case((grade_min.is_(None), literal(None, String)), (grade_min == grade_max, func.concat("Grade ", grade_min)), else_=func.concat("Grades ", grade_min, "–", grade_max))
        title = model.name
        description = model.bio if kind == "teachers" else model.description
        price = literal(None) if kind == "teachers" else model.cost
        currency = literal(None, String) if kind == "teachers" else model.currency
    fields = dict(id=model.id, title=title, description=description, version=model.version,
                  availability=model.availability, price=price, currency=currency, **columns)
    fields["schedule"] = model.schedule if kind in ("books", "classes") else literal(None, String)
    if languages is not None:
        fields["languages"] = languages
    return model, fields, languages


def public_data(row, kind):
    result = dict(row)
    result["id"] = str(result["id"])
    result["kind"] = kind
    result["price"] = str(result["price"]) if result["price"] is not None else None
    return result


def search(session, kind, query="", filters=None, offset=0, limit=24, sort="title", admin=False):
    model, fields, languages = source(kind)
    clauses = [] if admin else [model.published.is_(True)]
    if kind in ("books", "classes"):
        clauses.append(model.kind == kind)
    inventory_total = session.scalar(select(func.count()).select_from(model).where(*clauses))
    if inventory_total == 0:
        return dict(items=[], total=0, inventory_total=0, facets={name: CATEGORIES.get(kind, []) if name == "category" else [] for name in FACETS}, offset=offset, limit=limit)
    facets = {}
    for name in FACETS:
        expression = fields[name]
        if name == "subject" and kind in ("teachers", "kits"):
            subjects = subjects_for(kind)
            values = session.scalars(select(subjects.c.subject).where(subjects.c.owner_id.in_(select(model.id).where(*clauses))).distinct().order_by(subjects.c.subject).limit(100)).all()
            facets[name] = [value for value in values if value]
            continue
        if name == "category" and kind in ("teachers", "kits"):
            expression = func.jsonb_array_elements_text(model.learning_metadata["topic_labels"])
        if name == "language" and languages is not None:
            expression = func.jsonb_array_elements_text(languages)
        values = session.scalars(select(expression).select_from(model).where(*clauses).distinct().order_by(expression).limit(100)).all()
        facets[name] = [value for value in values if value]
    if kind in CATEGORIES:
        facets["category"] = sorted(set(facets["category"]) | set(CATEGORIES[kind]))
    if query.strip():
        # Escape LIKE metacharacters: student input is a literal search, never a wildcard instruction.
        pattern = "%" + query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        expressions = [fields[name] for name in ("title", "description", "author", "category", "subject")]
        if kind in ("teachers", "kits"):
            expressions.append(cast(model.learning_metadata["topic_labels"], String))
        clauses.append(or_(*(expression.ilike(pattern, escape="\\") for expression in expressions)))
    for name, value in (filters or {}).items():
        if name in FACETS and value:
            if name == "subject" and kind in ("teachers", "kits"):
                subjects = subjects_for(kind)
                clauses.append(model.id.in_(select(subjects.c.owner_id).where(subjects.c.subject == value)))
            elif name == "category" and kind in ("teachers", "kits"):
                clauses.append(model.learning_metadata["topic_labels"].contains([value]))
            else:
                clauses.append(languages.contains([value]) if name == "language" and languages is not None else fields[name] == value)
    total = session.scalar(select(func.count()).select_from(model).where(*clauses))
    order = [model.created_at.desc(), model.id] if sort == "newest" else [func.lower(fields["title"]), model.id]
    rows = session.execute(select(*(column.label(name) for name, column in fields.items())).where(*clauses).order_by(*order).offset(offset).limit(limit)).mappings().all()
    return dict(items=[public_data(row, kind) for row in rows], total=total, inventory_total=inventory_total,
                facets=facets, offset=offset, limit=limit)


def detail(session, kind, item_id, version=None):
    model, fields, _ = source(kind)
    clauses = [model.id == item_id, model.published.is_(True)]
    if kind in ("books", "classes"):
        clauses.append(model.kind == kind)
    if version is not None:
        clauses.append(model.version == version)
    row = session.execute(select(*(column.label(name) for name, column in fields.items())).where(*clauses)).mappings().first()
    if row is None:
        fail(404, "catalogue_item_unavailable")
    return public_data(row, kind)
