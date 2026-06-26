# bytejoin-cli

```text
=========================================================
                  bytejoin-cli

        local split-file merger for the terminal
=========================================================
```

A small local Python CLI that joins split files back together in order.

No uploads. No cloud. No external packages. It just reads part 1, then part 2, then part 3, and writes one output file.

For a longer bytejoin-cli walkthrough with example outputs and warning examples, read [GUIDE.md](GUIDE.md).

## What This Is

This is a generic file joiner.

It can merge split files such as:

```text
part1.pkg
part2.pkg
part3.pkg
```

```text
file_0.pkg
file_1.pkg
file_2.pkg
```

```text
archive.zip.001
archive.zip.002
archive.zip.003
```

It also works with other split binary chunks, for example `.bin`, `.iso.001`, `.7z.001`, `.rar` parts, video chunks, backup chunks, and similar files.

It does not understand the file format. It only joins bytes.

For this job, a local Python CLI is often nicer than a webapp or random `.exe`: there is no browser file-size weirdness, no installer, and the code is inspectable.

## What This Is Not

This tool does not:

- download anything
- repair broken files
- verify that a file is official
- guarantee that the merged output will be usable
- guarantee that the merged output will install, open, or work

If the parts are wrong, incomplete, corrupted, fake, out of order, or not meant to be joined this way, the output may be useless.

## Important Warning

Stuff can go wrong.

If the input files are corrupted, incomplete, in the wrong order, or not meant to be joined this way, the merged file can be broken. A broken merged file may fail to open, fail to install, crash another program, waste disk space, or need to be deleted and rebuilt.

bytejoin-cli tries to warn about obvious problems, but it cannot guarantee the final file is valid. You are responsible for checking your files, keeping backups when needed, and deciding whether the merged output is safe to use.

## Use Responsibly

Use this only with files you own or are authorized to process.

You are responsible for following any rules, licenses, terms, and laws that apply to your files.

Do not use this project with files you do not have permission to process.

This note is general information, not legal advice.

## Folder Layout

```text
bytejoin-cli/
  merge_parts.py
  START_HERE.bat
  README.md
  parts/
  demo_parts/
```

Use `parts` for your real files.

Use `demo_parts` only for the tiny included demo files.

## Simple Real File Guide

1. Open the project folder.

2. Open the `parts` folder.

3. Put all real split files in `parts`.

   Example:

   ```text
   parts/
     large_file_0.pkg
     large_file_1.pkg
     large_file_2.pkg
     large_file_3.pkg
     large_file_4.pkg
     large_file_5.pkg
   ```

4. Go back to the main project folder.

5. Double-click:

   ```text
   START_HERE.bat
   ```

   Or run:

   ```powershell
   py merge_parts.py
   ```

6. Choose:

   ```text
   1) Real files
   ```

7. Check the detected order.

   You should see something like:

   ```text
   Found 6 matching files

   OK 1/6 large_file_0.pkg (4.00 GB)
   OK 2/6 large_file_1.pkg (4.00 GB)
   OK 3/6 large_file_2.pkg (4.00 GB)
   OK 4/6 large_file_3.pkg (4.00 GB)
   OK 5/6 large_file_4.pkg (4.00 GB)
   OK 6/6 large_file_5.pkg (168.31 MB)
   ```

8. Check or rename the output.

   ```text
   Output filename:
   [large_file.pkg]
   ```

   Press Enter to accept.

   Or type a simpler name:

   ```text
   my_merged_file.pkg
   ```

9. When it says `Ready`, press Enter to begin.

10. Wait until it says:

    ```text
    Merge complete
    Output size matches expected size
    Done.
    ```

Do not close the window while it is merging.

## Demo Guide

The `demo_parts` folder contains tiny fake `.pkg` demo files.

They are not real game files. They are just text chunks named `.pkg` so you can test the app safely.

Run the demo:

```powershell
py merge_parts.py --demo
```

Preview the demo without writing anything:

```powershell
py merge_parts.py --demo --dry-run
```

Run the demo without prompts:

```powershell
py merge_parts.py --demo --yes --overwrite
```

The demo output is:

```text
demo_parts/merged.pkg
```

## Progress Bar

For big files, the tool updates about once per second.

It shows:

- current part
- current filename
- current file progress
- overall progress
- speed
- elapsed time
- estimated time remaining

Example:

```text
=========================================================
Part 2 of 6
File: large_file_1.pkg
Size: 4.00 GB
=========================================================

#################--------------  58.4 %

Current file:
2.34 GB / 4.00 GB

Overall:
6.34 GB / 20.16 GB

Speed:
842.00 MB/s

Elapsed:
00:01:28

Estimated remaining:
00:03:41
```

## Useful Commands

Use real files directly:

```powershell
py merge_parts.py --real
```

Use a custom folder:

```powershell
py merge_parts.py "D:\MyParts"
```

Use a specific pattern:

```powershell
py merge_parts.py --pattern "*.pkg"
```

Merge numbered archive parts:

```powershell
py merge_parts.py --pattern "*.001"
```

Merge binary chunks:

```powershell
py merge_parts.py --pattern "*.bin"
```

Choose the output filename immediately:

```powershell
py merge_parts.py --output final.pkg
```

Skip prompts:

```powershell
py merge_parts.py --yes
```

Overwrite an existing output:

```powershell
py merge_parts.py --overwrite
```

Calculate SHA-256 after merging:

```powershell
py merge_parts.py --sha256
```

Disable colors:

```powershell
py merge_parts.py --no-color
```

## About Paths

The script does not contain your personal Windows path.

It uses the folder where `merge_parts.py` is located. If you move the whole project somewhere else, `parts` and `demo_parts` move with it.

The CLI normally shows short paths like:

```text
parts
demo_parts
```

If you manually choose a folder outside the project, it may show the full path so you know exactly what folder is being used.

## Pre-Flight Checks

Before merging, the tool warns about common mistakes:

- missing part numbers
- duplicate part numbers
- odd numbering starts
- suspiciously small middle parts
- empty files

These checks make it safer for big files, but they cannot prove the contents are authentic or uncorrupted. For real integrity checking, compare against a trusted hash from the source.

## Requirements

- Python 3.8 or newer
- Windows, macOS, or Linux
- No external Python packages

## License

MIT License.
