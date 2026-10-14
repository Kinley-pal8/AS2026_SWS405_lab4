# SWS405 — Lab 4: The Sleuth Kit (Create, Delete & Recover Evidence)

Digital-forensics lab for **SWS405**. A 200 MB NTFS disk image is built, eight
files of different types are planted and then deleted, and every file is
recovered with [The Sleuth Kit](https://www.sleuthkit.org/) (TSK) — each
recovery proven **bit-for-bit identical** to the original with SHA-256 hashes,
and the evidence image proven **unaltered** by a final hash check.

| | |
|---|---|
| **Student** | Kinley Palden (02230287) |
| **Instructor** | Mr. Pema Thinley |
| **Platform** | Kali Linux · The Sleuth Kit 4.14.0 |
| **Date** | 14 October 2026 |

## Scenario

A USB drive was seized from a Finance employee suspected of leaking "Project
Falcon" data. Before seizure the suspect deleted a report, a photo, a contract,
a password list and other files. The task: analyse the drive image, find the
deleted files, examine their metadata, recover them, and prove the recovered
files are unaltered.

## Results at a glance

- **8 / 8** deleted files recovered — all SHA-256 hashes **OK**
- Partition found at sector **2048**; NTFS volume **EVIDENCE** (cluster 4096, MFT range 0–74)
- `report.pdf` → MFT entry **67**, non-resident in cluster **25984**; `secret.txt` → resident
- Timeline reconstructed (MACB): files created → read → `Confidential` folder emptied
- Final integrity check: `evidence.dd: OK` — the image was only ever read, never modified

## Repository structure

```
.
├── SUBMISSION_REPORT.md        Full lab report (results, review questions, screenshot gallery)
├── README.md                   This file
├── TSK_Hands_On_Lab_Kali.md    The original lab instructions
├── lab_guide.md                Plain-language explanation of the lab
├── screenshots/                21 screenshots captured during the lab (p1, 2.1 … 7.3)
└── tsk_lab/                    Lab artifacts
    ├── make_files.py           Generator for the 8 sample files + control file
    ├── original_hashes.txt     SHA-256 of the files before deletion (ground truth)
    ├── recovered_hashes.txt    SHA-256 of the recovered files
    ├── evidence.dd.sha256      Acquisition hash of the disk image
    ├── timeline.csv            MACB timeline (fls -m + mactime)
    ├── bodyfile.txt            Raw body file for the timeline
    ├── recovered/              Files recovered individually with icat
    └── tsk_recovered/          Files recovered in bulk with tsk_recover (folder tree preserved)
```

> **Note:** the 200 MB raw image `tsk_lab/evidence.dd` is **not** committed — it
> exceeds GitHub's 100 MB file limit. Its integrity is preserved by
> `tsk_lab/evidence.dd.sha256`, and it can be rebuilt by following the lab steps.

## How it was done (summary)

The lab is split into two roles, following forensic best practice:

1. **Suspect role (Parts 2–4)** — build `evidence.dd`, partition + format NTFS,
   mount, plant files (`make_files.py`), record original hashes, delete all but
   `readme.txt`, unmount, hash the image and set it read-only.
2. **Investigator role (Parts 5–7)** — working **read-only**: verify the
   acquisition hash, locate the partition (`mmls`) and file system (`fsstat`),
   list deleted files and MFT entries (`fls`), inspect metadata (`istat`),
   recover with `icat -r` and `tsk_recover`, verify with `sha256sum -c`, build a
   timeline (`mactime`), and re-verify the image hash.

**Tools:** `dd`, `parted`, `losetup`, `mkfs.ntfs`, `mount`, `python3`, `file`,
`sha256sum`, `img_stat`, `mmls`, `fsstat`, `fls`, `istat`, `ffind`, `icat`,
`blkcat`, `tsk_recover`, `mactime`.

Full command-by-command walkthrough and outputs are in
[`SUBMISSION_REPORT.md`](SUBMISSION_REPORT.md).

## Verifying the recovery

With the recovered files present, the hash match can be re-checked:

```bash
cd tsk_lab/tsk_recovered
sha256sum -c ../original_hashes.txt      # expect 8× OK
```
