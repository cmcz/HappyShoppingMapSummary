# Setup Instructions

## 🔑 GitHub Secrets Configuration

You need to add **ONE** secret to your GitHub repository:

### Required Secret:
- **Name**: `GEMINI_API_KEY`
- **Value**: Your Gemini API key (starts with something like `AIza...`)

### How to Add the Secret:

1. **Go to your repository** on GitHub.com
2. **Click "Settings"** tab (top navigation)
3. **Click "Secrets and variables"** → **"Actions"** (left sidebar)
4. **Click "New repository secret"**
5. **Enter the details**:
   - **Name**: `GEMINI_API_KEY` (exactly this name)
   - **Secret**: Paste your Gemini API key
6. **Click "Add secret"**

### ⚠️ Important Notes:

- **Secret name must be exactly**: `GEMINI_API_KEY`
- **DO NOT use names starting with**: `GITHUB_` (reserved by GitHub)
- **The `GITHUB_TOKEN` in the workflow** is automatically provided by GitHub - you don't need to add it manually

### 🧪 Test Your Setup:

1. **Go to "Actions" tab**
2. **Click "Process Happy Shopping PDFs"** 
3. **Click "Run workflow"**
4. **Check "Force processing"** for initial test
5. **Click "Run workflow"** button

If you see an error about API key, double-check the secret name is exactly `GEMINI_API_KEY`.

## 🚀 Manual Triggers

You can trigger the workflow anytime without waiting for 6 AM:

### Via GitHub Web:
1. Actions → Process Happy Shopping PDFs → Run workflow

### Via Git Push:
Push changes to `scripts/process_pdfs.py` or `.github/workflows/process-pdfs.yml`

## 📊 Expected Results

After successful run:
- New commit with updated `data/latest.json`
- GitHub release with processing details
- Your iOS app will fetch the new data

## 🔍 Troubleshooting

**"Secret names must not start with GITHUB_"**
- You tried to create a secret starting with `GITHUB_` - use `GEMINI_API_KEY` instead

**"GEMINI_API_KEY environment variable not set"**
- The secret wasn't added or has wrong name - must be exactly `GEMINI_API_KEY`

**"Invalid API key"**
- Check your Gemini API key is correct and has proper permissions