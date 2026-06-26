# bytejoin-cli Full Guide

```text
=========================================================
                 bytejoin-cli - Full Guide
=========================================================
```

This guide shows the normal flow, demo flow, warning messages, and what the tool can and cannot verify.

## Short Version

For real files:

```text
1. Put split files in parts/
2. Run START_HERE.bat or py merge_parts.py
3. Choose Real files
4. Check the order
5. Accept or rename the output
6. Press Enter to merge
```

For demo files:

```powershell
py merge_parts.py --demo
```

## Example Real Folder

```text
parts/
  large_file_0.pkg
  large_file_1.pkg
  large_file_2.pkg
  large_file_3.pkg
  large_file_4.pkg
  large_file_5.pkg
```

## Example Preview

```text
=========================================================
                    bytejoin-cli v1.0
=========================================================

Scanning folder: parts

Detected extension: .pkg
Found 6 matching files

OK 1/6 large_file_0.pkg (4.00 GB)
OK 2/6 large_file_1.pkg (4.00 GB)
OK 3/6 large_file_2.pkg (4.00 GB)
OK 4/6 large_file_3.pkg (4.00 GB)
OK 5/6 large_file_4.pkg (4.00 GB)
OK 6/6 large_file_5.pkg (168.31 MB)

Combined size: 20.16 GB

Output:
large_file.pkg

Output filename:
[large_file.pkg]
```

Press Enter to accept the suggested name, or type your own:

```text
my_merged_file.pkg
```

## Example Progress

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

## Example Finished Output

```text
=========================================================
Merge complete
=========================================================

Output:
large_file.pkg

Size:
20.16 GB

Verified:
OK Output size matches expected size

Average speed:
935.00 MB/s

Time:
4m 31s

Done.
```

## Pre-Flight Warnings

The tool now checks for common mistakes before merging.

It can warn about:

- missing part numbers
- duplicate part numbers
- numbering that starts somewhere strange
- only some files having detectable part numbers
- a middle part being much smaller than the others
- empty files

Example missing part:

```text
parts/
  file_0.pkg
  file_1.pkg
  file_3.pkg
```

Warning:

```text
Pre-flight warnings:
! Missing part number(s): 2

If this looks wrong, stop now and fix the files before merging.
```

Example suspicious size:

```text
parts/
  file_0.pkg  4.00 GB
  file_1.pkg  168.31 MB
  file_2.pkg  4.00 GB
```

Warning:

```text
Pre-flight warnings:
! file_1.pkg is much smaller than the largest part, but it is not last.
```

This catches common "oops" cases. It does not prove that the file contents are correct.

## What Verification Means

At the end, the tool checks:

```text
combined input size == output size
```

This is useful. It catches many write failures and interrupted merges.

But it does not prove:

- the files are authentic
- the files are not corrupted
- the output will install or open
- the source was legal
- the package is valid

For real corruption checking, you need a trusted checksum from the source, such as SHA-256 or MD5. If you have one, use:

```powershell
py merge_parts.py --sha256
```

Then compare the printed hash with the trusted hash.

## File Types

The tool is universal because it only joins bytes.

Common examples:

```text
.pkg
.bin
.iso.001
.zip.001
.7z.001
.rar parts
backup chunks
video chunks
```

The important rule is simple:

```text
Only use it when the files are meant to be joined in order.
```

## Use Responsibly

You are responsible for what you merge and what you do with the result.

Use only files you own or are authorized to process.

This is general information, not legal advice.
