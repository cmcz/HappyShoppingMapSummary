# How to Remove Data Files from Git History

If you want to completely remove `data/*.json` files from your git history to avoid merge conflicts:

## Option 1: Simple Removal (Recommended)
The files are already ignored by `.gitignore` and the workflow is fixed to handle untracked files.

```bash
# If data files are currently tracked, remove them:
git rm --cached data/*.json
git commit -m "Remove data files from git tracking"
git push
```

## Option 2: Complete History Cleanup (Nuclear Option)
⚠️ **Warning**: This rewrites git history and requires force push!

```bash
# Remove all data/*.json files from entire git history
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch data/*.json' \
  --prune-empty --tag-name-filter cat -- --all

# Force push (⚠️ WARNING: This rewrites history!)
git push origin --force --all
```

## What the Fixed Workflow Does

The updated workflow now:
1. ✅ Detects **both** tracked file changes AND new untracked files
2. ✅ Works when `data/*.json` files are in `.gitignore`
3. ✅ Still commits generated data files to the repository
4. ✅ No more "No changes detected" false positives

## Result
- No more merge conflicts from data files
- Workflow still publishes data for iOS app
- Cleaner git history focused on code changes