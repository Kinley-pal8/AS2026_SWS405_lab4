# The Sleuth Kit Hands-On Lab

**Create, Delete and Recover Evidence on Kali Linux**
*7 October 2026*

In this lab you build your own 200 MB NTFS disk image, plant 8 files of different types, delete them, and then recover every one of them with The Sleuth Kit (TSK), proving each recovery with a SHA-256 hash match. Every command below was test-run end to end, and the example outputs are real outputs from that run.

## Lab overview

**Scenario.** A USB drive was seized from a Finance employee suspected of leaking "Project Falcon" data. Before the drive was seized, the suspect deleted a report, a photo, a contract, a password list and other files. Your job is to analyse the drive image, find the deleted files, examine their metadata, recover them and prove the recovered files are unaltered.

**Learning objectives.** By the end of the lab, students can:

- Install and verify The Sleuth Kit on Kali Linux.
- Explain the TSK layer model: image → partition → file system → file name → metadata → content.
- Use `img_stat`, `mmls`, `fsstat`, `fls`, `istat`, `icat`, `ffind` and `tsk_recover` correctly.
- Find a partition offset and use it with `-o` in every file-system command.
- Recover deleted files and verify them with SHA-256 hashes.
- Build a simple file-activity timeline with `fls -m` and `mactime`.

**Requirements.** Kali Linux (VM is fine) with sudo rights, about 1 GB of free disk space, and 60–90 minutes.

### The lab at a glance

| Part | What you do | Main tools | Outcome |
|---|---|---|---|
| 1 | Install TSK | `apt`, `mmls -V` | TSK version printed |
| 2 | Build the evidence image | `dd`, `parted`, `losetup`, `mkfs.ntfs`, `mount` | Empty NTFS partition mounted |
| 3 | Plant 8 test files and hash them | `python3`, `file`, `sha256sum` | `original_hashes.txt` |
| 4 | Delete the files and seal the image | `rm`, `umount`, `sha256sum`, `chmod` | Read-only `evidence.dd` with a known hash |
| 5 | Investigate with TSK | `img_stat`, `mmls`, `fsstat`, `fls`, `istat` | Deleted files and their MFT entries identified |
| 6 | Recover and verify | `icat -r`, `file`, `sha256sum` | 8 files recovered, all hashes match |
| 7 | Bulk recovery and timeline | `tsk_recover`, `fls -m`, `mactime` | Recovered folder tree and a timeline |

**Golden rule for the whole lab.** Parts 2–4 play the role of the suspect. From Part 5 onwards you are the investigator: you never mount or modify `evidence.dd` again; you only read it with TSK.

---

## Part 1: Install The Sleuth Kit on Kali

TSK is often already present on Kali (it ships with Autopsy), but installing it is safe either way: apt simply reports that it is up to date.

**Step 1.1 - Update the package list and install the tools.** Open a terminal and run:

```bash
sudo apt update
sudo apt install -y sleuthkit ntfs-3g parted file python3
```

- `sleuthkit` is The Sleuth Kit itself.
- `ntfs-3g` provides `mkfs.ntfs` and NTFS mounting, needed to build the test image.
- `parted` creates the partition table; `file` identifies file types; `python3` runs the file generator.

**Expected outcome:** apt finishes with lines such as `Setting up sleuthkit (4.12.1...)`, or reports `sleuthkit is already the newest version`.

**Step 1.2 - Verify the installation.**

```bash
mmls -V
which img_stat mmls fsstat fls istat icat tsk_recover mactime
```

**Expected outcome:**

```
The Sleuth Kit ver 4.12.1
/usr/bin/img_stat
/usr/bin/mmls
/usr/bin/fsstat
/usr/bin/fls
/usr/bin/istat
/usr/bin/icat
/usr/bin/tsk_recover
/usr/bin/mactime
```

Your version number may be newer; any 4.x version works for this lab. If `which` prints nothing for a tool, the install failed: rerun Step 1.1 and read the error message.

**Step 1.3 - Create a working folder.** Everything in the lab lives here.

```bash
mkdir -p ~/tsk_lab && cd ~/tsk_lab
```

---

## Part 2: Build the evidence image

You create a file that behaves exactly like a real disk: a partition table, one NTFS partition starting at sector 2048, and a file system you can mount. You are playing the suspect's drive here.

**Step 2.1 - Create a blank 200 MB image.**

```bash
dd if=/dev/zero of=evidence.dd bs=1M count=200 status=progress
```

`if=/dev/zero` fills the file with zero bytes, `bs=1M count=200` makes it 200 × 1 MiB = 209,715,200 bytes.

**Expected outcome:** `209715200 bytes (210 MB, 200 MiB) copied`. Check with `ls -l evidence.dd`.

**Step 2.2 - Write a partition table and one partition.**

```bash
parted -s evidence.dd mklabel msdos mkpart primary ntfs 1MiB 100%
parted -s evidence.dd unit s print
```

`mklabel msdos` writes a DOS/MBR partition table. `mkpart primary ntfs 1MiB 100%` creates one partition from 1 MiB to the end. 1 MiB ÷ 512 bytes = sector 2048, the standard modern alignment.

**Expected outcome:**

```
Disk /home/kali/tsk_lab/evidence.dd: 409600s
Sector size (logical/physical): 512B/512B
Partition Table: msdos

Number  Start  End      Size     Type     File system  Flags
 1      2048s  409599s  407552s  primary
```

Remember 2048: TSK will rediscover this number in Part 5.

**Step 2.3 - Attach the image as a loop device.** Linux needs a block device to format and mount the partition.

```bash
LOOP=$(sudo losetup -fP --show evidence.dd)
echo $LOOP
ls ${LOOP}*
```

`-f` picks the first free loop device, `-P` scans the partition table, `--show` prints the device name.

**Expected outcome:** `/dev/loop0` followed by `/dev/loop0  /dev/loop0p1`. The number may differ (for example `loop1`); the `$LOOP` variable takes care of that. Keep this terminal open, because `$LOOP` exists only in this shell.

**Step 2.4 - Format the partition as NTFS.**

```bash
sudo mkfs.ntfs -Q -L EVIDENCE ${LOOP}p1
```

`-Q` is a quick format (no zeroing pass), `-L EVIDENCE` sets the volume label.

**Expected outcome:** ends with `mkntfs completed successfully. Have a nice day.`

**Step 2.5 - Mount it.**

```bash
sudo mkdir -p /mnt/evidence
sudo mount -t ntfs-3g ${LOOP}p1 /mnt/evidence
df -h /mnt/evidence
```

**Expected outcome:** a line similar to `/dev/loop0p1  199M  2.5M  197M  2% /mnt/evidence`. The drive is empty and ready for files.

> If `${LOOP}p1` does not exist (some VMs and containers do not create partition nodes), attach the partition directly using its offset in bytes instead, and use `$LOOP` wherever the lab says `${LOOP}p1`:
>
> ```bash
> sudo losetup -d $LOOP
> LOOP=$(sudo losetup -f --show -o $((2048*512)) --sizelimit $((407552*512)) evidence.dd)
> ```
>
> This is a preview of the core idea of the lab: a partition is just a region that starts at an offset inside the image.

---

## Part 3: Plant files of different types and hash them

A short Python script creates 9 realistic files: text, CSV, PDF, PNG, Word (.docx), HTML, JSON, ZIP, plus a `readme.txt` that will not be deleted (a control sample). It needs nothing beyond the Python that ships with Kali.

**Step 3.1 - Create the generator script.** Copy the whole block into the terminal; the `EOF` lines must be included.

```bash
cat > ~/tsk_lab/make_files.py << 'EOF'
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
EOF
```

**Step 3.2 - Run it against the mounted drive.**

```bash
sudo python3 ~/tsk_lab/make_files.py /mnt/evidence
ls -laR /mnt/evidence
```

**Expected outcome:** `Sample files created in /mnt/evidence`, then a listing like this:

```
/mnt/evidence:
drwxrwxrwx 1 root root    384 Confidential
-rwxrwxrwx 1 root root    182 backup.zip
-rwxrwxrwx 1 root root   3831 notes.html
-rwxrwxrwx 1 root root 215663 photo.png
-rwxrwxrwx 1 root root     46 readme.txt
-rwxrwxrwx 1 root root   4030 report.pdf
-rwxrwxrwx 1 root root     72 secret.txt

/mnt/evidence/Confidential:
-rwxrwxrwx 1 root root 3532 contacts.json
-rwxrwxrwx 1 root root 1099 contract.docx
-rwxrwxrwx 1 root root 1765 passwords.csv
```

You can open them to check they are real: `xdg-open /mnt/evidence/report.pdf` or `xdg-open /mnt/evidence/photo.png`.

**Step 3.3 - Confirm the file types by content, not by name.**

```bash
cd /mnt/evidence && file $(find . -type f | sort)
```

**Expected outcome:**

```
./Confidential/contacts.json: JSON text data
./Confidential/contract.docx: Microsoft Word 2007+
./Confidential/passwords.csv: CSV ASCII text
./backup.zip:                 Zip archive data, at least v2.0 to extract
./notes.html:                 HTML document, ASCII text
./photo.png:                  PNG image data, 320 x 240, 8-bit/color RGB
./readme.txt:                 ASCII text
./report.pdf:                 PDF document, version 1.4, 1 page(s)
./secret.txt:                 ASCII text
```

`file` reads the first bytes of each file (its "magic number", such as `%PDF` or `\x89PNG`). You will use this again after recovery to prove the recovered bytes are the right type.

**Step 3.4 - Record the original hashes.** This is your ground truth for checking recovery later. The control file `readme.txt` is excluded because it will not be deleted.

```bash
cd /mnt/evidence
sudo find . -type f ! -name readme.txt -exec sha256sum {} \; | sort -k2 > ~/tsk_lab/original_hashes.txt
cat ~/tsk_lab/original_hashes.txt
```

**Expected outcome:** 8 lines, one hash per file, for example:

```
8e5e30af...ee5c  ./Confidential/contacts.json
225da871...2e07  ./Confidential/contract.docx
49643b2b...7611  ./Confidential/passwords.csv
385a38ae...4b3c  ./backup.zip
b5e5497e...40a4  ./notes.html
375ec525...a2a7  ./photo.png
3969565e...4d15  ./report.pdf
8d7363b0...ee22  ./secret.txt
```

Your hashes for `contract.docx` and `backup.zip` will differ from these, because ZIP files store the time they were created. That is fine: you always compare against your own `original_hashes.txt`.

---

## Part 4: Delete the files and seal the image

The suspect now deletes everything except `readme.txt`, including the whole `Confidential` folder. Deleting on NTFS only marks the MFT entries and clusters as free; the bytes stay on disk until something overwrites them. That is why recovery is possible.

**Step 4.1 - Delete the files.**

```bash
cd /mnt/evidence
sudo rm -f secret.txt report.pdf photo.png notes.html backup.zip
sudo rm -rf Confidential
sync
ls -la /mnt/evidence
```

`sync` forces Linux to write all pending changes to the image.

**Expected outcome:** only `readme.txt` remains.

```
-rwxrwxrwx 1 root root   46 readme.txt
```

**Step 4.2 - Unmount and detach.** From now on the image is evidence and must not be mounted again.

```bash
cd ~/tsk_lab
sudo umount /mnt/evidence
sudo losetup -d $LOOP
losetup -a
```

**Expected outcome:** no errors, and `losetup -a` no longer lists `evidence.dd`. If `umount` says "target is busy", you are still inside `/mnt/evidence`: run `cd ~/tsk_lab` and try again.

**Step 4.3 - Hash the image (acquisition hash).**

```bash
sha256sum evidence.dd | tee evidence.dd.sha256
```

**Expected outcome:** one 64-character hash followed by `evidence.dd`. In a real case this hash is recorded when the drive is acquired, and it is rechecked at the end to prove the analysis did not change the evidence.

**Step 4.4 - Make the image read-only.**

```bash
chmod 444 evidence.dd
ls -l evidence.dd
```

**Expected outcome:** `-r--r--r-- 1 kali kali 209715200 ... evidence.dd`. This is a simple software write-protect; real labs also use hardware write-blockers when imaging physical drives.

---

## Part 5: Investigate the image with TSK

You are now the investigator. You received `evidence.dd` and its hash, and you know nothing else. Each step answers one question and hands a value to the next step: image → partition offset → file system → deleted file names → metadata address → content.

Work from `~/tsk_lab` for the rest of the lab. TSK reads the image directly, so none of these commands need sudo or mounting.

**Step 5.1 - Verify the evidence before touching it.** Question: Is this the same image that was acquired?

```bash
cd ~/tsk_lab
sha256sum -c evidence.dd.sha256
```

**Expected outcome:** `evidence.dd: OK`. If it says FAILED, stop: the evidence has changed and any result would be unreliable.

**Step 5.2 - `img_stat`: what is this image?**

```bash
img_stat evidence.dd
```

**Expected outcome:**

```
IMAGE FILE INFORMATION
--------------------------------------------
Image Type: raw

Size in bytes: 209715200
Sector size:    512
```

What it means: a raw (dd) image of 209,715,200 bytes with 512-byte sectors, so 409,600 sectors in total. An E01 image would show `Image Type: ewf`. TSK reads both the same way.

**Step 5.3 - `mmls`: how is the disk divided?**

```bash
mmls evidence.dd
```

**Expected outcome:**

```
DOS Partition Table
Offset Sector: 0
Units are in 512-byte sectors

      Slot      Start        End          Length       Description
000:  Meta      0000000000   0000000000   0000000001   Primary Table (#0)
001:  -------   0000000000   0000002047   0000002048   Unallocated
002:  000:000   0000002048   0000409599   0000407552   NTFS / exFAT (0x07)
```

How to read it:

- **000 Meta:** sector 0 holds the MBR partition table itself.
- **001 Unallocated:** sectors 0–2047 are the alignment gap before the first partition. Real investigations check gaps like this for hidden data.
- **002 NTFS / exFAT (0x07):** the partition you want. Its Start is 2048.

That Start value is the offset. Every file-system command from now on gets `-o 2048`. In bytes it is 2048 × 512 = 1,048,576 (1 MiB), which matches the `1MiB` you gave parted in Part 2.

> Try it: run `fsstat evidence.dd` without `-o`. TSK fails with a message like `Cannot determine file system type`, because sector 0 holds a partition table, not a file system.

**Step 5.4 - `fsstat -t`: which file system?**

```bash
fsstat -t -o 2048 evidence.dd
```

**Expected outcome:** `ntfs`. The `-t` option prints only the type.

**Step 5.5 - `fsstat`: how is the file system laid out?**

```bash
fsstat -o 2048 evidence.dd | head -30
```

**Expected outcome (key lines):**

```
FILE SYSTEM INFORMATION
--------------------------------------------
File System Type: NTFS
Volume Serial Number: 6A0F772972DE0827
OEM Name: NTFS
Volume Name: EVIDENCE
Version: Windows XP

METADATA INFORMATION
--------------------------------------------
First Cluster of MFT: 4
First Cluster of MFT Mirror: 25471
Size of MFT Entries: 1024 bytes
Range: 0 - 74
Root Directory: 5

CONTENT INFORMATION
--------------------------------------------
Sector Size: 512
Cluster Size: 4096
Total Cluster Range: 0 - 50942
```

What it means:

- **Volume Name: EVIDENCE** matches the label set in Part 2. Your serial number will differ.
- The **MFT** (Master File Table) is NTFS's metadata store. Every file has a 1,024-byte MFT entry holding its name, timestamps and the location of its data. Entries 0–15 are system files such as `$MFT`; entry 5 is the root directory.
- **Range: 0 - 74** means this small volume has 75 MFT entries, so every file you look for has an address between 0 and 74.
- A **cluster** (4,096 bytes = 8 sectors) is the smallest unit of file data.

**Step 5.6 - `fls`: what files exist now?**

```bash
fls -o 2048 evidence.dd
```

**Expected outcome (system files starting with `$` shortened):**

```
r/r 4-128-1:    $AttrDef
...
r/r 0-128-1:    $MFT
...
r/r 73-128-2:   readme.txt
-/d * 64-144-2: Confidential
-/r * 65-128-2: secret.txt
-/r * 67-128-2: report.pdf
-/r * 68-128-2: photo.png
-/r * 70-128-2: notes.html
-/r * 72-128-2: backup.zip
V/V 74:         $OrphanFiles
```

How to read one line, using `-/r * 67-128-2: report.pdf`:

| Field | Meaning |
|---|---|
| `-/r` | Type from the directory entry / type from the MFT entry. `-` = unknown (the deleted directory entry no longer says), `r` = regular file, `d` = directory |
| `*` | Deleted. The name and MFT entry are no longer allocated |
| `67` | MFT entry number, the metadata address you give to `istat` and `icat` |
| `128-2` | Attribute type 128 (`$DATA`, the file's content) and attribute id 2 |
| `report.pdf` | The file name |

Notice that `readme.txt` has no `*`: it is the allocated control file. The files inside `Confidential` are not shown yet because plain `fls` lists only the root folder.

**Step 5.7 - `fls -r -d -p`: list every deleted file.**

```bash
fls -r -d -p -o 2048 evidence.dd
```

`-r` recurses into subfolders, `-d` shows deleted entries only, `-p` prints the full path.

**Expected outcome:**

```
-/d * 64-144-2: Confidential
-/r * 66-128-2: Confidential/passwords.csv
-/r * 69-128-2: Confidential/contract.docx
-/r * 71-128-2: Confidential/contacts.json
-/r * 65-128-2: secret.txt
-/r * 67-128-2: report.pdf
-/r * 68-128-2: photo.png
-/r * 70-128-2: notes.html
-/r * 72-128-2: backup.zip
-/r * 16:       $OrphanFiles/OrphanFile-16
...
-/r * 23:       $OrphanFiles/OrphanFile-23
```

What it means: all 8 deleted files and the deleted folder are found, with their MFT entries. Write the entry numbers down; you need them in Part 6.

The `OrphanFile-16` to `OrphanFile-23` lines are reserved, never-used MFT entries that every new NTFS volume has; they are not evidence and can be ignored. Your entry numbers will normally match this table, but always use the numbers from your own output.

| MFT entry | Deleted file |
|---|---|
| 65 | secret.txt |
| 66 | Confidential/passwords.csv |
| 67 | report.pdf |
| 68 | photo.png |
| 69 | Confidential/contract.docx |
| 70 | notes.html |
| 71 | Confidential/contacts.json |
| 72 | backup.zip |

**Step 5.8 - `istat`: examine a deleted file's metadata.** Start with the PDF, entry 67.

```bash
istat -o 2048 evidence.dd 67
```

**Expected outcome:**

```
MFT Entry Header Values:
Entry: 67        Sequence: 2
$LogFile Sequence Number: 0
Not Allocated File
Links: 0

$STANDARD_INFORMATION Attribute Values:
Flags: Archive
Created:        2026-10-07 16:54:58.573165300 (UTC)
File Modified:  2026-10-07 16:54:58.573911700 (UTC)
MFT Modified:   2026-10-07 16:54:58.573911700 (UTC)
Accessed:       2026-10-07 16:54:58.718063500 (UTC)

$FILE_NAME Attribute Values:
Name: report.pdf
Parent MFT Entry: 5     Sequence: 5
...
Attributes:
Type: $STANDARD_INFORMATION (16-0)   Name: N/A   Resident   size: 48
Type: $FILE_NAME (48-3)   Name: N/A   Resident   size: 86
Type: $DATA (128-2)   Name: N/A   Non-Resident   size: 4030  init_size: 4030
25984
```

How to read it:

- **Not Allocated File** confirms the deletion at the metadata level.
- The four `$STANDARD_INFORMATION` timestamps are NTFS's MACB times: Modified (content), Accessed, Changed (MFT entry changed), Born (created). Your dates and times will be when you ran Part 3.
- **Parent MFT Entry: 5** means the file was in the root directory.
- **`$DATA ... Non-Resident size: 4030`** means the content is 4,030 bytes stored outside the MFT, in cluster 25984 (the number on the last line). Your cluster number may differ.

Now compare a small file, `secret.txt` (entry 65):

```bash
istat -o 2048 evidence.dd 65 | tail -5
```

**Expected outcome (last line):**

```
Type: $DATA (128-2)   Name: N/A   Resident   size: 72
```

What it means: the 72-byte file is resident: NTFS stored the content inside the 1,024-byte MFT entry itself, so there is no cluster list. Small NTFS files are usually resident, and they survive deletion as long as the MFT entry is not reused.

**Optional check, `ffind`:** turn a metadata address back into a name.

```bash
ffind -o 2048 evidence.dd 67
```

**Expected outcome:** `* //report.pdf`, where `*` again means deleted.

---

## Part 6: Recover every deleted file and verify it

`icat` reads the content that an MFT entry points to and writes it to standard output; you redirect it into a new file. All 8 files were recovered with matching hashes in the test run.

**Step 6.1 - Look at the content before saving it.** Start with the small text file. Nothing is written to disk yet; the content goes straight to the screen.

```bash
icat -r -o 2048 evidence.dd 65
```

**Expected outcome:**

```
Meeting with supplier on Friday 10:00.
Account: 4471-2290
Do not share.
```

The "deleted" note is fully readable. `-r` switches on recovery mode, which tells `icat` to follow the data runs of an unallocated (deleted) entry. Never run `icat` on a binary file such as a PNG without redirecting it, because the raw bytes will garble the terminal.

**Step 6.2 - See the raw cluster (optional).** In Step 5.8, `istat` showed that `report.pdf` lives in cluster 25984. Read that cluster directly with `blkcat`:

```bash
blkcat -o 2048 evidence.dd 25984 | head -c 120
```

**Expected outcome:**

```
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
...
```

The PDF signature `%PDF-1.4` sits right at the start of the cluster: the file's bytes are still on disk even though the file is "gone". Use your own cluster number if it was different.

**Step 6.3 - Recover the PDF to a file.**

```bash
mkdir -p ~/tsk_lab/recovered
icat -r -o 2048 evidence.dd 67 > recovered/report.pdf
ls -l recovered/report.pdf
file recovered/report.pdf
```

**Expected outcome:**

```
-rw-r--r-- 1 kali kali 4030 ... recovered/report.pdf
recovered/report.pdf: PDF document, version 1.4, 1 page(s)
```

The size, 4,030 bytes, matches the `$DATA size: 4030` that `istat` reported. Open it with `xdg-open recovered/report.pdf` and you will see the "CONFIDENTIAL REPORT - Project Falcon" page.

**Step 6.4 - Recover all the other files.** Run one `icat` per file, using the MFT entries from Step 5.7:

```bash
cd ~/tsk_lab
icat -r -o 2048 evidence.dd 65 > recovered/secret.txt
icat -r -o 2048 evidence.dd 66 > recovered/passwords.csv
icat -r -o 2048 evidence.dd 68 > recovered/photo.png
icat -r -o 2048 evidence.dd 69 > recovered/contract.docx
icat -r -o 2048 evidence.dd 70 > recovered/notes.html
icat -r -o 2048 evidence.dd 71 > recovered/contacts.json
icat -r -o 2048 evidence.dd 72 > recovered/backup.zip
ls -l recovered
```

**Expected outcome:**

```
-rw-r--r-- 1 kali kali    182 backup.zip
-rw-r--r-- 1 kali kali   3532 contacts.json
-rw-r--r-- 1 kali kali   1099 contract.docx
-rw-r--r-- 1 kali kali   3831 notes.html
-rw-r--r-- 1 kali kali   1765 passwords.csv
-rw-r--r-- 1 kali kali 215663 photo.png
-rw-r--r-- 1 kali kali   4030 report.pdf
-rw-r--r-- 1 kali kali     72 secret.txt
```

Every size matches the original listing from Step 3.2. Note that `icat` needs only the MFT number, not the name: you chose the output file names yourself. The names came from `fls`.

**Step 6.5 - Confirm the file types.**

```bash
file recovered/*
```

**Expected outcome:**

```
recovered/backup.zip:    Zip archive data, at least v2.0 to extract
recovered/contacts.json: JSON text data
recovered/contract.docx: Microsoft Word 2007+
recovered/notes.html:    HTML document, ASCII text
recovered/passwords.csv: CSV ASCII text
recovered/photo.png:     PNG image data, 320 x 240, 8-bit/color RGB
recovered/report.pdf:    PDF document, version 1.4, 1 page(s)
recovered/secret.txt:    ASCII text
```

This is identical to the Step 3.3 output, so the content is the right type, not just the right name. Open a few to see them: `xdg-open recovered/photo.png`, `unzip -l recovered/backup.zip`, `head recovered/passwords.csv`.

**Step 6.6 - Prove the recovery with hashes.** The original hash list stores `Confidential/` paths, while the recovered folder is flat, so `sed` strips that folder name before the check:

```bash
cd ~/tsk_lab/recovered
sha256sum -c <(sed 's#\./Confidential/#./#' ../original_hashes.txt)
cd ~/tsk_lab
```

**Expected outcome:**

```
./contacts.json: OK
./contract.docx: OK
./passwords.csv: OK
./backup.zip: OK
./notes.html: OK
./photo.png: OK
./report.pdf: OK
./secret.txt: OK
```

Eight OK lines mean every recovered file is bit-for-bit identical to the original that was deleted. Then record the hashes of what you recovered for your report:

```bash
sha256sum recovered/* | tee recovered_hashes.txt
```

**Why recovery can fail in real cases:** this lab recovers 100% because nothing was written after the deletion. On a drive in use, new files can reuse the freed clusters (the data is overwritten) or reuse the MFT entry (the name and data runs are lost). SSDs with TRIM may also erase freed blocks automatically. A FAILED hash on a real case means the content is partly overwritten, and you report it that way.

---

## Part 7: Bulk recovery, timeline and final integrity check

**Step 7.1 - `tsk_recover`: recover every deleted file in one command.** Part 6 recovered files one by one, which is how you work when you need specific items. `tsk_recover` does the same job for all deleted files at once and rebuilds the folder tree.

```bash
tsk_recover -o 2048 evidence.dd tsk_recovered
find tsk_recovered -type f | sort
```

**Expected outcome:**

```
Files Recovered: 8
tsk_recovered/Confidential/contacts.json
tsk_recovered/Confidential/contract.docx
tsk_recovered/Confidential/passwords.csv
tsk_recovered/backup.zip
tsk_recovered/notes.html
tsk_recovered/photo.png
tsk_recovered/report.pdf
tsk_recovered/secret.txt
```

By default `tsk_recover` exports only unallocated (deleted) files, so `readme.txt` is not included. Use `-a` for allocated files only or `-e` for everything; `tsk_recover -e` reports `Files Recovered: 9`.

Because the folder structure is kept, the original hash list can be checked directly:

```bash
cd tsk_recovered && sha256sum -c ../original_hashes.txt && cd ..
```

**Expected outcome:** the same 8 OK lines as Step 6.6.

**Step 7.2 - Build a timeline with `fls -m` and `mactime`.** A timeline orders every file event by time, which is how investigators reconstruct what happened. It takes two commands: `fls -m` writes a "body file" with every timestamp, and `mactime` sorts it.

```bash
fls -r -m / -o 2048 evidence.dd > bodyfile.txt
mactime -b bodyfile.txt -d -z UTC | grep -v '\$' > timeline.csv
cat timeline.csv
```

`-m /` sets the path prefix in the body file, `-d` makes comma-separated output, `-z UTC` fixes the time zone, and `grep -v '\$'` hides NTFS system files.

**Expected outcome (your date and times will be when you ran the lab):**

```
Date,Size,Type,Mode,UID,GID,Meta,File Name
Wed Oct 07 2026 16:54:58,48,.a.b,-/drwxrwxrwx,48,0,64-144-2,"/Confidential (deleted)"
Wed Oct 07 2026 16:54:58,72,macb,-/rrwxrwxrwx,48,0,65-128-2,"/secret.txt (deleted)"
Wed Oct 07 2026 16:54:58,1765,macb,-/rrwxrwxrwx,48,0,66-128-2,"/Confidential/passwords.csv (deleted)"
Wed Oct 07 2026 16:54:58,4030,macb,-/rrwxrwxrwx,48,0,67-128-2,"/report.pdf (deleted)"
Wed Oct 07 2026 16:54:58,215663,macb,-/rrwxrwxrwx,48,0,68-128-2,"/photo.png (deleted)"
...
Wed Oct 07 2026 16:54:58,46,macb,r/rrwxrwxrwx,48,0,73-128-2,"/readme.txt"
Wed Oct 07 2026 16:55:02,48,m.c.,-/drwxrwxrwx,48,0,64-144-2,"/Confidential (deleted)"
```

How to read it: the Type column shows which timestamps fired at that moment: `m` modified, `a` accessed, `c` MFT changed, `b` born (created). All files were created at 16:54:58. The last line shows the `Confidential` folder modified and changed at 16:55:02, four seconds later: that is the moment its contents were deleted. You can open `timeline.csv` in LibreOffice Calc to sort and filter it. (Some Kali versions print a harmless `Old package separator` warning from `mactime`; ignore it.)

**Step 7.3 - Prove the evidence was not changed.**

```bash
sha256sum -c evidence.dd.sha256
```

**Expected outcome:** `evidence.dd: OK`. The image hash is the same as before the analysis, which proves that every TSK command only read the evidence. This is the last line of any defensible examination.

---

## Lab report, review questions, troubleshooting and cleanup

### Lab report template

Students fill in this table from their own outputs and hand it in with `original_hashes.txt`, `recovered_hashes.txt` and `timeline.csv`.

| Item | Your value | Command it came from |
|---|---|---|
| Image SHA-256 (before) | | `sha256sum` |
| Image type and size | | `img_stat` |
| Partition start sector (offset) | | `mmls` |
| File system type and volume name | | `fsstat` |
| Cluster size / MFT entry size | | `fsstat` |
| Number of deleted files found | | `fls -r -d -p` |
| MFT entry of report.pdf | | `fls` |
| report.pdf created time (UTC) | | `istat` |
| report.pdf data cluster | | `istat` |
| Files recovered / hashes matching | | `icat`, `sha256sum -c` |
| Time the Confidential folder was emptied | | `mactime` |
| Image SHA-256 (after) matches? | | `sha256sum -c` |

### Review questions

1. Why does `fsstat evidence.dd` fail without `-o`, and where does the value 2048 come from?
2. What do the `*` and the `-/r` mean in `-/r * 67-128-2: report.pdf`?
3. `secret.txt` is resident and `report.pdf` is non-resident. What is the difference, and how did `istat` show it?
4. `icat` recovered the files without knowing their names. How is that possible?
5. Why do we compare SHA-256 hashes instead of just opening the recovered files?
6. Give two reasons a deleted file might not be recoverable on a real, in-use drive.
7. What does the final `sha256sum -c evidence.dd.sha256` prove, and why is it important in court?

### Extension task: see overwriting happen

Rebuild the image (Parts 2–4), but in Step 4.1 run this right after the `rm` commands and before `sync`:

```bash
sudo dd if=/dev/urandom of=/mnt/evidence/filler.bin bs=1M count=150
```

Then repeat Parts 5–7. In the test run, `fls -r -d -p` found only the 5 root-folder files: the new file reused the `Confidential` folder's MFT entry, so the 3 files inside it lost their path. `tsk_recover` plus `sha256sum -c` gave OK only for `secret.txt` and `backup.zip`, while `report.pdf`, `photo.png` and `notes.html` came back FAILED. Explain this result using what `istat` told you about resident and non-resident data.

### Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `Cannot determine file system type` | Missing or wrong `-o` value | Take the Start sector from `mmls` and pass it with `-o` |
| `${LOOP}p1: No such file` | Partition node not created, or `$LOOP` lost in a new terminal | Run `echo $LOOP`; re-attach with `losetup -fP`, or use the offset method in Part 2 |
| `mkfs.ntfs: command not found` | ntfs-3g not installed | `sudo apt install -y ntfs-3g` |
| `umount: target is busy` | Your shell is inside `/mnt/evidence` | `cd ~/tsk_lab`, then unmount again |
| Permission denied writing to the image | The image is read-only (by design) | Correct: TSK only needs read access. Never `chmod` it back during analysis |
| Different MFT numbers or cluster numbers | Different file order or NTFS version | Use the numbers from your own `fls` and `istat` output |
| Hashes of contract.docx and backup.zip differ from the handout | ZIP files store their creation time | Compare only against your own `original_hashes.txt` |

### Cleanup

When you have finished and handed in your report:

```bash
cd ~
sudo umount /mnt/evidence 2>/dev/null
sudo losetup -D
rm -rf ~/tsk_lab
```

`losetup -D` detaches all loop devices. Deleting `~/tsk_lab` removes the image, the recovered files and the hash lists; keep a copy if you want to repeat Parts 5–7 without rebuilding the image.
