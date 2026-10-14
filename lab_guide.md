# Understanding the TSK Lab — Plain-Language Guide

I will explain your lab from the beginning in simple language, assuming you are new to Linux commands, loops, disk images, and digital forensics.

The most important thing to understand first is this:

`evidence.dd` is a file that acts like a complete hard disk. You create it, put a partition and a file system inside it, save sample files in it, delete some of those files, and then investigate the same image to recover evidence.

You do not need a real hard disk for this lab. Your Kali Linux computer creates a simulated disk using an ordinary file. The explanation below follows your uploaded lab instructions.

---

## 1. First understand the whole lab

Think of the process as a real investigation involving a suspect's hard disk.

- **Step 1: Create `evidence.dd`** — Create an empty 200 MiB file that will represent a hard disk.
- **Step 2: Prepare the virtual disk** — Add a partition table, create an NTFS file system, and mount the partition.
- **Step 3: Put files inside** — Create a PDF, image, text file, CSV, Word document, and other sample files.
- **Step 4: Delete selected files** — Delete the files from the mounted partition, leaving `readme.txt`.
- **Step 5: Preserve the image and investigate** — Use Sleuth Kit to identify deleted files and attempt to recover their contents.

The key idea is that you create the image first and investigate that very same image later. You do not create a new `evidence.dd` after deleting the files.

### The five steps at a glance

**Step 1: Create evidence.dd** — Create an empty 200 MiB file that will represent a hard disk.

```bash
dd if=/dev/zero of=evidence.dd bs=1M count=200
# 200+0 records in
# 200+0 records out
# 209715200 bytes (210 MB) copied, 0.XXX s, XXX MB/s
```

**Step 2: Prepare the virtual disk** — Add a partition table, create an NTFS file system, and mount the partition.

```bash
sudo parted evidence.dd
# (parted) mklabel msdos
# (parted) mkpart primary ntfs 1MiB 200MiB
# (parted) quit

sudo mkfs.ntfs -F /dev/loop0p1
sudo mount /dev/loop0p1 /mnt/evidence
```

Partition layout: NTFS (≈ 199 MiB), mounted at `/mnt/evidence`.

**Step 3: Put files inside** — Create a PDF, image, text file, CSV, Word document, and other sample files (`report.pdf`, `image.jpg`, `notes.txt`, `data.csv`, `document.docx`, `archive.zip`).

```bash
cd /mnt/evidence
touch readme.txt
echo "This is a sample file" > readme.txt
touch report.pdf image.jpg notes.txt data.csv document.docx archive.zip
```

**Step 4: Delete selected files** — Delete the files from the mounted partition, leaving `readme.txt`.

```bash
cd /mnt/evidence
rm -f report.pdf image.jpg notes.txt data.csv document.docx archive.zip
ls
```

(`readme.txt` is kept; the rest are deleted.)

**Step 5: Preserve the image and investigate** — Use Sleuth Kit to identify deleted files and attempt to recover their contents.

```bash
fls evidence.dd
icat evidence.dd <inode> > recovered.pdf
icat evidence.dd <inode> > recovered.jpg
mmls evidence.dd
mdfind evidence.dd
photorec evidence.dd
```

Sleuth Kit lets you: identify deleted files (`fls`, `mdfind`), recover file contents (`icat`, `photorec`), and analyze partition structure (`mmls`).

---

## 2. What is the actual directory structure?

Before running commands, you need to understand where each thing lives. Your lab uses a directory called `tsk_lab` in your Kali Linux home directory.

### The directory structure before the lab starts

```
/home/kali/
└── tsk_lab/
    ├── evidence.dd          The virtual disk image
    ├── make_files.py        Python script to create sample files
    ├── original_hashes.txt  Hashes of files before deletion
    └── evidence.dd.sha256   Hash of the whole disk image
/mnt/evidence/               Mount point
```

`/mnt/evidence/` is where you access the files stored inside the virtual disk while it is mounted.

These paths have different jobs:

- `/home/kali/tsk_lab/` is where you keep the disk image and your lab scripts.
- `/mnt/evidence/` is where Linux lets you access the contents of the partition inside `evidence.dd`.
- `evidence.dd` is the disk image file itself, not a folder.
- `make_files.py` is a program that creates sample files inside the mounted disk.

The lab creates `tsk_lab` in advance, so if it does not exist, create it first:

```bash
mkdir -p ~/tsk_lab
cd ~/tsk_lab
pwd
```

Expected output:

```
/home/kali/tsk_lab
```

Explanation:

- `mkdir` means create a directory.
- `-p` means create any missing parent directories and do not complain if the directory already exists.
- `~` means your current user's home directory. For Kali, it is normally `/home/kali`.
- `cd` means change directory.
- `pwd` means print working directory; it tells you where you are currently working.

---

## 3. What is `evidence.dd`? Where does it come from?

This is the most important part of your question.

### 3.1 Is `evidence.dd` a real hard disk?

No. In this lab, it starts as a normal file. You use a Linux command to fill it with zero bytes and make it the size of a small disk.

The command is:

```bash
dd if=/dev/zero of=evidence.dd bs=1M count=200 status=progress
```

Let's explain every part.

| Command part | Simple meaning |
|---|---|
| `dd` | Copies data from an input to an output. |
| `if=/dev/zero` | Input comes from `/dev/zero`, which supplies zero bytes. |
| `of=evidence.dd` | Write the output to a file named `evidence.dd`. |
| `bs=1M` | Copy data in blocks of 1 MiB each. |
| `count=200` | Copy 200 blocks. |
| `status=progress` | Display progress while copying. |

The result is a file of 209,715,200 bytes, or 200 MiB.

At this point, `evidence.dd` contains zeros. It does not yet contain your sample files or a usable NTFS file system. Think of it as an empty notebook. You have created the notebook, but you have not yet written anything in it.

### 3.2 How does a normal file become a virtual disk?

Your next commands prepare that file to behave like a disk.

- `evidence.dd` — An ordinary file filled with zero bytes
- **Partition table** — Records where the partition begins and ends
- **NTFS file system** — Organizes directories, file names, metadata, and file data
- Mounted at `/mnt/evidence` — You can now create, open, and delete files stored inside the image.

Your command for creating the partition table is:

```bash
parted -s evidence.dd mklabel msdos mkpart primary ntfs 1MiB 100%
```

Here is the meaning:

- `parted` is a disk partitioning tool.
- `-s` means run in script mode without interactive questions.
- `evidence.dd` tells it which disk image to modify.
- `mklabel msdos` creates a DOS/MBR partition table.
- `mkpart primary ntfs` defines one primary partition intended for an NTFS file system.
- `1MiB` says the partition starts 1 MiB from the beginning of the image.
- `100%` says it ends at the end of the image.

**Important:** `parted` defines the partition; it does not format that partition as NTFS. That is why you later run `mkfs.ntfs`.

The next command is:

```bash
parted -s evidence.dd unit s print
```

- `unit s` asks `parted` to show locations in sectors.
- `print` displays the partition information.

A sector is a small unit of disk storage. In this lab, each sector is 512 bytes. The partition begins at sector 2048.

### 3.3 What is a loop device?

You then run:

```bash
LOOP=$(sudo losetup -fP --show evidence.dd)
```

This command is often confusing for beginners because it contains the word `LOOP`.

First, `LOOP` here is a variable name, not a programming loop. You could call it `DISK` instead, but the lab uses `LOOP`.

Break the command down:

- `sudo` runs the command with administrator privileges.
- `losetup` connects a file to a Linux loop device.
- `-f` finds an available loop device.
- `-P` asks Linux to scan the image's partition table and create partition device nodes.
- `--show` prints the loop device name.
- `evidence.dd` is the file to connect.
- `$(...)` runs the command inside the parentheses and captures its output.
- `LOOP=...` saves that output in a shell variable.

For example, the variable might hold `/dev/loop0`. Linux may then expose the partition as `/dev/loop0p1`. The `p1` means partition 1 of loop device 0.

The image still exists as `/home/kali/tsk_lab/evidence.dd`. The loop device is simply a way for Linux to access its contents as though they were on a disk.

Next:

```bash
echo $LOOP
ls ${LOOP}*
```

- `echo $LOOP` prints the device name stored in the variable.
- `ls ${LOOP}*` lists matching device names, such as `/dev/loop0` and `/dev/loop0p1`.
- `$LOOP` retrieves the value of the variable.
- `${LOOP}p1` means take the variable's value and append `p1`.

Now format the partition:

```bash
sudo mkfs.ntfs -Q -L EVIDENCE ${LOOP}p1
```

- `mkfs.ntfs` creates an NTFS file system.
- `-Q` requests a quick format.
- `-L EVIDENCE` sets the file system's volume label to `EVIDENCE`.
- `${LOOP}p1` identifies the partition being formatted.

This prepares the partition to store files.

### 3.4 What does mounting mean?

Run:

```bash
sudo mkdir -p /mnt/evidence
sudo mount -t ntfs-3g ${LOOP}p1 /mnt/evidence
df -h /mnt/evidence
```

Mounting means making the contents of a file system accessible through a directory.

- `mkdir -p /mnt/evidence` creates the directory used as the access point.
- `mount` connects the NTFS partition to that directory.
- `-t ntfs-3g` specifies the NTFS driver.
- `${LOOP}p1` is the partition being mounted.
- `/mnt/evidence` is the directory through which you access it.
- `df -h /mnt/evidence` shows its storage usage in human-readable units.

Before mounting, `/mnt/evidence` is just an ordinary directory on your Kali system. After mounting, opening that directory shows the files inside the virtual disk's NTFS partition.

This distinction is crucial: the directory `/mnt/evidence` is not the disk image. It is the doorway through which you access the disk image's contents.

---

## 4. What are loops in programming?

Now let's understand the other meaning of the word: a programming loop.

A loop tells a computer to repeat an instruction, usually for a number of times or for each item in a collection.

Imagine telling a student: "Write the numbers 1 to 5 in your notebook."

Without a loop, you might write five separate instructions:

```python
print(1)
print(2)
print(3)
print(4)
print(5)
```

With a loop, you can write:

```python
for i in range(5):
    print(i)
```

Output:

```
0
1
2
3
4
```

Why does it start at zero? Because `range(5)` generates five numbers: `0, 1, 2, 3, 4`. It stops before 5.

If you want to print numbers from 1 to 5:

```python
for i in range(1, 6):
    print(i)
```

Output:

```
1
2
3
4
5
```

The important parts are:

- `for` starts the loop.
- `i` is a variable that takes a different value during each repetition.
- `range(1, 6)` generates the numbers 1 through 5.
- `:` marks the start of the loop's body.
- The indented line `print(i)` is executed for every number.

### 4.1 Why does your lab use loops?

Your Python script creates many sample evidence files automatically. Instead of manually writing dozens of lines, it uses loops to repeat a task.

For example, the lab has this code:

```python
for i in range(60):
    f.write(f"server{i:02d},admin{i:02d},P@ss-{random.Random(i).randint(100000,999999)}\n")
```

This loop creates 60 rows in `passwords.csv`.

Let's simplify it first:

```python
for i in range(3):
    print("Creating record", i)
```

Output:

```
Creating record 0
Creating record 1
Creating record 2
```

Your real code uses `range(60)`, so it repeats 60 times. During each repetition:

- `i` changes from 0 to 59.
- `server{i:02d}` creates names such as `server00`, `server01`, and `server02`.
- `admin{i:02d}` creates names such as `admin00`, `admin01`, and `admin02`.
- `random.Random(i).randint(100000,999999)` generates a six-digit number.
- `f.write(...)` writes one row to the CSV file.
- `\n` starts a new line.

This creates data that looks like:

```
system,username,password
server00,admin00,P@ss-...
server01,admin01,P@ss-...
server02,admin02,P@ss-...
```

The `...` above is just a placeholder for the generated digits.

The `random.Random(i)` expression uses `i` as a seed, so the number generated for a given `i` is repeatable in this script. These are fictional sample credentials, not real passwords recovered from a system.

### 4.2 Every loop in your Python script, explained

Your script contains several loops for different purposes.

| Code in the script | What it does |
|---|---|
| `for i in range(60):` | Writes 60 CSV data rows. |
| `for i in range(1, 60)` | Generates 59 additional report lines. |
| `for i, o in enumerate(objs, 1):` | Processes the PDF's five objects, one at a time. |
| `for o in offs` | Writes the PDF's object-offset entries into its index. |
| `for y in range(h):` | Processes each of the image's 240 rows. |
| `for x in range(w)` | Processes each of the image's 320 columns to generate pixel values. |
| `for i in range(1, 40)` | Generates 39 additional clauses in the Word document. |
| `for i in range(80)` | Generates 80 HTML entries. |
| `for i in range(50)` | Generates 50 fictional contacts in the JSON data. |

Some of the loops appear inside other expressions rather than on their own lines. They still repeat an operation. For example:

```python
"".join(f"<p>Entry {i}: package handed over at gate {i % 7}.</p>" for i in range(80))
```

This generates 80 HTML paragraphs and joins them into one long string.

The `%` symbol means modulo, or remainder. `i % 7` cycles through values 0 to 6 as `i` increases, so the fictional gate number repeats.

Remember: the `LOOP` shell variable is unrelated to these Python loops. One stores a Linux device name; the other repeats instructions.

---

## 5. Where do the sample files actually come from?

This is the second major point to understand.

Your lab includes a Python script named `make_files.py`. You create this script by copying the code block into the terminal.

The command is:

```bash
cat > ~/tsk_lab/make_files.py << 'EOF'
```

Here is what each part does:

- `cat` can display text or accept text from standard input.
- `>` redirects that text into a file.
- `~/tsk_lab/make_files.py` is the destination file.
- `<< 'EOF'` tells the shell to accept multiple lines of text until it encounters a line containing only `EOF`.
- The quoted `EOF` prevents the shell from expanding things like `$variables` while you are entering the script.

You then paste all the Python code, followed by:

```
EOF
```

That final `EOF` ends the input. It is not part of the Python program.

**Important:** creating `make_files.py` does not create the evidence files yet. It only saves the instructions that will create them later.

### 5.1 What happens when you run the Python script?

The lab uses:

```bash
sudo python3 ~/tsk_lab/make_files.py /mnt/evidence
```

Break it down:

| Part | Meaning |
|---|---|
| `sudo` | Run with administrator privileges. |
| `python3` | Start the Python interpreter. |
| `~/tsk_lab/make_files.py` | Read and execute the script you saved. |
| `/mnt/evidence` | Tell the script where to create the sample files. |

Look at the beginning of the script:

```python
import os, sys, zlib, struct, random, zipfile, json
out = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(os.path.join(out, "Confidential"), exist_ok=True)
p = lambda *a: os.path.join(out, *a)
```

Simple explanation:

- `import` loads Python modules that provide useful functions.
- `os` helps work with directories and file paths.
- `sys` lets the program read command-line arguments.
- `zlib` and `struct` help construct the PNG image and PDF-related binary data.
- `random` generates sample numbers.
- `zipfile` creates ZIP archives and the package used for the Word document.
- `json` creates JSON data.
- `sys.argv[1]` retrieves the first argument after the script's name: `/mnt/evidence`.
- `if len(sys.argv) > 1 else "."` means use the supplied directory, or use the current directory `.` if no directory was supplied.
- `os.makedirs(...)` creates a directory named `Confidential` inside the destination.
- `exist_ok=True` allows that directory to exist already.
- `p = lambda *a: os.path.join(out, *a)` defines a small helper function to build file paths.

That last line is especially useful. A path is the address of a file or directory.

For example, when `out` is `/mnt/evidence`:

```python
p("secret.txt")
```

produces:

```
/mnt/evidence/secret.txt
```

And:

```python
p("Confidential", "passwords.csv")
```

produces:

```
/mnt/evidence/Confidential/passwords.csv
```

The script is not creating these files in a random place. Its destination is determined by the `/mnt/evidence` argument.

### 5.2 How does each file get created?

Here are examples from your script.

**A. Creating `secret.txt`**

```python
with open(p("secret.txt"), "w") as f:
    f.write("Meeting with supplier on Friday 10:00.\nAccount: 4471-2290\nDo not share.\n")
```

- `open(...)` opens a file.
- `"w"` means write mode. It creates the file if it does not exist and replaces its contents if it already exists.
- `as f` assigns the opened file to the variable `f`.
- `f.write(...)` writes the text to the file.
- `\n` means start a new line.
- `with` ensures the file is properly closed when the indented block finishes.

The result is: `/mnt/evidence/secret.txt`

**B. Creating `passwords.csv`**

```python
with open(p("Confidential", "passwords.csv"), "w") as f:
    f.write("system,username,password\n")
    for i in range(60):
        f.write(...)
```

The script first writes a header row. The loop then writes 60 additional rows.

The result is: `/mnt/evidence/Confidential/passwords.csv`

**C. Creating `report.pdf`**

Your script constructs a small PDF by writing PDF objects, their contents, and an index that allows readers to locate those objects.

The loop:

```python
for i, o in enumerate(objs, 1):
```

processes each object in the `objs` list, assigning a number to it. The script then assembles the PDF bytes and writes them to:

```
/mnt/evidence/report.pdf
```

The script builds this PDF itself. It does not download a report from somewhere else.

**D. Creating `photo.png`**

The script creates an image 320 pixels wide and 240 pixels high.

```python
w, h = 320, 240
```

The loops process the rows and columns of the image, generating red, green, and blue pixel values. The script compresses these values into PNG format and writes the image to:

```
/mnt/evidence/photo.png
```

**E. Creating `contract.docx`**

The script builds the Word document using XML files stored in a ZIP-format package. It writes that package to:

```
/mnt/evidence/Confidential/contract.docx
```

**F. Creating the remaining files**

The script also generates:

- `notes.html` — an HTML page with 80 entries.
- `contacts.json` — fictional contact records.
- `backup.zip` — a ZIP archive containing `plan.txt`.
- `readme.txt` — a control file that the lab deliberately keeps.

After running the script, your structure should look like this:

```
/mnt/evidence/
├── secret.txt
├── report.pdf
├── photo.png
├── notes.html
├── backup.zip
├── readme.txt
└── Confidential/
    ├── passwords.csv
    ├── contract.docx
    └── contacts.json
```

There are nine files in total: eight files that the lab will delete, plus `readme.txt`, which remains as the control sample.

Check the directory with:

```bash
ls -laR /mnt/evidence
```

- `ls` lists files.
- `-l` shows detailed information.
- `-a` includes hidden entries.
- `-R` recursively lists subdirectories too.

You can verify file types with:

```bash
cd /mnt/evidence
file $(find . -type f | sort)
```

Here, `find . -type f` locates regular files under the current directory, `sort` orders their paths, and `$(...)` passes those paths to `file`. The `file` utility examines file content signatures and other structural clues to identify file types.

### 5.3 Why does the lab calculate file hashes?

Before deletion, the lab records SHA-256 hashes:

```bash
cd /mnt/evidence
```

(The hashes become your ground truth: after you recover the deleted files, you compare each recovered file's hash against this original list to prove the recovery is bit-for-bit identical. See Part 6 of the lab instructions.)
