"""Preserve existing public schema identifiers when internal packages move."""

# These two pre-existing Confirm models need qualified names because they share
# a class name. Keep generated-client identifiers stable across this folder move.
SCHEMA_NAME_ALIASES = {
    "app__modules__functional__bulk_transfer__router__Confirm": "app__modules__bulk_transfer__router__Confirm",
    "app__modules__functional__conversations__router__Confirm": "app__modules__conversations__router__Confirm",
}


def install_schema_compatibility(application) -> None:
    original_openapi = application.openapi

    def compatible_openapi():
        document = original_openapi()
        schemas = document.get("components", {}).get("schemas", {})
        for current, stable in SCHEMA_NAME_ALIASES.items():
            if current in schemas:
                if stable in schemas and schemas[stable] != schemas[current]:
                    raise ValueError("Conflicting public OpenAPI schema identifier")
                schemas[stable] = schemas.pop(current)

        def replace_references(value):
            if isinstance(value, dict):
                reference = value.get("$ref")
                if isinstance(reference, str) and reference.startswith("#/components/schemas/"):
                    name = reference.removeprefix("#/components/schemas/")
                    if name in SCHEMA_NAME_ALIASES:
                        value["$ref"] = "#/components/schemas/" + SCHEMA_NAME_ALIASES[name]
                for item in value.values():
                    replace_references(item)
            elif isinstance(value, list):
                for item in value:
                    replace_references(item)

        replace_references(document)
        return document

    application.openapi = compatible_openapi
