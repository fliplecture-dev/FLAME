from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
import logging

RESOURCE_ERRORS = {
    "direct_storage_unavailable": ("Private file storage is unavailable. Keep the selected file and retry when storage is available.", "file"),
    "staged_upload_missing": ("The selected file has not reached private storage. Retry the upload.", "file"),
    "upload_ticket_expired_or_invalid": ("The upload authorization expired or is invalid. Select the file and upload again.", "file"),
    "upload_content_mismatch": ("The uploaded bytes do not match the selected file. Select the file again and retry.", "file"),
    "upload_size_mismatch": ("The uploaded file size does not match the selected file.", "file"),
    "upload_content_conflict": ("This upload already contains different bytes. Select the file again.", "file"),
    "upload_target_conflict": ("This upload belongs to a different import target. Select the file again.", "file"),
    "upload_in_progress": ("This file is still being validated. Retry the same upload shortly.", "file"),
    "export_too_large": ("This export exceeds the supported package size. Export the workbook without media.", None),
    "video_thumbnail_required": ("Upload a PNG, JPEG or WebP video thumbnail, save the draft, then publish.", "thumbnail_upload_id"),
    "video_thumbnail_image_required": ("Choose a static PNG, JPEG or WebP image for the video thumbnail.", "thumbnail_upload_id"),
    "video_thumbnail_type_required": ("Thumbnails can be attached only to Video resources.", "thumbnail_upload_id"),
    "curriculum_revision_changed": ("This curriculum changed. Refresh Explore paths, review the latest topic and try again.", None),
    "explore_path_unavailable": ("This learning path is no longer available. Refresh paths and choose a published topic.", None),
    "explore_item_unavailable": ("This item is no longer available for this learning path. Refresh Explore to see current items.", None),
    "explore_version_changed": ("This item changed. Refresh Explore and review its latest version before opening it.", None),
    "external_video_type_required": ("Select Video and use a YouTube/Vimeo URL as the media source.", "type"),
    "external_video_url_invalid": ("Enter a supported HTTPS YouTube or public Vimeo video URL, not iframe HTML, a playlist, a private link or another provider.", "external_url"),
    "external_video_unavailable": ("This video is unavailable or private. Choose a public video that permits embedding; password-protected videos are not supported.", "external_url"),
    "external_video_not_embeddable": ("Embedding is disabled or restricted for this video. Choose a public embeddable video or upload a licensed video.", "external_url"),
    "external_video_verification_failed": ("The video provider could not be verified. Your details are preserved. Check the URL and provider availability, then retry.", "external_url"),
    "external_video_credentials_required": ("Public visibility and embedding need verification before publication. Configure FLAME_RESOURCE_YOUTUBE_API_KEY or FLAME_RESOURCE_VIMEO_API_TOKEN for the selected provider. This does not enable strict student playback.", "external_url"),
    "external_video_strict_playback_blocked": ("This source cannot play in FLAME's strict student mode. Use a licensed uploaded video instead. No external page will be opened.", None),
    "distribution_rights_required": ("Enter a rights basis, rights holder and distribution scope before publishing.", "rights_holder"),
    "rights_reference_required": ("Enter the licence or permission reference before publishing.", "rights_reference"),
    "animation_too_complex": ("This GIF has too many frames or pixels. Use a smaller animation (up to 1,000 frames).", "file"),
    "invalid_resource_sort": ("Choose a supported resource sorting option.", None),
    "resource_delete_confirmation_required": ("Confirm deletion of this specific resource before continuing.", None),
    "alt_text_required": ("Enter an image description before publishing.", "alt_text"),
    "accessibility_note_required": ("Enter captions, a transcript or an accessibility note before publishing.", "caption_or_transcript"),
    "published_path_required": ("Select at least one available path in a published curriculum.", "paths"),
    "resource_paths_unavailable": ("Some selected paths were removed or archived. Refresh paths, keep valid selections and remove or replace unavailable paths.", "paths"),
    "invalid_resource_path": ("The subtopic does not belong to the selected topic, or is no longer available.", "paths"),
    "stale_version": ("Resource changed elsewhere: review the latest version before saving.", None),
    "resource_creation_exists": ("This resource creation already completed. Review the saved draft before making further changes.", None),
    "invalid_image_decision": ("This image is no longer available for the selected answer.", None),
    "resource_type_media_mismatch": ("The uploaded media does not match the resource type.", "type"),
    "resource_unavailable": ("Set availability to Available before publishing.", "availability"),
    "resource_asset_missing": ("The uploaded media is missing. Select a replacement file.", "file"),
    "resource_source_required": ("Upload a media file or enter an approved HTTPS URL.", "file"),
    "resource_storage_unavailable": ("Media storage is unavailable. Retry when storage is available.", "file"),
    "resource_delivery_unavailable": ("Media delivery is unavailable. Try preview again shortly.", None),
    "resource_not_found": ("The resource no longer exists. Review the resource list.", None),
    "upload_not_found": ("The upload is no longer available to this account. Select the file again.", "file"),
    "upload_already_used": ("This upload is already attached to a saved item. Review that item before retrying.", "file"),
    "upload_required": ("Select a valid uploaded media file.", "file"),
    "external_url_required": ("Enter an approved HTTPS URL.", "external_url"),
    "invalid_external_url": ("Enter a valid approved HTTPS URL.", "external_url"),
    "external_host_not_approved": ("This media host is not approved. Upload the media or use an approved host.", "external_url"),
    "interactive_self_contained_required": ("Use a self-contained HTML5 file: inline scripts/styles and embed assets. External files and libraries are not supported.", "file"),
    "interactive_unsupported_element": ("Interactive HTML cannot contain forms, nested frames, objects or embedded pages.", "file"),
    "interactive_navigation_not_allowed": ("Remove automatic navigation from this interactive.", "file"),
    "interactive_utf8_required": ("Save the HTML5 file using UTF-8 encoding.", "file"),
    "interactive_complete_html_required": ("Upload a complete HTML document with html, head and body elements.", "file"),
    "invalid_interactive_document": ("This HTML5 document is invalid.", "file"),
    "interactive_document_size": ("Upload a nonempty HTML5 document up to 2 MiB.", "file"),
    "interactive_media_required": ("Paste or upload HTML5 before publishing this Interactive draft.", "file"),
    "interactive_accessibility_required": ("Add keyboard instructions and an accessibility note before publication.", "accessibility_note"),
    "unsupported_media_format": ("Select a supported file with a matching media type.", "file"),
    "invalid_media_content": ("The file is not valid media in its declared format.", "file"),
    "empty_file": ("Select a nonempty media file.", "file"),
}

B4_CODES = {
    "curriculum_not_found", "level_not_found", "node_not_found", "parent_not_found",
    "unknown_kind", "ancestor_not_found", "ancestor_archived", "node_archived",
    "curriculum_archived", "incomplete_curriculum", "topic_requires_subtopic",
    "published_topic_requires_subtopic", "duplicate_curriculum_code", "duplicate_sibling",
    "version_conflict", "updated_elsewhere", "already_archived", "invalid_level_path", "invalid_subject_path",
    "invalid_domain_path", "invalid_category_path", "invalid_topic_path",
    "invalid_subtopic_path", "subject_requires_level", "domain_requires_subject",
    "category_requires_domain", "topic_requires_domain", "subtopic_requires_topic",
    "membership_not_found", "membership_conflict_retry", "student_not_found",
    "only_curriculum_or_subject_can_hide", "import_not_found", "already_committed",
    "stale_preview", "invalid_preview", "import_cancelled", "replacement_confirmation_mismatch", "subtopic_required", "invalid_rows", "idempotency_conflict",
    "archived_path_conflict", "invalid_workbook", "invalid_filename",
    "unsupported_file_type", "file_too_large", "file_required", "payload_expired",
    "search_term_too_short", "empty_edit", "outcome_only_for_topic",
    "topic_fields_only_for_topic", "category_only_for_topic",
    "session_not_found", "profile_not_found", "account_inactive", "invalid_cursor",
    "session_context_mismatch", "unavailable_context", "activity_context_mismatch",
    "invalid_idempotency_key", "idempotency_key_conflict", "request_in_progress",
    "session_request_in_progress", "request_claim_lost", "account_deletion_unavailable",
    "clarification_expired", "clarification_unavailable", "clarification_not_found",
    "clarification_already_resolved", "clarification_choice_unclear",
    "clarification_id_mismatch", "invalid_clarification", "clarification_reply_out_of_bounds",
    "clarification_choice_required", "topic_resolution_unavailable",
    "daily_limit_reached", "required", "duplicate_row", "value_too_long", "source_path_changed", "duplicate_source_row",
    "source_required", "values_required", "duplicate_existing_path", "invalid_rename", "invalid_review_changes",
    "invalid_review_values", "row_not_found", "sheet_not_mapped", "level_must_match_sheet_mapping", "invalid_page",
    "file_hash_mismatch", "draft_in_use",
}


def error_response(request: Request, status: int, code: str, message: str,
                   retryable: bool = False, headers: dict | None = None):
    return JSONResponse(
        status_code=status,
        content={
            "status": "error",
            "request_id": getattr(request.state, "request_id", None),
            "error": {"code": code, "message": message, "retryable": retryable},
        },
        headers=headers,
    )


def install_error_handlers(app: FastAPI):
    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        from app.modules.functional.bulk_transfer.errors import BulkFailure
        if isinstance(exc, BulkFailure):
            return error_response(request, exc.status_code, "bulk_import_conflict" if exc.status_code == 409 else "bulk_transfer_failed", str(exc.detail), retryable=exc.status_code in (409, 503))
        codes = {404: "not_found", 405: "method_not_allowed",
                 401: "unauthenticated", 403: "forbidden",
                 429: "rate_limited", 503: "dependency_unavailable"}
        detail_code = exc.detail.get("code") if isinstance(exc.detail, dict) else exc.detail
        if detail_code in RESOURCE_ERRORS:
            message, field = RESOURCE_ERRORS[detail_code]
            response = error_response(request, exc.status_code, detail_code, message,
                                      retryable=exc.status_code == 503 or detail_code == "upload_in_progress", headers=exc.headers)
            import json
            content = json.loads(response.body)
            if isinstance(exc.detail, dict) and detail_code == "distribution_rights_required":
                fields = [name for name in exc.detail.get("fields", []) if name in {"rights_basis", "rights_holder", "distribution_scope"}]
                content["error"]["fields"] = fields
                field = fields[0] if fields else field
            if field:
                content["error"]["field"] = field
            if detail_code == "resource_paths_unavailable" and isinstance(exc.detail, dict):
                content["error"]["invalid_paths"] = exc.detail.get("invalid_paths", [])
            logging.getLogger("flame").warning("resource_operation_failed", extra={"fields": {
                "request_id": getattr(request.state, "request_id", None), "code": detail_code,
                "status": exc.status_code, "route": getattr(request.scope.get("route"), "path", "unmatched"),
                "field": field}})
            return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)
        safe_code = detail_code if isinstance(detail_code, str) and detail_code in B4_CODES else None
        response = error_response(
            request, exc.status_code, safe_code or codes.get(exc.status_code, "request_failed"),
            safe_code.replace("_", " ").capitalize() + "." if safe_code else "The request could not be completed.",
            retryable=exc.status_code in (429, 503) or safe_code in
            ("request_in_progress", "session_request_in_progress"), headers=exc.headers,
        )
        if safe_code and isinstance(exc.detail, dict) and (exc.detail.get("row_key") or exc.detail.get("field")):
            import json
            content = json.loads(response.body)
            row_key = exc.detail.get("row_key")
            field = exc.detail.get("field")
            if isinstance(row_key, str) and len(row_key) <= 100:
                content["error"]["row_key"] = row_key
            if field in {"level", "subject", "domain", "category", "topic", "subtopic"}:
                content["error"]["field"] = field
            return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)
        if safe_code in {"stale_preview", "invalid_preview"} and isinstance(exc.detail, dict):
            mismatch = exc.detail.get("revision_mismatch")
            if mismatch in {"import_base_revision", "curriculum_version", "draft_revision", "import_preview_revision"}:
                import json
                content = json.loads(response.body)
                content["error"]["revision_mismatch"] = mismatch
                return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Do not echo input, credentials, or message bodies in errors.
        if request.url.path.startswith("/api/v1/admin/resources"):
            allowed = {"title", "type", "description", "paths", "upload_id", "external_url", "alt_text",
                       "caption_or_transcript", "accessibility_note", "rights_basis", "rights_holder",
                       "rights_reference", "attribution", "distribution_scope", "availability", "file", "expected_version"}
            fields = sorted({str(part) for error in exc.errors() for part in error["loc"] if part in allowed})
            logging.getLogger("flame").warning("resource_validation_failed", extra={"fields": {
                "request_id": getattr(request.state, "request_id", None), "fields": fields,
                "route": getattr(request.scope.get("route"), "path", "unmatched")}})
            return JSONResponse(status_code=422, content={"status": "error",
                "request_id": getattr(request.state, "request_id", None),
                "error": {"code": "validation_error", "message": "Check the highlighted resource fields.",
                          "fields": fields, "retryable": False}})
        return error_response(request, 422, "validation_error",
                              "Request fields are invalid.")


