"""Authoring assistance for resource templates; import validation remains authoritative."""
from openpyxl.comments import Comment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import PatternFill

NOTES = {
 "record_key":("Leave blank for new resources; FLAME generates it. Preserve existing keys when syncing again.","gs-0123456789abcdef"),
 "existing_id":("Leave blank for new resources. Preserve the FLAME UUID written back or exported for existing resources.","35017360-0926-4621-8eb0-bdbe9fe602b6"),
 "title":("Required: descriptive resource title, 1–255 characters.","How clouds form"),
 "topic":("Optional grouping labels; separate with |. These labels do not create curriculum mappings. Up to 20 labels, 255 characters each.","Weather | Clouds"),
 "type":("Use image, video or interactive. In Google sync it must match the tab. Diagrams belong to image; animations and external videos belong to video.","video"),
 "external_url":("HTTPS supported source URL. Video can use YouTube/Vimeo. Other URLs require the server allowlist. Leave blank to retain existing media; Interactive sync drafts should leave this blank and add HTML in FLAME.","https://www.youtube.com/watch?v=IBedXUq0oVo"),
 "file":("Excel/ZIP only: relative media path under assets/. Leave blank for Google sync; it cannot read local files. Interactive drafts may omit HTML.","assets/clouds.png"),
 "description":("Explain what this teaches; up to 2,000 characters.","Shows water droplets collecting to form clouds."),
 "alt_text":("Accessible description of the image, not its filename; up to 1,000 characters.","Water vapour cools into droplets above a lake."),
 "caption_or_transcript":("Captions or transcript for video; up to 10,000 characters. Publication rules still apply.","Warm water evaporates and rises into the air."),
 "accessibility_note":("Accessibility information or keyboard instructions; up to 1,000 characters.","Use Tab to reach controls and Enter to activate."),
 "rights_basis":("Select owned, licensed or permission only when verified. Leave blank for an unreviewed draft.","owned"),
 "rights_holder":("Owner or licensor name; up to 255 characters.","FlipLecture"),
 "rights_reference":("Licence/permission reference or URL; up to 2,048 characters. Required for licensed/permission publication.","https://example.org/licence"),
 "attribution":("Required credit text from the rights holder; up to 2,000 characters.","Illustration by FlipLecture"),
 "distribution_scope":("Approved audience/distribution scope; up to 255 characters.","members"),
 "availability":("available or unavailable. This does not publish the resource.","available"),
 "concepts":("Up to 20 concept terms, 80 characters each; separate with |.","clouds | condensation | water droplets"),
 "synonyms":("Up to 40 alternative terms, 80 characters each; separate with |.","cloud formation | water vapour"),
 "grade_min":("Starting grade: integer 0–12; 0 means KG. Fill both grade fields or leave both blank; starting grade must not exceed ending grade.","1"),
 "grade_max":("Ending grade: integer 0–12; 0 means KG. Fill both grade fields or leave both blank.","3"),
 "teaching_languages":("Language codes, up to 10; separate with |. Leave blank if unknown.","en | ta"),
 "purposes":("Allowed values: explain, demonstrate, practise, human_help. Separate multiple values with |, not commas. Optional.","explain | demonstrate"),
 "published":("Informational only. Import/sync never publishes new rows or changes publication status.","FALSE"),
 "version":("Informational FLAME version; do not change it to force an update.","3"),
 "status":("Informational only: draft, published or deleted. Use sync_action=delete to request deletion in Google Sheets. New imports remain drafts.","draft"),
 "sync_action":("Google Sheets: blank/sync keeps the resource. Set delete to request reviewed deletion while preserving key/ID. FLAME writes deleted after completion; do not use deleted to request deletion.","delete"),
}
LIMITS={"record_key":255,"title":255,"description":2000,"external_url":2048,"alt_text":1000,"caption_or_transcript":10000,"accessibility_note":1000,"rights_holder":255,"rights_reference":2048,"attribution":2000,"distribution_scope":255}


def resource_guidance(sheet, media_type=None):
    columns={cell.value:cell.column_letter for cell in sheet[1]}
    def add(field,kind,formula,formula2=None):
        dv=DataValidation(type=kind,formula1=formula,formula2=formula2,allow_blank=True)
        dv.errorTitle="Check "+field;dv.error="Use the allowed values. Read the column header note for instructions and examples."
        dv.promptTitle=field;dv.prompt=NOTES[field][0][:255];dv.showErrorMessage=True;dv.errorStyle="stop";dv.showInputMessage=True
        if kind=="list":dv.showDropDown=False
        sheet.add_data_validation(dv);dv.add(f'{columns[field]}2:{columns[field]}2001')
    for field,col in columns.items():
        if field not in NOTES:continue
        instruction,example=NOTES[field]
        if field=="type" and media_type:instruction=f'This tab accepts only {media_type}. Leave blank to infer the tab type.';example=media_type
        sheet[f'{col}1'].comment=Comment(instruction+'\n\nExample: '+example,"FLAME")
        if field in LIMITS:
            formula=f'AND(LEN({col}2)<={LIMITS[field]},LEFT({col}2,1)<>"=")'
            if field=="title":formula=f'AND(LEN(TRIM({col}2))>0,{formula})'
            add(field,"custom",formula)
    for field,values in {"type":media_type or "image,video,interactive","rights_basis":"owned,licensed,permission","availability":"available,unavailable","published":"TRUE,FALSE","status":"draft,published,deleted","sync_action":"sync,delete,deleted"}.items():
        if field in columns:add(field,"list",'"'+values+'"')
    if "external_url" in columns:
        col=columns['external_url']
        # Replace the length rule with a combined URL/length rule, avoiding overlapping validations.
        sheet.data_validations.dataValidation=[dv for dv in sheet.data_validations.dataValidation if str(dv.sqref)!=f'{col}2:{col}2001']
        add("external_url","custom",f'OR({col}2="",AND(LEFT({col}2,8)="https://",LEN({col}2)<=2048,ISERROR(SEARCH(" ",{col}2))))')
    for field in ("grade_min","grade_max"):
        if field in columns:
            col=columns[field];other=columns.get("grade_max" if field=="grade_min" else "grade_min")
            order=f',OR(${other}2="",{col}2{"<=" if field=="grade_min" else ">="}${other}2)' if other else ''
            add(field,"custom",f'OR({col}2="",AND(ISNUMBER({col}2),{col}2=INT({col}2),{col}2>=0,{col}2<=12{order}))')
    if 'grade_min' in columns and 'grade_max' in columns:
        lo,hi=columns['grade_min'],columns['grade_max']
        rule=FormulaRule(formula=[f'OR(AND(${lo}2="",${hi}2<>""),AND(${lo}2<>"",${hi}2=""),AND(ISNUMBER(${lo}2),ISNUMBER(${hi}2),${lo}2>${hi}2))'],fill=PatternFill('solid',fgColor='FFF0CC'))
        sheet.conditional_formatting.add(f'{lo}2:{hi}2001',rule)
    if 'version' in columns:add('version','whole','1','2147483647');sheet.data_validations.dataValidation[-1].operator='between'
    if 'existing_id' in columns:
        col=columns['existing_id']
        add('existing_id','custom',f'OR({col}2="",AND(LEN({col}2)=36,MID({col}2,9,1)="-",MID({col}2,14,1)="-",MID({col}2,19,1)="-",MID({col}2,24,1)="-"))')
    for field,maximum,length in [('topic',20,5119),('concepts',20,1619),('synonyms',40,3239),('teaching_languages',10,255)]:
        if field in columns:
            col=columns[field]
            add(field,'custom',f'OR({col}2="",AND(LEFT({col}2,1)<>"=",LEN({col}2)<={length},LEN({col}2)-LEN(SUBSTITUTE({col}2,"|",""))<{maximum}))')
    if 'purposes' in columns:
        col=columns['purposes'];expression=f'("|"&SUBSTITUTE({col}2," ","")&"|")'
        for value in ('explain','demonstrate','practise','human_help'):expression=f'SUBSTITUTE({expression},"|{value}|","|")'
        add('purposes','custom',f'OR({col}2="",{expression}="|")')
