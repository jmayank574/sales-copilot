"""Manual smoke test: writes one TEST row, then deletes it. Run: python -m tests.smoke_sheets"""
from app import sheets

ws = sheets._worksheet()
sheets.ensure_headers(ws)
print("headers:", ws.row_values(1))

row = {h: "test" for h in sheets.HEADERS}
row["Email"] = "smoke-test@example.com"
print("first append:", sheets.append_lead(row))
print("duplicate append:", sheets.append_lead(row))

cell = ws.find("smoke-test@example.com", in_column=sheets.EMAIL_COL)
ws.delete_rows(cell.row)
print("cleaned up row", cell.row)
