#!/usr/bin/env python3
# Creates sample evidence files of different types in the folder given as argument.
import os, sys, zlib, struct, random, zipfile, json

out = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(os.path.join(out, "Confidential"), exist_ok=True)
p = lambda *a: os.path.join(out, *a)

# 1. Plain text (small, stays inside the MFT record)
with open(p("secret.txt"), "w") as f:
    f.write("Meeting with supplier on Friday 10:00.\nAccount: 4471-2290\nDo not share.\n")

# 2. CSV
with open(p("Confidential", "passwords.csv"), "w") as f:
    f.write("system,username,password\n")
    for i in range(60):
        f.write(f"server{i:02d},admin{i:02d},P@ss-{random.Random(i).randint(100000,999999)}\n")

# 3. PDF (valid single-page PDF built by hand)
lines = ["CONFIDENTIAL REPORT", "Project Falcon - Q3 financial summary",
         "Revenue: 1,250,000   Costs: 980,000", "Prepared by: J. Smith"]
lines += [f"Line {i:03d}: internal ledger entry for audit trail" for i in range(1, 60)]
text = "BT /F1 11 Tf 50 800 Td 14 TL " + " ".join(f"({l}) Tj T*" for l in lines) + " ET"
objs = ["<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(text)} >>\nstream\n{text}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
pdf = b"%PDF-1.4\n"; offs = []
for i, o in enumerate(objs, 1):
    offs.append(len(pdf)); pdf += f"{i} 0 obj\n{o}\nendobj\n".encode()
xref = len(pdf)
pdf += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
pdf += b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
pdf += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
open(p("report.pdf"), "wb").write(pdf)

# 4. PNG image (gradient with noise)
w, h = 320, 240; rnd = random.Random(7); raw = b""
for y in range(h):
    raw += b"\x00" + bytes(v for x in range(w) for v in
        ((x * 255 // w), (y * 255 // h), (rnd.randint(0, 255))))
def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) \
      + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
open(p("photo.png"), "wb").write(png)

# 5. Word document (.docx)
body = "".join(f"<w:p><w:r><w:t>{t}</w:t></w:r></w:p>" for t in
    ["SUPPLY CONTRACT", "This agreement is made between Falcon Ltd and Orion Corp.",
     "Value: 75,000 USD. Delivery: 30 days."] + [f"Clause {i}: standard terms apply." for i in range(1, 40)])
with zipfile.ZipFile(p("Confidential", "contract.docx"), "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    z.writestr("word/document.xml", '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + body + '</w:body></w:document>')

# 6. HTML page
with open(p("notes.html"), "w") as f:
    f.write("<html><head><title>Notes</title></head><body><h1>Drop location</h1>"
            + "".join(f"<p>Entry {i}: package handed over at gate {i % 7}.</p>" for i in range(80)) + "</body></html>")

# 7. JSON data
json.dump({"case": "Falcon", "contacts": [{"name": f"Contact {i}", "phone": f"+1-555-01{i:02d}"} for i in range(50)]},
          open(p("Confidential", "contacts.json"), "w"), indent=2)

# 8. ZIP archive
with zipfile.ZipFile(p("backup.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("plan.txt", "Phase 1: collect\nPhase 2: transfer\nPhase 3: erase traces\n" * 40)

# 9. A file that will NOT be deleted (control sample)
with open(p("readme.txt"), "w") as f:
    f.write("This drive belongs to the Finance department.\n")
print("Sample files created in", os.path.abspath(out))
