"""Google Sheets transport and row validation. Catalogue ownership stays in bulk transfer.

Row developer metadata, rather than row numbers or titles, identifies write-back targets.
Only identifier cells are written; arbitrary URLs, media downloads and formulas are not used.
"""
import difflib
import json
import re
from pathlib import Path
from openpyxl.utils import get_column_letter
from uuid import uuid4
import httpx
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.service_account import Credentials
from app.modules.bulk_transfer.errors import fail
from app.modules.bulk_transfer.workbooks import FIELDS
from app.modules.bulk_transfer.service import digest, plan, snapshot, split
from app.modules.resources.models import Resource
from uuid import UUID

TABS = {"Image": "image", "Video": "video", "Interactive": "interactive"}
MARKER = "flame_resource_sync_v1"
IDENTIFIERS = {"record_key", "existing_id"}


class BoundedGoogleRequest(GoogleRequest):
    def __call__(self, *args, **kwargs):
        kwargs["timeout"] = 30
        return super().__call__(*args, **kwargs)


def spreadsheet_id(value):
    value = value.strip()
    match = re.fullmatch(r"https://docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]{20,100})(?:/[^\s]*)?", value)
    if match: return match[1]
    if re.fullmatch(r"[A-Za-z0-9_-]{20,100}", value): return value
    fail(422, "Enter a Google spreadsheet URL or spreadsheet ID.")


def credentials(config):
    if not config.google_sheets_credentials_file:
        fail(503, "Google Sheets is not configured. Set FLAME_GOOGLE_SHEETS_CREDENTIALS_FILE on the API server.")
    try:
        info = json.loads(Path(config.google_sheets_credentials_file).read_text(encoding="utf-8"))
        if info.get("type") != "service_account" or info.get("token_uri") != "https://oauth2.googleapis.com/token":
            raise ValueError()
        return Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    except (OSError, ValueError, KeyError):
        fail(503, "Google service-account configuration is invalid. Ask the server administrator to check it.")


class SheetsClient:
    def __init__(self, config, ident):
        self.ident = spreadsheet_id(ident)
        auth = credentials(config)
        try: auth.refresh(BoundedGoogleRequest())
        except Exception: fail(503, "Google authentication failed. Check the configured service account and retry.")
        self.token = auth.token

    def call(self, method, suffix="", **kwargs):
        try:
            with httpx.stream(method, "https://sheets.googleapis.com/v4/spreadsheets/" + self.ident + suffix,
                headers={"Authorization": "Bearer " + self.token}, timeout=30, follow_redirects=False, **kwargs) as response:
                if response.status_code in (401, 403, 404):
                    fail(422, "Google spreadsheet is unavailable. Enable the Sheets API and share this spreadsheet with the service account as Editor.")
                if response.status_code == 429: fail(503, "Google Sheets quota reached. Retry later; existing FLAME records are retained.")
                if response.status_code != 200: fail(503, "Google Sheets request failed. Retry or check spreadsheet permissions.")
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 12 * 1024 * 1024: fail(413, "Google spreadsheet response exceeds 12 MiB. Use smaller batches.")
                return json.loads(data)
        except (httpx.HTTPError, ValueError): fail(503, "Google Sheets could not be reached. Retry without changing your existing catalogue.")

    def read(self):
        book = self.call("GET", params={"fields": "sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)))"})
        self.grid_rows={x['properties']['sheetId']:x['properties'].get('gridProperties',{}).get('rowCount',1000) for x in book.get('sheets',[])}
        columns={x['properties']['title']:x['properties'].get('gridProperties',{}).get('columnCount',60) for x in book.get('sheets',[])}
        self.grid_columns={x['properties']['sheetId']:columns[x['properties']['title']] for x in book.get('sheets',[])}
        if any(columns.get(n,0)>60 for n in TABS):fail(413,'Resource tabs must have at most 60 columns. Remove extra columns before syncing; nothing was changed.')
        names = {x["properties"]["title"]: x["properties"]["sheetId"] for x in book.get("sheets", [])}
        # Read all used rows before enforcing the 2,000-row limit. A truncated range
        # must never make a moved row look deleted in a connected spreadsheet.
        ranges = [("ranges", "'" + name + "'!A:"+get_column_letter(columns[name])) for name in TABS if name in names]
        values = self.call("GET", "/values:batchGet", params=ranges + [("valueRenderOption", "FORMULA")]) if ranges else {}
        grids = {name: item.get("values", []) for name, item in zip((n for n in TABS if n in names), values.get("valueRanges", []))}
        markers = {};groups={};self.tracking_cleanup=[]
        metadata = self.call("POST", "/developerMetadata:search", json={"dataFilters": [{"developerMetadataLookup": {"metadataKey": MARKER, "locationType": "ROW"}}]})
        for match in metadata.get("matchedDeveloperMetadata", []):
            item = match["developerMetadata"]
            loc = item.get("location", {}).get("dimensionRange", {})
            if item.get("metadataKey") == MARKER and loc.get("dimension") == "ROWS" and loc.get("endIndex") == loc.get("startIndex", -1) + 1:
                key = (loc["sheetId"], loc["startIndex"] + 1)
                groups.setdefault(key,[]).append(item)
        for key,items in groups.items():
            if len(items)==1:markers[key]=items[0];continue
            bindings=getattr(self,'bindings',{})
            tab=next((n for n,s in names.items() if s==key[0]),None)
            grid=grids.get(tab,[]);raw=dict(zip(grid[0],grid[key[1]-1])) if grid and key[1]<=len(grid) else {}
            same=len({m['metadataValue'] for m in items})==1
            candidates=items if same else [m for m in items if (b:=bindings.get(m['metadataValue'])) and
                (raw.get('existing_id') and str(raw['existing_id'])==b['resource_id'] or raw.get('record_key') and str(raw['record_key'])==b['record_key'])]
            if not candidates or len({m['metadataValue'] for m in candidates})!=1 or (not same and any(m['metadataValue'] not in bindings for m in items)):
                fail(409,'Duplicate FLAME tracking cannot be resolved safely. Restore the row identifiers or undo the row edit, then validate again. No resources were deleted.')
            winner=min(candidates,key=lambda m:m['metadataId']);markers[key]=winner
            self.tracking_cleanup.extend(m['metadataId'] for m in items if m['metadataId']!=winner['metadataId'])
        self.tracking_cleanup.sort()
        return names, grids, markers

    def mark(self, requests):
        if not requests: return {}
        response = self.call("POST", ":batchUpdate", json={"requests": [{"createDeveloperMetadata": {"developerMetadata": x}} for x in requests]})
        return {x["createDeveloperMetadata"]["developerMetadata"]["metadataValue"]: x["createDeveloperMetadata"]["developerMetadata"]["metadataId"] for x in response["replies"]}


def collect(names, grids, markers, *, reserve=False, namespace=""):
    """Return row-specific issues before planning; never silently drop unknown columns."""
    records, refs, issues, requests = [], [], [], []
    allowed = set(FIELDS["resources"]) | {"published", "version", "status", "sync_action"}
    used_keys, used_markers = set(), set()
    for tab, media_type in TABS.items():
        def issue(level, column, message, row=1):
            issues.append({"severity": level, "tab": tab, "row": row, "column": column, "message": message})
        if tab not in names:
            issue("error", "", "Required tab is missing. Add a tab named " + tab + "."); continue
        grid = grids.get(tab, [])
        headers = [str(x).strip() for x in (grid[0] if grid else [])]
        while headers and not headers[-1]: headers.pop()
        header_errors = False
        for h in headers:
            if h not in allowed or headers.count(h) > 1:
                suggestion = difflib.get_close_matches(h, sorted(allowed), n=1, cutoff=.55)
                issue("error", h, "Duplicate column." if headers.count(h) > 1 else "Unknown column. " + ("Expected " + suggestion[0] + "." if suggestion else "Use the FLAME template column names.")); header_errors = True
        for h in ["record_key", "existing_id", "title"]:
            if h not in headers: issue("error", h, "Required column is missing. Identifier columns may contain blank cells."); header_errors = True
        missing = sorted(allowed - set(headers) - {"published", "version", "status", "type", "sync_action"})
        if missing: issue("warning", "", "Optional columns missing: " + ", ".join(missing))
        if len(grid) > 2001: issue("error", "", "Tab exceeds 2,000 data rows."); header_errors = True
        if header_errors: continue
        for number, cells in enumerate(grid[1:], 2):
            if not any(x not in (None, "") for x in cells): continue
            if len(records) >= 2000: fail(413, "Sync is limited to 2,000 records across all three tabs.")
            raw = {h: c for h, c in zip(headers, cells) if c not in (None, "")}
            row_errors = []
            if any(c not in (None, "") for c in cells[len(headers):]): row_errors.append("Data has no column heading.")
            if any(isinstance(c, str) and c.startswith("=") for c in cells): row_errors.append("Formulas are not accepted; paste plain values.")
            if raw.get("type") and raw["type"] != media_type: row_errors.append("type must be " + media_type + " in this tab.")
            raw["type"] = media_type
            marker = markers.get((names[tab], number))
            value = marker["metadataValue"] if marker else uuid4().hex if reserve else None
            if not value: fail(409, "Sheet tracking changed. Start a fresh sync preview.")
            if value in used_markers: fail(409, "Duplicate FLAME row tracking. Do not copy row metadata between resources.")
            used_markers.add(value)
            key = str(raw.get("record_key") or "gs-" + digest([namespace, value])[:32]).strip()
            if key in used_keys: row_errors.append("Duplicate record_key in this spreadsheet; each resource row needs its own key.")
            used_keys.add(key)
            source = dict(raw)
            raw["record_key"] = key; raw["_row"] = len(records) + 2
            records.append(raw)
            refs.append({"tab": tab, "row": number, "sheet_id": names[tab], "marker": value,
                "metadata_id": marker["metadataId"] if marker else None, "headers": headers, "source": source,
                "record_key": key, "errors": row_errors})
            if marker is None:
                requests.append({"metadataKey": MARKER, "metadataValue": value, "visibility": "DOCUMENT",
                    "location": {"dimensionRange": {"sheetId": names[tab], "dimension": "ROWS", "startIndex": number - 1, "endIndex": number}}})
    return records, refs, issues, requests


def sheet_plan(db, config, payload):
    from app.modules.bulk_transfer.sheet_lifecycle import lifecycle_entries
    normal,special=lifecycle_entries(db,payload)
    review = plan(db, config, "resources", {**payload,'records':normal}) if normal else {'entries':[],'counts':{},'total':0}
    entries={e['row']:e for e in review['entries']};entries.update(special)
    review['entries']=[entries[r['_row']] for r in payload['records']];review['total']=len(review['entries'])
    for entry, ref, raw in zip(review["entries"], payload["sheets"]["rows"], payload["records"]):
        entry["tab"] = ref["tab"]; entry["sheet_row"] = ref["row"]
        if entry['operation'] in ('delete','retired'):continue
        errors = list(ref["errors"])
        if raw.get("file"): errors.append("Local files cannot be read from Google Sheets. Upload media in FLAME or use Excel/ZIP import; leave file blank for retained media.")
        if raw["type"] == "interactive" and raw.get("external_url"): errors.append("Paste or upload HTML5 in FLAME after syncing the Interactive draft; leave external_url blank.")
        if errors: entry["errors"] = entry.get("errors", []) + errors; entry["operation"] = "invalid"
        conflicts = []
        if entry.get("existing_id"):
            before = snapshot(db, "resources", db.get(Resource, UUID(entry["existing_id"])))
            if before.get('type')!=raw.get('type'):
                entry['errors']=entry.get('errors',[])+['This existing resource has a different media type. Move it to the matching Image, Video or Interactive tab.']
                entry['operation']='invalid'
            for field in entry.get("preserved_fields", []):
                if field in raw and raw[field] not in (None, "") and before.get(field) not in (None, "", []):
                    incoming = split(raw[field]) if isinstance(before[field], list) else raw[field]
                    if incoming != before[field]: conflicts.append(field)
            for field in ("external_url", "type", "availability"):
                incoming = entry.get("body", {}).get(field)
                if raw.get(field) not in (None, "") and before.get(field) not in (None, "") and incoming != before[field]:
                    conflicts.append(field)
            old_metadata = before.get("learning_metadata", {})
            incoming_metadata = entry.get("body", {}).get("learning_metadata", {})
            for column, field in [("topic", "topic_labels"), ("concepts", "concepts"), ("synonyms", "synonyms"), ("teaching_languages", "languages"), ("purposes", "purposes"), ("grade_min", "grade_min"), ("grade_max", "grade_max")]:
                if column in raw and old_metadata.get(field) not in (None, "", []) and incoming_metadata.get(field) != old_metadata[field] and (before.get("published") or field in {"grade_min", "grade_max"}):
                    conflicts.append(column)
        entry["conflicts"] = conflicts
    review["counts"] = {op: sum(e["operation"] == op for e in review["entries"]) for op in ("add", "merge", "unchanged", "invalid")}
    from app.modules.bulk_transfer.sheet_connector import augment_review
    return augment_review(db,payload['sheets'],review)


def recheck(client, source, ids=None):
    """Locate current rows by marker and compare contents before commit/write-back."""
    names, grids, markers = client.read()
    by_value = {m["metadataValue"]: (sheet, row, m) for (sheet, row), m in markers.items()}
    if len(by_value) != len(markers): fail(409, "Duplicate FLAME row markers. Resolve the sheet conflict before retrying.")
    result = []
    for ref in source["rows"]:
        located = by_value.get(ref["marker"])
        if not located or located[0] != ref["sheet_id"]: fail(409, "A source row was removed or moved to another tab. Start a new preview; FLAME records are retained.")
        sheet, row, meta = located
        if names.get(ref["tab"]) != sheet: fail(409, "A source tab changed. Restore it or start a new preview.")
        grid = grids[ref["tab"]]; headers = [str(x).strip() for x in grid[0]]
        while headers and not headers[-1]: headers.pop()
        if headers != ref["headers"] or row > len(grid): fail(409, "Sheet columns or rows changed. Review a fresh preview before continuing.")
        current = {h: c for h, c in zip(headers, grid[row - 1]) if c not in (None, "")}
        original = ref["source"]
        # type is inferred when absent in the sheet.
        current.setdefault("type", TABS[ref["tab"]])
        if digest({k:v for k,v in current.items() if k not in IDENTIFIERS}) != digest({k:v for k,v in original.items() if k not in IDENTIFIERS}):
            fail(409, "A source row changed after preview. Start a new preview; saved FLAME data is retained.")
        expected = {"record_key": ref["record_key"], "existing_id": ids.get(ref["record_key"]) if ids else original.get("existing_id")}
        for field in IDENTIFIERS:
            if current.get(field) not in (original.get(field), expected[field]): fail(409, "A source identifier changed. Resolve the row conflict before retrying.")
        result.append((ref, meta["metadataId"]))
    return result


def writeback(client, source, ids):
    rows = recheck(client, source, ids)
    data = []
    for ref, metadata_id in rows:
        values = [None] * len(ref["headers"])
        values[ref["headers"].index("record_key")] = ref["record_key"]
        values[ref["headers"].index("existing_id")] = ids[ref["record_key"]]
        data.append({"dataFilter": {"developerMetadataLookup": {"metadataId": metadata_id}}, "majorDimension": "ROWS", "values": [values]})
    result = client.call("POST", "/values:batchUpdateByDataFilter", json={"valueInputOption": "RAW", "data": data})
    if result.get("totalUpdatedCells") != len(data) * 2:
        fail(409, "Google did not confirm every identifier cell. Retry write-back; existing FLAME resources are retained.")
