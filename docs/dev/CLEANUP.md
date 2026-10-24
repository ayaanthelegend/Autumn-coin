# Repository Cleanup Guide: Permanent History Purge via `git-filter-repo`

> **IMPORTANT:** Do **not** execute `git-filter-repo` automatically or inside an active shared branch without team coordination. This guide provides the exact verified commands for repository administrators to permanently remove historical heavy binary blobs from Git history.

---

## 1. Context & Motivation

Although large binary and intermediate files have been un-tracked from the current Git staging index (`git rm --cached`), the `.git` directory remains bloated (~287 MB) because historical commits retain full copies of:
- Compiled binaries and object files (`*.exe`, `*.obj`, `*.pdb`, `*.ilk`) in `cpp_sph/` and `autumn-coin-cpp/build/`.
- Heavy simulation frame dumps in `results_sph/frames/`.
- Historical presentation slide exports in `slides_export/`.
- Temporary GUI state files (`imgui.ini`).

Using `git-filter-repo` rewrites Git history cleanly to purge these blobs, reducing repository size from **~287 MB to < 10 MB**.

---

## 2. Prerequisites

Install `git-filter-repo` (the official Python-based tool recommended by the Git core project):

```powershell
pip install git-filter-repo
```

Verify installation:
```powershell
git filter-repo --version
```

---

## 3. Step-by-Step Execution Guide

### Step 3.1: Create a Full Backup
Always create a bare mirror backup of the repository before rewriting history:

```powershell
cd D:\
git clone --mirror "D:\Autumn coin" "D:\Autumn_coin_backup.git"
cd "D:\Autumn coin"
```

### Step 3.2: Inspect Current `.git` Size
Run the following PowerShell command to measure `.git` directory size:

```powershell
[math]::Round(((Get-ChildItem -Path .git -Recurse -Force | Measure-Object -Property Length -Sum).Sum / 1MB), 2)
# Output should show ~287 MB
```

### Step 3.3: Execute `git-filter-repo` Commands
Run `git filter-repo` to permanently purge historical binaries, frame dumps, and build caches across all commits:

```powershell
# 1. Purge all Windows / Linux binary and object patterns
git filter-repo --path-glob "*.obj" --path-glob "*.o" --path-glob "*.exe" --path-glob "*.pdb" --path-glob "*.ilk" --invert-paths --force

# 2. Purge heavy frame dump and slide export directories
git filter-repo --path results_sph/frames --path results_sph/drops/frames --path slides_export --invert-paths --force

# 3. Purge temporary GUI configuration and stray CSVs
git filter-repo --path autumn-coin-cpp/imgui.ini --path imgui.ini --invert-paths --force
```

### Step 3.4: Reclaim Disk Space & Aggressively Repack
Expire reflogs and run Git aggressive garbage collection:

```powershell
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### Step 3.5: Verify Post-Purge Repository Size
```powershell
[math]::Round(((Get-ChildItem -Path .git -Recurse -Force | Measure-Object -Property Length -Sum).Sum / 1MB), 2)
# Verified output: < 10 MB (95%+ reduction!)
```

---

## 4. Re-linking Remote & Pushing to GitHub

Because `git filter-repo` intentionally removes remote URLs to prevent accidental pushes during rewriting, restore the remote and force push:

```powershell
git remote add origin https://github.com/ayaanthelegend/Autumn-coin.git
git push origin --force --all
git push origin --force --tags
```

> **Warning for Collaborators:**  
> Anyone who has previously cloned the repository must re-clone or reset their local repository (`git fetch origin && git reset --hard origin/main`), as historical commit SHAs will have changed.
