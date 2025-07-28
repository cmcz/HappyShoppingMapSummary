#!/usr/bin/env python3
"""
Debug script to test PDF processing without using API credits
"""

import os
import sys
import requests
from process_pdfs import PDFProcessor

def test_url_discovery():
    """Test URL discovery without API key"""
    print("🧪 Testing URL discovery...")
    
    processor = PDFProcessor("dummy_key")  # Don't need real key for URL discovery
    urls = processor.discover_pdf_urls()
    
    print(f"✅ Discovery test results:")
    print(f"   Found {len(urls)} URLs:")
    for i, url in enumerate(urls):
        print(f"   {i+1}. {url}")
    
    return urls

def test_pdf_download(url):
    """Test PDF download and basic info"""
    print(f"\n🧪 Testing PDF download from: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        print(f"✅ Download successful:")
        print(f"   Status: {response.status_code}")
        print(f"   Size: {len(response.content)} bytes")
        print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
        
        # Check if it's actually a PDF
        if response.content.startswith(b'%PDF'):
            print("✅ File appears to be a valid PDF")
            return response.content
        else:
            print("❌ File does not appear to be a PDF")
            print(f"   First 100 bytes: {response.content[:100]}")
            return None
            
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return None

def test_pdf_text_extraction(pdf_content):
    """Test PDF text extraction"""
    print(f"\n🧪 Testing PDF text extraction...")
    
    processor = PDFProcessor("dummy_key")
    text = processor.extract_text_from_pdf(pdf_content)
    
    if text:
        print(f"✅ Text extraction successful:")
        print(f"   Length: {len(text)} characters")
        print(f"   First 300 chars: {text[:300]}")
        
        # Look for Japanese text
        japanese_chars = sum(1 for c in text if ord(c) > 127)
        print(f"   Japanese characters: {japanese_chars}")
        
        return text
    else:
        print("❌ No text extracted")
        return None

def main():
    print("🔧 Happy Shopping PDF Processor - Debug Mode")
    print("=" * 60)
    
    # Test 1: URL Discovery
    urls = test_url_discovery()
    
    if not urls:
        print("❌ No URLs discovered, cannot continue")
        return
    
    # Test 2: Download first PDF
    pdf_content = test_pdf_download(urls[0])
    
    if not pdf_content:
        print("❌ PDF download failed, cannot continue")
        return
    
    # Test 3: Text extraction
    text = test_pdf_text_extraction(pdf_content)
    
    if not text:
        print("❌ Text extraction failed")
        return
    
    print(f"\n🎉 Debug complete! The issue might be:")
    print(f"   1. If no URLs found → Website structure changed")
    print(f"   2. If PDF download failed → URLs are invalid") 
    print(f"   3. If no text extracted → PDF is image-based or corrupted")
    print(f"   4. If text extracted but 0 shops → Gemini AI processing issue")

if __name__ == "__main__":
    main()