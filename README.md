# Happy Shopping Map Data Processing v2.0

This repository contains the intelligent automated PDF processing system for the Happy Shopping Certificate participating stores in Chuo City, Tokyo.

## 🚀 Key Features

- **🔍 Auto-Discovery**: Dynamically discovers latest PDF URLs from the source website
- **🤖 AI Processing**: Uses Gemini 2.0 Flash for intelligent data extraction
- **⚡ Smart Updates**: Only processes when PDFs actually change
- **🗺️ Geocoding**: Automatically adds coordinates to all shops
- **📱 iOS Integration**: Provides clean JSON API for mobile apps

## Architecture

- **Web Scraping**: Automatically discovers PDFs from `https://happy-kaimonoken.info/tenposearch/`
- **GitHub Actions**: Processes PDFs daily at 6:00 AM JST using Gemini AI
- **Change Detection**: Tracks PDF URLs and only processes when changed
- **Output**: Structured JSON data stored in `/data/` directory
- **iOS App**: Fetches processed JSON data instead of parsing PDFs directly

## Data Sources

The system automatically discovers and processes PDFs from:
- **Search Page**: `https://happy-kaimonoken.info/tenposearch/`
- **Small/Medium Retailers**: `tempo_*.pdf` files
- **Large Retailers**: `daiten_*.pdf` files

## Output Format

```json
{
  "lastUpdated": "2025-01-28T10:00:00Z",
  "dataVersion": "2.0",
  "totalShops": 150,
  "processedPDFs": ["https://...tempo_250714.pdf", "https://...daiten_250616.pdf"],
  "discoveredPDFs": ["https://...tempo_250714.pdf", "https://...daiten_250616.pdf"],
  "shops": [
    {
      "name": "店舗名",
      "address": "東京都中央区...",
      "phoneNumber": "03-1234-5678",
      "businessCategory": "コンビニ、雑貨",
      "businessCategoryCode": 1,
      "district": "銀座",
      "isLargeRetailer": false,
      "specialMarket": null,
      "certificateType": "中小小売店(全券種)",
      "coordinate": {
        "latitude": 35.6762,
        "longitude": 139.7649
      }
    }
  ],
  "processingMetadata": {
    "model": "gemini-2.0-flash-exp",
    "discoveryUrl": "https://happy-kaimonoken.info/tenposearch/",
    "processingTime": "2025-01-28T10:00:00Z"
  }
}
```

## 🛠️ Setup

1. **Fork this repository** to your GitHub account
2. **Set GitHub secret** `GEMINI_API_KEY` with your Gemini API key:
   - Go to Settings → Secrets and variables → Actions
   - Add secret named `GEMINI_API_KEY`
3. **GitHub Actions will automatically**:
   - Run daily at 6:00 AM JST (21:00 UTC)
   - Discover PDFs from the search page
   - Only process when PDFs change
   - Commit results to `/data/latest.json`
4. **iOS app integration**: 
   - Update repository name in app settings
   - App fetches from: `https://raw.githubusercontent.com/[username]/HappyShoppingMapSummary/main/data/latest.json`

## 🚀 Manual Processing

You can manually trigger processing:

```bash
# Force processing even if no changes
python scripts/process_pdfs.py --force

# Regular processing (only if URLs changed) 
python scripts/process_pdfs.py
```

Or use GitHub Actions:
- Go to **Actions** → **Process Happy Shopping PDFs** → **Run workflow**
- Toggle "Force processing" if needed

## 📊 Features

### Smart Discovery
- Scrapes `https://happy-kaimonoken.info/tenposearch/` for PDF links
- Handles dynamic file names (dates change frequently)
- Robust fallback to hardcoded URLs if scraping fails

### Change Detection
- Tracks processed URLs in `/data/last_processed_urls.json`
- Only processes when new PDFs are discovered
- Saves API costs and processing time

### AI Processing
- **Model**: gemini-2.0-flash-exp (latest and fastest)
- **Extraction**: Shop names, addresses, categories, phone numbers, certificate types
- **Certificate Types**: 
  - `tempo` PDFs → "中小小売店(全券種)" (Small/Medium Retailers - All Certificate Types)
  - `daiten` PDFs → "大規模小売店(青色券)" (Large Retailers - Blue Certificates)
- **Geocoding**: Adds coordinates using AI knowledge of Tokyo
- **Validation**: Data quality checks and cleanup

### iOS Integration
- Clean JSON API ready for mobile consumption
- Progress tracking and error handling
- Repository configuration in app settings
- Real-time data freshness indicators