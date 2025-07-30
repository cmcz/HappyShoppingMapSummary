#!/usr/bin/env python3
"""
PDF Processing Script for Happy Shopping Map
Uses Gemini AI to extract and structure shop data from PDFs
"""

import os
import json
import requests
import PyPDF2
from datetime import datetime, timezone
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import re
import sys
from bs4 import BeautifulSoup
import time

class PDFProcessor:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        # Using gemini-2.5-flash - newer model that might be more efficient
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Track API usage to avoid rate limits
        self.api_calls_made = 0
        self.max_daily_calls = 45  # Conservative limit for free tier (50 limit)
        
        # Base URL to scrape for PDF links
        self.search_url = "https://happy-kaimonoken.info/tenposearch/"
        
        # File to store last processed URLs - will be set to absolute path when needed
        self.url_cache_file = "data/last_processed_urls.json"
        
        # Districts in Chuo City
        self.districts = [
            "明石町", "入船", "勝どき", "京橋", "銀座", "新川", "日本橋", 
            "八重洲", "築地", "豊海町", "佃", "月島", "晴海", "東銀座"
        ]
        
        # Business categories mapping
        self.categories = {
            "コンビニ、雑貨": 1,
            "織物、衣類、身の回り品小売業": 2,
            "飲食料品小売業": 3,
            "自動車・オートバイ小売業": 4,
            "家具・建具・畳小売業": 5,
            "機械器具小売業": 6,
            "その他の小売業": 7,
            "宿泊業、飲食サービス業": 8,
            "サービス業（他に分類されないもの）": 9,
            "大規模小売店": 10
        }
        
        # Certificate type mapping based on PDF URL keywords
        self.certificate_types = {
            "tempo": "中小小売店(全券種)",
            "daiten": "大規模小売店(青色券)"
        }

    def discover_pdf_urls(self) -> List[str]:
        """Scrape the search page to find latest PDF URLs"""
        print(f"🔍 Discovering PDF URLs from: {self.search_url}")
        
        try:
            # Add headers to mimic a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            print("📡 Sending request to website...")
            response = requests.get(self.search_url, headers=headers, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'  # Ensure proper Japanese encoding
            
            print(f"✅ Received response: {response.status_code} ({len(response.text)} chars)")
            
            soup = BeautifulSoup(response.text, 'lxml')
            print(f"🔍 Parsing HTML with BeautifulSoup...")
            
            # Find PDF links - look for links containing 'tempo' or 'daiten' and ending with .pdf
            pdf_urls = []
            
            # Search for all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Check if it's a PDF link for our target files
                if (href.endswith('.pdf') and 
                    ('tempo' in href.lower() or 'daiten' in href.lower()) and
                    'wp-content/uploads' in href):
                    
                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        full_url = f"https://happy-kaimonoken.info{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = f"https://happy-kaimonoken.info/{href}"
                    
                    pdf_urls.append(full_url)
                    print(f"Found PDF: {full_url}")
            
            # Also search in script tags or data attributes that might contain PDF URLs
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Look for PDF URLs in JavaScript
                    pdf_matches = re.findall(r'https?://[^\s"\']+\.pdf', script.string)
                    for match in pdf_matches:
                        if ('tempo' in match.lower() or 'daiten' in match.lower()) and 'wp-content/uploads' in match:
                            if match not in pdf_urls:
                                pdf_urls.append(match)
                                print(f"Found PDF in script: {match}")
            
            # Remove duplicates and sort
            pdf_urls = list(set(pdf_urls))
            pdf_urls.sort()
            
            print(f"Discovered {len(pdf_urls)} PDF URLs")
            return pdf_urls
            
        except Exception as e:
            print(f"❌ Error discovering PDF URLs: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to default URLs if scraping fails
            print("🔄 Falling back to hardcoded PDF URLs...")
            fallback_urls = [
                "https://happy-kaimonoken.info/wp-content/uploads/2025/07/tempo_250714.pdf",
                "https://happy-kaimonoken.info/wp-content/uploads/2025/06/daiten_250616.pdf"
            ]
            
            for url in fallback_urls:
                print(f"   📄 Fallback URL: {url}")
            
            return fallback_urls

    def load_last_processed_urls(self) -> List[str]:
        """Load the last processed PDF URLs from cache"""
        try:
            # Use absolute path
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_file = os.path.join(repo_root, self.url_cache_file)
            
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('urls', [])
        except Exception as e:
            print(f"Error loading URL cache: {e}")
        return []

    def save_processed_urls(self, urls: List[str]) -> None:
        """Save the processed PDF URLs to cache"""
        try:
            # Use absolute path
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_file = os.path.join(repo_root, self.url_cache_file)
            
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            cache_data = {
                'urls': urls,
                'lastProcessed': datetime.now(timezone.utc).isoformat(),
                'count': len(urls)
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            print(f"Saved {len(urls)} URLs to cache: {cache_file}")
        except Exception as e:
            print(f"Error saving URL cache: {e}")

    def urls_have_changed(self, current_urls: List[str]) -> bool:
        """Check if the discovered URLs are different from last processed"""
        last_urls = self.load_last_processed_urls()
        current_set = set(current_urls)
        last_set = set(last_urls)
        
        if current_set != last_set:
            print("📋 URL changes detected:")
            
            new_urls = current_set - last_set
            if new_urls:
                print(f"  ➕ New URLs: {list(new_urls)}")
            
            removed_urls = last_set - current_set
            if removed_urls:
                print(f"  ➖ Removed URLs: {list(removed_urls)}")
            
            return True
        else:
            print("✅ No URL changes detected")
            return False

    def get_certificate_type(self, url: str) -> str:
        """Determine certificate type based on PDF URL"""
        url_lower = url.lower()
        
        if 'tempo' in url_lower:
            return self.certificate_types["tempo"]
        elif 'daiten' in url_lower:
            return self.certificate_types["daiten"]
        else:
            # Fallback logic based on other URL patterns
            if '中小' in url or 'small' in url_lower:
                return self.certificate_types["tempo"]
            elif '大規模' in url or 'large' in url_lower:
                return self.certificate_types["daiten"]
            else:
                # Default to small retailers if uncertain
                return self.certificate_types["tempo"]

    def download_pdf(self, url: str) -> bytes:
        """Download PDF from URL"""
        print(f"Downloading PDF: {url}")
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.content

    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content"""
        print(f"📄 Extracting text from PDF ({len(pdf_content)} bytes)...")
        try:
            from io import BytesIO
            pdf_file = BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            print(f"📖 PDF has {len(pdf_reader.pages)} pages")
            
            text = ""
            for i, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                text += page_text + "\n"
                print(f"  Page {i+1}: {len(page_text)} characters extracted")
                
                # Show sample of first page for debugging
                if i == 0 and page_text:
                    sample = page_text[:200].replace('\n', ' ')
                    print(f"  📝 Sample text: {sample}...")
            
            print(f"✅ Total extracted: {len(text)} characters")
            return text
        except Exception as e:
            print(f"❌ Error extracting PDF text: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def process_with_gemini(self, text: str, is_large_retailer: bool = False, certificate_type: str = "") -> List[Dict[str, Any]]:
        """Process extracted text with Gemini AI"""
        print(f"🤖 Processing {len(text)} characters with Gemini AI")
        print(f"   📋 Large retailer: {is_large_retailer}")
        print(f"   🏷️ Certificate type: {certificate_type}")
        
        if len(text) < 50:
            print(f"⚠️  Text too short ({len(text)} chars), might indicate extraction issues")
            print(f"   Raw text: '{text[:100]}'")
        
        prompt = f"""
Please extract shop information from this Japanese PDF text and return it as a JSON array. Each shop should have the following structure:

{{
  "name": "店舗名",
  "address": "住所（中央区の後の部分のみ）",
  "phoneNumber": "電話番号（あれば）",
  "businessCategory": "業種カテゴリ",
  "businessCategoryCode": 数字コード,
  "district": "地区名",
  "isLargeRetailer": {str(is_large_retailer).lower()},
  "specialMarket": "特別市場名（築地魚河岸など、あれば）",
  "certificateType": "{certificate_type}"
}}

Business category codes:
- コンビニ、雑貨: 1
- 織物、衣類、身の回り品小売業: 2
- 飲食料品小売業: 3
- 自動車・オートバイ小売業: 4
- 家具・建具・畳小売業: 5
- 機械器具小売業: 6
- その他の小売業: 7
- 宿泊業、飲食サービス業: 8
- サービス業（他に分類されないもの）: 9
- 大規模小売店: 10

Districts in 中央区: {', '.join(self.districts)}

Rules:
1. Extract only actual shop names and data, ignore headers and category titles
2. For address, include only the part after "中央区"
3. Detect district from address if possible
4. Phone numbers should be in format like "03-1234-5678"
5. Return only valid JSON array, no other text
6. If special market like "築地魚河岸" is mentioned, include it

Text to process:
{text[:6000]}  # Reduce text length to use fewer tokens
"""

        # Check API quota before making request
        if self.api_calls_made >= self.max_daily_calls:
            print(f"❌ Daily API quota reached ({self.api_calls_made}/{self.max_daily_calls})")
            return []
        
        try:
            print(f"🔄 Sending request to AI... (call {self.api_calls_made + 1}/{self.max_daily_calls})")
            
            # Implement exponential backoff for retries
            max_retries = 3
            base_delay = 10  # Start with 10 seconds
            
            for attempt in range(max_retries):
                try:
                    response = self.model.generate_content(prompt)
                    result_text = response.text.strip()
                    self.api_calls_made += 1
                    print(f"✅ API call successful (total calls: {self.api_calls_made})")
                    break
                    
                except Exception as api_error:
                    error_str = str(api_error).lower()
                    if any(keyword in error_str for keyword in ["429", "quota", "overloaded", "503", "unavailable"]):
                        # Handle rate limits, quotas, and server overload
                        retry_delay = base_delay * (2 ** attempt)  # Exponential backoff
                        
                        # Try to extract suggested delay from error message
                        import re
                        delay_match = re.search(r'retry_delay.*?seconds: (\d+)', str(api_error))
                        if delay_match:
                            suggested_delay = int(delay_match.group(1))
                            retry_delay = max(retry_delay, suggested_delay + 5)  # Add buffer
                        
                        # For server overload, use longer delays
                        if "overloaded" in error_str or "503" in error_str:
                            retry_delay = max(retry_delay, 60)  # At least 1 minute for overload
                        
                        if attempt < max_retries - 1:
                            if "overloaded" in error_str:
                                print(f"⚠️  Gemini server overloaded (attempt {attempt + 1}/{max_retries})")
                            else:
                                print(f"⚠️  Rate limit hit (attempt {attempt + 1}/{max_retries})")
                            print(f"⏳ Waiting {retry_delay} seconds before retry...")
                            time.sleep(retry_delay)
                        else:
                            print(f"❌ Final failure after {max_retries} attempts: {api_error}")
                            return []
                    else:
                        # Non-retryable error
                        print(f"❌ Non-retryable error: {api_error}")
                        raise api_error
            
            print(f"📥 Received response ({len(result_text)} chars)")
            
            # Show first part of response for debugging
            if result_text:
                preview = result_text[:300].replace('\n', ' ')
                print(f"   📝 Response preview: {preview}...")
            
            # Clean up the response to ensure it's valid JSON
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
                print("🧹 Cleaned markdown code blocks")
            
            # Parse JSON
            print("🔍 Parsing JSON...")
            shops = json.loads(result_text)
            
            print(f"✅ Parsed {len(shops)} raw entries")
            
            # Validate and clean data
            cleaned_shops = []
            for i, shop in enumerate(shops):
                if isinstance(shop, dict) and shop.get('name'):
                    # Ensure required fields with safe string handling
                    name = shop.get('name') or ''
                    address = shop.get('address') or ''
                    district = shop.get('district') or ''
                    
                    cleaned_shop = {
                        "name": name.strip() if name else '',
                        "address": address.strip() if address else '',
                        "phoneNumber": shop.get('phoneNumber') if shop.get('phoneNumber') else None,
                        "businessCategory": shop.get('businessCategory', 'その他の小売業'),
                        "businessCategoryCode": shop.get('businessCategoryCode', 7),
                        "district": district.strip() if district else '',
                        "isLargeRetailer": is_large_retailer,
                        "specialMarket": shop.get('specialMarket') if shop.get('specialMarket') else None,
                        "certificateType": shop.get('certificateType', certificate_type)
                    }
                    cleaned_shops.append(cleaned_shop)
                    print(f"   ✅ Shop {i+1}: {cleaned_shop['name']}")
                else:
                    print(f"   ❌ Skipped invalid entry {i+1}: {shop}")
            
            print(f"🎉 Final result: {len(cleaned_shops)} valid shops extracted")
            return cleaned_shops
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"   Error at line {e.lineno}, column {e.colno}")
            print(f"   Raw response length: {len(result_text)} chars")
            
            # Show context around the error
            if hasattr(e, 'pos'):
                start = max(0, e.pos - 100)
                end = min(len(result_text), e.pos + 100)
                error_context = result_text[start:end]
                print(f"   Error context: ...{error_context}...")
            
            # Try multiple fix strategies
            print("🔧 Attempting to fix JSON...")
            
            fixed_shops = []
            
            # Strategy 1: Find and fix truncated JSON at specific patterns
            strategies = [
                # Look for incomplete object at the end - be more specific
                (r',\s*$', ']'),  # Trailing comma
                (r',\s*\{\s*"[^"]*"\s*:\s*"[^"]*"?\s*[^}]*$', ']', 'Remove incomplete trailing object'),
                (r'\{\s*"[^"]*"\s*:\s*"[^"]*"?\s*[^}]*$', ']', 'Remove incomplete final object'),
                (r'"[^"]*$', '"]', 'Complete incomplete string'),
                (r':\s*"[^"]*$', ': ""}]', 'Complete incomplete property value')
            ]
            
            for strategy_idx, strategy in enumerate(strategies):
                try:
                    import re
                    
                    if len(strategy) == 3:
                        pattern, replacement, description = strategy
                        print(f"   🔧 Strategy {strategy_idx + 1}: {description}")
                    else:
                        pattern, replacement = strategy
                        print(f"   🔧 Strategy {strategy_idx + 1}: Pattern fix")
                    
                    # Apply the fix
                    fixed_text = re.sub(pattern, replacement, result_text, flags=re.MULTILINE | re.DOTALL)
                    
                    if fixed_text != result_text:
                        print(f"      Applied fix, testing...")
                        shops = json.loads(fixed_text)
                        print(f"      ✅ Strategy {strategy_idx + 1} worked! Parsed {len(shops)} entries")
                        fixed_shops = shops
                        break
                    else:
                        print(f"      No changes made with this pattern")
                        
                except Exception as strategy_error:
                    print(f"      ❌ Strategy {strategy_idx + 1} failed: {strategy_error}")
                    continue
            
            # Strategy 2: Smart truncation - find the last complete object
            if not fixed_shops:
                try:
                    print("   🔧 Trying smart truncation...")
                    
                    # Look for the last complete object by finding closing braces
                    # We need to be more careful about JSON structure
                    
                    # Count braces to find balanced objects
                    brace_count = 0
                    last_complete_pos = -1
                    
                    # Start from the beginning and track balanced braces
                    for i, char in enumerate(result_text):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            # If we're back to 0 braces after seeing an object, this might be a complete object
                            if brace_count == 0:
                                # Look ahead to see if there's a comma or array end
                                next_chars = result_text[i+1:i+10].strip()
                                if next_chars.startswith(',') or next_chars.startswith(']') or i == len(result_text) - 1:
                                    last_complete_pos = i
                    
                    if last_complete_pos > 0:
                        # Truncate at the last complete object and add closing bracket
                        truncated_text = result_text[:last_complete_pos + 1]
                        
                        # Check if we need to add array closing
                        if not truncated_text.rstrip().endswith(']'):
                            # Count how many objects we have by looking for complete objects
                            if ',' in truncated_text:
                                fixed_json = truncated_text + '\n]'
                            else:
                                # Single object, wrap in array
                                fixed_json = '[' + truncated_text + ']'
                        else:
                            fixed_json = truncated_text
                            
                        print(f"      Trying smart truncation at position {last_complete_pos}")
                        shops = json.loads(fixed_json)
                        print(f"      ✅ Smart truncation worked! Parsed {len(shops)} entries")
                        fixed_shops = shops
                        
                except Exception as smart_error:
                    print(f"      ❌ Smart truncation failed: {smart_error}")
                    
                    # Fallback to simple pattern matching
                    try:
                        print("      🔧 Trying simple pattern truncation...")
                        
                        # Find the last complete object ending with simple patterns
                        patterns_to_try = [
                            '  }\n]',  # Complete array end
                            '  }',     # Object end with indent
                            '}',       # Simple object end
                            '  },',    # Object end with comma and indent  
                            '},',      # Object end with comma
                        ]
                        
                        for pattern in patterns_to_try:
                            last_complete = result_text.rfind(pattern)
                            if last_complete > 0:
                                # Calculate proper end position
                                if pattern.endswith(']'):
                                    # Already has array end
                                    fixed_json = result_text[:last_complete + len(pattern)]
                                else:
                                    # Add array end
                                    end_pos = last_complete + len(pattern.rstrip(','))
                                    fixed_json = result_text[:end_pos] + '\n]'
                                
                                print(f"         Trying pattern '{pattern}' at pos {last_complete}")
                                shops = json.loads(fixed_json)
                                print(f"         ✅ Pattern truncation worked! Parsed {len(shops)} entries")
                                fixed_shops = shops
                                break
                                
                    except Exception as pattern_error:
                        print(f"         ❌ Pattern truncation failed: {pattern_error}")
            
            # Strategy 3: Extract individual JSON objects
            if not fixed_shops:
                try:
                    print("   🔧 Trying individual object extraction...")
                    import re
                    
                    # Multiple patterns to catch different object formats
                    patterns = [
                        # Standard complete objects
                        r'\{\s*"name"\s*:\s*"[^"]+"\s*,(?:[^{}]|{[^{}]*})*\}',
                        # Objects that might span multiple lines
                        r'\{\s*"name"\s*:\s*"[^"]+"\s*,[\s\S]*?\n\s*\}',
                        # More lenient pattern for incomplete objects we can fix
                        r'\{\s*"name"\s*:\s*"[^"]+"\s*,[\s\S]*?(?=\s*\{|\s*\]|\s*$)'
                    ]
                    
                    extracted_shops = []
                    
                    for pattern_idx, pattern in enumerate(patterns):
                        matches = re.findall(pattern, result_text, re.MULTILINE)
                        print(f"      Pattern {pattern_idx + 1}: Found {len(matches)} potential objects")
                        
                        for match_idx, match in enumerate(matches):
                            try:
                                # Clean up the match
                                clean_match = match.strip()
                                
                                # Ensure it ends with }
                                if not clean_match.endswith('}'):
                                    # Try to find where it should end
                                    if '"certificateType"' in clean_match:
                                        # Find the end of certificateType and add closing
                                        cert_end = clean_match.rfind('"')
                                        if cert_end > 0:
                                            clean_match = clean_match[:cert_end + 1] + '\n  }'
                                    else:
                                        clean_match += '\n  }'
                                
                                # Try to parse
                                shop = json.loads(clean_match)
                                if shop.get('name'):  # Ensure it has a name
                                    extracted_shops.append(shop)
                                    print(f"         ✅ Object {match_idx + 1}: {shop['name']}")
                                    
                            except json.JSONDecodeError as parse_error:
                                print(f"         ❌ Object {match_idx + 1} parse failed: {parse_error}")
                                # Try to fix common issues
                                try:
                                    # Remove trailing commas
                                    fixed_match = re.sub(r',(\s*[}\]])', r'\1', clean_match)
                                    shop = json.loads(fixed_match)
                                    if shop.get('name'):
                                        extracted_shops.append(shop)
                                        print(f"         🔧 Fixed Object {match_idx + 1}: {shop['name']}")
                                except:
                                    continue
                            except Exception as other_error:
                                print(f"         ❌ Object {match_idx + 1} failed: {other_error}")
                                continue
                    
                    # Remove duplicates based on name
                    if extracted_shops:
                        seen_names = set()
                        unique_shops = []
                        for shop in extracted_shops:
                            name = shop.get('name', '')
                            if name and name not in seen_names:
                                seen_names.add(name)
                                unique_shops.append(shop)
                        
                        print(f"      ✅ Extracted {len(unique_shops)} unique objects")
                        fixed_shops = unique_shops
                        
                except Exception as extract_error:
                    print(f"      ❌ Individual extraction failed: {extract_error}")
            
            # If we got some shops, validate them
            if fixed_shops:
                cleaned_shops = []
                for i, shop in enumerate(fixed_shops):
                    if isinstance(shop, dict) and shop.get('name'):
                        cleaned_shop = {
                            "name": shop.get('name', '').strip(),
                            "address": shop.get('address', '').strip(),
                            "phoneNumber": shop.get('phoneNumber') if shop.get('phoneNumber') else None,
                            "businessCategory": shop.get('businessCategory', 'その他の小売業'),
                            "businessCategoryCode": shop.get('businessCategoryCode', 7),
                            "district": shop.get('district'),
                            "isLargeRetailer": is_large_retailer,
                            "specialMarket": shop.get('specialMarket') if shop.get('specialMarket') else None,
                            "certificateType": shop.get('certificateType', certificate_type)
                        }
                        cleaned_shops.append(cleaned_shop)
                        print(f"   ✅ Shop {i+1}: {cleaned_shop['name']}")
                
                print(f"🎉 Recovered: {len(cleaned_shops)} valid shops")
                return cleaned_shops
            else:
                print("   ❌ All fix strategies failed")
                return []
        except Exception as e:
            print(f"❌ Error processing with Gemini: {e}")
            import traceback
            traceback.print_exc()
            return []

    def add_coordinates_with_gemini(self, shops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add coordinate estimates using Gemini AI's knowledge of Tokyo addresses"""
        print("Adding coordinate estimates with Gemini AI...")
        
        # Process in batches to avoid token limits
        batch_size = 10
        result_shops = []
        
        for i in range(0, len(shops), batch_size):
            batch = shops[i:i+batch_size]
            
            prompt = f"""
Given these shop addresses in 中央区 (Chuo City), Tokyo, please add estimated coordinates.
Return the same JSON with added "coordinate" field containing latitude and longitude.

Use your knowledge of Tokyo geography to provide reasonable estimates for these addresses:

{json.dumps(batch, ensure_ascii=False, indent=2)}

Return format:
{{
  "name": "店舗名",
  "address": "住所",
  "phoneNumber": "電話番号",
  "businessCategory": "業種",
  "businessCategoryCode": 1,
  "district": "地区",
  "isLargeRetailer": false,
  "specialMarket": null,
  "certificateType": "中小小売店(全券種)",
  "coordinate": {{
    "latitude": 35.6762,
    "longitude": 139.7649
  }}
}}

Rules:
1. 中央区 coordinates are roughly: latitude 35.66-35.69, longitude 139.76-139.79
2. 銀座 is around 35.6719, 139.7658
3. 築地 is around 35.6654, 139.7707
4. 日本橋 is around 35.6833, 139.7736
5. If you can't determine location, use central Chuo coordinates: 35.6762, 139.7649
6. Return only valid JSON array
"""

            try:
                print(f"      ⏳ Processing batch {(i//batch_size) + 1} of {(len(shops) + batch_size - 1)//batch_size}")
                response = self.model.generate_content(prompt)
                result_text = response.text.strip()
                
                if result_text.startswith('```json'):
                    result_text = result_text.replace('```json', '').replace('```', '').strip()
                
                batch_with_coords = json.loads(result_text)
                result_shops.extend(batch_with_coords)
                
                # Add delay between batches to avoid rate limits
                if i + batch_size < len(shops):  # Don't delay after last batch
                    print(f"      ⏳ Waiting 5 seconds to avoid API rate limits...")
                    time.sleep(5)
                
            except Exception as e:
                print(f"Error adding coordinates for batch: {e}")
                # Fallback: add default coordinates
                for shop in batch:
                    shop["coordinate"] = {
                        "latitude": 35.6762,
                        "longitude": 139.7649
                    }
                    # Ensure certificate type is preserved
                    if "certificateType" not in shop:
                        shop["certificateType"] = "中小小売店(全券種)"  # Default
                result_shops.extend(batch)
                
                # Still add delay even on error to avoid further rate limit issues
                if i + batch_size < len(shops):
                    print(f"      ⏳ Waiting 5 seconds after error to avoid further rate limits...")
                    time.sleep(5)
        
        print(f"Added coordinates to {len(result_shops)} shops")
        return result_shops
    
    def add_default_coordinates(self, shops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add default coordinate estimates based on district names to avoid API usage"""
        print("Adding default coordinate estimates based on districts...")
        
        # District coordinates for Chuo City areas
        district_coords = {
            "明石町": {"latitude": 35.6640, "longitude": 139.7720},
            "入船": {"latitude": 35.6640, "longitude": 139.7760},
            "勝どき": {"latitude": 35.6590, "longitude": 139.7780},
            "京橋": {"latitude": 35.6750, "longitude": 139.7700},
            "銀座": {"latitude": 35.6719, "longitude": 139.7658},
            "新川": {"latitude": 35.6800, "longitude": 139.7800},
            "日本橋": {"latitude": 35.6833, "longitude": 139.7736},
            "八重洲": {"latitude": 35.6800, "longitude": 139.7650},
            "築地": {"latitude": 35.6654, "longitude": 139.7707},
            "豊海町": {"latitude": 35.6550, "longitude": 139.7650},
            "佃": {"latitude": 35.6600, "longitude": 139.7820},
            "月島": {"latitude": 35.6630, "longitude": 139.7850},
            "晴海": {"latitude": 35.6550, "longitude": 139.7900},
            "東銀座": {"latitude": 35.6690, "longitude": 139.7680}
        }
        
        # Default central Chuo coordinates
        default_coord = {"latitude": 35.6762, "longitude": 139.7649}
        
        for shop in shops:
            district = shop.get('district', '')
            
            # Try to match district
            coord = default_coord.copy()
            if district in district_coords:
                coord = district_coords[district].copy()
                print(f"   📍 {shop.get('name', 'Unknown')}: {district} -> {coord['latitude']}, {coord['longitude']}")
            else:
                # Try partial matching for districts
                for known_district, known_coord in district_coords.items():
                    if known_district in district or district in known_district:
                        coord = known_coord.copy()
                        print(f"   📍 {shop.get('name', 'Unknown')}: {district} (matched {known_district}) -> {coord['latitude']}, {coord['longitude']}")
                        break
                else:
                    print(f"   📍 {shop.get('name', 'Unknown')}: {district} (default) -> {coord['latitude']}, {coord['longitude']}")
            
            shop["coordinate"] = coord
        
        print(f"Added default coordinates to {len(shops)} shops")
        return shops
    
    def add_coordinates_with_geocoding(self, shops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add coordinates using Google Maps Geocoding API (excellent for Japanese addresses)"""
        print("Adding coordinates using Google Maps Geocoding API...")
        
        # District coordinates as fallback
        district_coords = {
            "明石町": {"latitude": 35.6640, "longitude": 139.7720},
            "入船": {"latitude": 35.6640, "longitude": 139.7760},
            "勝どき": {"latitude": 35.6590, "longitude": 139.7780},
            "京橋": {"latitude": 35.6750, "longitude": 139.7700},
            "銀座": {"latitude": 35.6719, "longitude": 139.7658},
            "新川": {"latitude": 35.6800, "longitude": 139.7800},
            "日本橋": {"latitude": 35.6833, "longitude": 139.7736},
            "八重洲": {"latitude": 35.6800, "longitude": 139.7650},
            "築地": {"latitude": 35.6654, "longitude": 139.7707},
            "豊海町": {"latitude": 35.6550, "longitude": 139.7650},
            "佃": {"latitude": 35.6600, "longitude": 139.7820},
            "月島": {"latitude": 35.6630, "longitude": 139.7850},
            "晴海": {"latitude": 35.6550, "longitude": 139.7900},
            "東銀座": {"latitude": 35.6690, "longitude": 139.7680}
        }
        
        default_coord = {"latitude": 35.6762, "longitude": 139.7649}
        
        successful_geocodes = 0
        failed_geocodes = 0
        google_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        
        # Debug: Check all environment variables related to Google Maps
        print("🔍 Debugging Google Maps API key access:")
        print(f"   GOOGLE_MAPS_API_KEY exists: {google_api_key is not None}")
        if google_api_key:
            print(f"   API key length: {len(google_api_key)} chars")
            print(f"   API key starts with: {google_api_key[:10]}...")
            print("🔑 Google Maps API key found - using real geocoding")
        else:
            print("⚠️  No Google Maps API key - using district-based fallbacks only")
            print("   Make sure GOOGLE_MAPS_API_KEY is set in GitHub repository secrets")
        
        for i, shop in enumerate(shops):
            address = shop.get('address') or ''
            district = shop.get('district') or ''
            name = shop.get('name', 'Unknown')
            
            # Safely strip strings
            address = address.strip() if address else ''
            district = district.strip() if district else ''
            
            # Create full address for geocoding
            full_address = f"{address}, 中央区, 東京都, 日本" if address else f"{district}, 中央区, 東京都, 日本"
            
            # Only show progress every 10 shops when using fallbacks
            if google_api_key or (i + 1) % 10 == 0 or i == 0 or i == len(shops) - 1:
                print(f"   🔍 {i+1}/{len(shops)}: {name}")
                if google_api_key:
                    print(f"      Address: {full_address}")
            
            # Try geocoding with Google Maps API (requires API key)
            coord = None
            
            if google_api_key:
                try:
                    import urllib.parse
                    import urllib.request
                    import json
                    
                    # Encode the address for URL
                    encoded_address = urllib.parse.quote(full_address)
                    
                    # Google Maps Geocoding API endpoint
                    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={google_api_key}"
                    
                    # Make request with timeout
                    with urllib.request.urlopen(url, timeout=10) as response:
                        data = json.loads(response.read().decode())
                        
                        if data['status'] == 'OK' and data['results']:
                            result = data['results'][0]
                            location = result['geometry']['location']
                            lat = float(location['lat'])
                            lon = float(location['lng'])
                            
                            # Validate coordinates are in Tokyo area
                            if 35.6 <= lat <= 35.8 and 139.6 <= lon <= 139.9:
                                coord = {"latitude": lat, "longitude": lon}
                                successful_geocodes += 1
                                print(f"      ✅ Geocoded: {lat:.4f}, {lon:.4f}")
                            else:
                                print(f"      ⚠️  Coordinates outside Tokyo area: {lat}, {lon}")
                        else:
                            print(f"      ❌ No geocoding results: {data.get('status', 'unknown')}")
                            
                except Exception as e:
                    print(f"      ❌ Geocoding error: {e}")
                    failed_geocodes += 1
            else:
                # No API key - silently use fallbacks
                failed_geocodes += 1
            
            # Fallback to district coordinates if geocoding failed
            if coord is None:
                if district in district_coords:
                    coord = district_coords[district].copy()
                    if google_api_key:  # Only log if we tried real geocoding
                        print(f"      📍 Using district default: {district}")
                else:
                    # Try partial matching
                    for known_district, known_coord in district_coords.items():
                        if known_district in district or district in known_district:
                            coord = known_coord.copy()
                            if google_api_key:
                                print(f"      📍 Using matched district: {known_district}")
                            break
                    else:
                        coord = default_coord.copy()
                        if google_api_key:
                            print(f"      📍 Using central default")
            
            shop["coordinate"] = coord
            
            # Rate limiting for Google Maps API (50 requests per second, but be conservative)
            if i < len(shops) - 1 and google_api_key:  # Don't sleep after last request or if no API key
                time.sleep(0.1)  # 10 requests per second to be safe
        
        print(f"\n📊 Geocoding results:")
        print(f"   ✅ Successful: {successful_geocodes}")
        print(f"   ❌ Failed: {failed_geocodes}")
        print(f"   📍 Using fallbacks: {len(shops) - successful_geocodes}")
        
        return shops

    def process_all_pdfs(self, force: bool = False) -> Optional[Dict[str, Any]]:
        """Process all PDFs and return structured data"""
        print("🔍 Starting PDF discovery and processing...")
        
        # Discover current PDF URLs
        current_urls = self.discover_pdf_urls()
        
        if not current_urls:
            print("❌ No PDF URLs discovered")
            return None
        
        # Check if URLs have changed (unless forced)
        if not force and not self.urls_have_changed(current_urls):
            print("⏭️  No changes detected, skipping processing")
            return None
        
        print(f"🚀 Processing {len(current_urls)} PDFs...")
        all_shops = []
        processed_urls = []
        
        for url in current_urls:
            try:
                print(f"\n📄 Processing: {url}")
                
                # Download PDF
                pdf_content = self.download_pdf(url)
                
                # Extract text
                text = self.extract_text_from_pdf(pdf_content)
                if not text.strip():
                    print(f"⚠️  No text extracted from {url}")
                    continue
                
                # Determine certificate type and retailer type based on URL
                certificate_type = self.get_certificate_type(url)
                is_large_retailer = 'daiten' in url.lower()
                
                print(f"🏷️  Certificate type: {certificate_type}")
                
                # Process with Gemini
                shops = self.process_with_gemini(text, is_large_retailer, certificate_type)
                all_shops.extend(shops)
                processed_urls.append(url)
                
                print(f"✅ Extracted {len(shops)} shops from {url}")
                
                # Longer delay to avoid rate limits
                print("⏳ Waiting 3 seconds to avoid API rate limits...")
                time.sleep(3)
                
            except Exception as e:
                print(f"❌ Error processing {url}: {e}")
                continue
        
        if not all_shops:
            print("❌ No shops extracted from any PDFs")
            return None
        
        print(f"\n🗺️  Adding coordinates to {len(all_shops)} shops...")
        # Use geocoding service instead of AI for accurate coordinates
        all_shops = self.add_coordinates_with_geocoding(all_shops)
        
        # Save processed URLs to cache
        self.save_processed_urls(current_urls)
        
        # Create final output
        output = {
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "dataVersion": "2.0",  # Upgraded version with dynamic URL discovery
            "totalShops": len(all_shops),
            "processedPDFs": processed_urls,
            "discoveredPDFs": current_urls,
            "shops": all_shops,
            "processingMetadata": {
                "model": "gemini-2.5-flash",
                "discoveryUrl": self.search_url,
                "processingTime": datetime.now(timezone.utc).isoformat(),
                "apiCallsUsed": self.api_calls_made,
                "coordinateMethod": "google-maps-geocoding"
            }
        }
        
        print(f"✅ Processing complete! Generated data for {len(all_shops)} shops")
        return output

def main():
    print("🤖 Happy Shopping PDF Processor v2.0")
    print("=" * 50)
    
    # Get API key from environment
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable not set")
        sys.exit(1)
    
    # Check if we should force processing
    force_processing = '--force' in sys.argv or os.getenv('FORCE_PROCESSING', '').lower() == 'true'
    if force_processing:
        print("🔄 Force processing enabled")
    
    # Create processor and run
    processor = PDFProcessor(api_key)
    
    try:
        result = processor.process_all_pdfs(force=force_processing)
        
        if result is None:
            print("⏭️  No processing needed - PDFs haven't changed")
            print("💡 Use --force flag or set FORCE_PROCESSING=true to force processing")
            return
        
        # Ensure data directory exists - use absolute path from repo root
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(repo_root, 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        print(f"📁 Repository root: {repo_root}")
        print(f"📁 Data directory: {data_dir}")
        
        # Save results
        output_file = os.path.join(data_dir, 'latest.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n🎉 Processing complete!")
        print(f"📄 Processed {len(result.get('processedPDFs', []))} PDFs")
        print(f"🔍 Discovered {len(result.get('discoveredPDFs', []))} PDF URLs")
        print(f"🏪 Extracted {result['totalShops']} shops")
        print(f"💾 Saved to {output_file}")
        print(f"🤖 Used model: {result.get('processingMetadata', {}).get('model', 'unknown')}")
        
        # Verify the file was actually written
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ File verified: {output_file} ({file_size} bytes)")
            
            # Show first few lines to verify content
            with open(output_file, 'r', encoding='utf-8') as f:
                first_lines = f.read(500)
                print(f"📝 File content preview: {first_lines}...")
        else:
            print(f"❌ File NOT found at: {output_file}")
            print(f"📁 Current working directory: {os.getcwd()}")
            print(f"📁 Files in current directory: {os.listdir('.')}")
        
        # Also save with timestamp for history
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        history_file = os.path.join(data_dir, f'shops_{timestamp}.json')
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"📚 Backup saved to {history_file}")
        
        # Set output for GitHub Actions
        if os.getenv('GITHUB_ACTIONS'):
            with open(os.getenv('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
                f.write(f"shops_count={result['totalShops']}\n")
                f.write(f"pdfs_processed={len(result.get('processedPDFs', []))}\n")
                f.write("data_updated=true\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()