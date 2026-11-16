import re
from src.drive.ingestion import get_drive_service
from src.classifier import classify_domain

service = get_drive_service()
text = service.files().get_media(fileId="1IkgjpqUCsHkKoryzEKx-bNPo2UZjg9DE").execute().decode("utf-8")

print("notion gate :", bool(re.search(r"[-—–]\s*Notion\s*Notes", text, re.I)))
print("numbered ln :", bool(re.search(r"(?m)^\s*\d+\.\s", text)))
print("LC \\d+      :", bool(re.search(r"\bLC\s*\d+\b", text, re.I)))
print("'Notion' hits:", re.findall(r".{0,15}Notion.{0,15}", text, re.I)[:5])
print("result      :", classify_domain(text))