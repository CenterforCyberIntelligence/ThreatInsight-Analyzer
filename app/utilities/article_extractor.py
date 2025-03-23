import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Optional, Dict, List, Tuple
import traceback
from urllib.parse import urlparse

from app.utilities.logger import print_status, info, debug, error, warning

def extract_article_content(url: str, verbose: bool = True) -> Optional[str]:
    """
    Extract article content using multiple methods and combine the best results.
    
    Args:
        url: The URL to extract content from
        verbose: Whether to print status messages
        
    Returns:
        Extracted article text or None if extraction failed
    """
    info(f"Starting enhanced extraction from URL: {url}")
    
    if verbose:
        print_status(f"Starting enhanced extraction from URL: {url}")
        print_status(f"Setting up request headers...")
    
    try:
        # Parse the URL to get the domain
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Get specialized headers for the domain
        headers = get_domain_specific_headers(domain)
        debug(f"Using domain-specific headers for {domain}")
        
        if verbose:
            print_status(f"Sending HTTP request to {url}")
            start_time = time.time()
            
        # Send the HTTP request
        debug(f"Sending HTTP request to {url} with timeout=20 seconds")
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=20)
        elapsed = time.time() - start_time
        
        debug(f"Received response in {elapsed:.2f} seconds (Status: {response.status_code})")
        
        if verbose:
            print_status(f"Received response in {elapsed:.2f} seconds (Status: {response.status_code})")
        
        response.raise_for_status()
        
        # Parse the HTML content
        debug(f"Parsing HTML content ({len(response.text)} bytes)")
        parse_start = time.time()
        
        if verbose:
            print_status(f"Parsing HTML content ({len(response.text)} bytes)")
            parse_start = time.time()
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        parse_elapsed = time.time() - parse_start
        debug(f"HTML parsed in {parse_elapsed:.2f} seconds")
        
        if verbose:
            print_status(f"HTML parsed in {parse_elapsed:.2f} seconds")
            print_status("Applying multiple extraction methods...")
        
        # Try multiple methods and combine the results
        extraction_results = []
        
        # Method 1: Extract using common article containers
        method1_text = extract_by_containers(soup, verbose)
        if method1_text and len(method1_text) > 200:
            extraction_results.append((method1_text, len(method1_text), "container_based"))
            debug(f"Container method retrieved {len(method1_text)} characters")
        
        # Method 2: Extract using paragraphs
        method2_text = extract_by_paragraphs(soup, verbose)
        if method2_text and len(method2_text) > 200:
            extraction_results.append((method2_text, len(method2_text), "paragraph_based"))
            debug(f"Paragraph method retrieved {len(method2_text)} characters")
        
        # Method 3: Extract using text density
        method3_text = extract_by_text_density(soup, verbose)
        if method3_text and len(method3_text) > 200:
            extraction_results.append((method3_text, len(method3_text), "density_based"))
            debug(f"Density method retrieved {len(method3_text)} characters")
        
        # Select the best result (prioritize by length but consider quality)
        if not extraction_results:
            warning(f"All extraction methods failed for {url}")
            if verbose:
                print_status(f"All extraction methods failed. Trying fallback method...", is_error=True)
            
            # Fallback: Get all text from body with minimal cleaning
            fallback_text = soup.body.get_text(" ", strip=True)
            fallback_text = clean_extracted_text(fallback_text)
            
            if fallback_text and len(fallback_text) > 200:
                debug(f"Fallback method retrieved {len(fallback_text)} characters")
                return fallback_text
            return None
        
        # Sort by length (descending)
        extraction_results.sort(key=lambda x: x[1], reverse=True)
        
        # Pick the longest result that isn't garbage
        final_text = extraction_results[0][0]
        method_used = extraction_results[0][2]
        
        info(f"Extraction complete. Retrieved {len(final_text)} characters using {method_used} method from {url}")
        debug(f"Content sample: \n{final_text[:200]}...")
        
        if verbose:
            print_status(f"Extraction complete. Retrieved {len(final_text)} characters of content using {method_used} method")
            
            # Print a sample of the content
            sample = final_text[:200] + "..." if len(final_text) > 200 else final_text
            print_status(f"Content sample: \n{sample}")
        
        return final_text
    except requests.exceptions.Timeout:
        error(f"Request timed out after 20 seconds for URL: {url}")
        
        if verbose:
            print_status(f"Request timed out after 20 seconds", is_error=True)
        return None
    except requests.exceptions.ConnectionError:
        error(f"Connection error when accessing URL: {url}")
        
        if verbose:
            print_status(f"Connection error when accessing {url}", is_error=True)
        return None
    except requests.exceptions.HTTPError as e:
        error(f"HTTP error for URL {url}: {e}")
        
        if verbose:
            print_status(f"HTTP error: {e}", is_error=True)
        return None
    except Exception as e:
        error_details = traceback.format_exc()
        error(f"Error extracting content from {url}: {e}")
        error(f"Traceback: {error_details}")
        
        if verbose:
            print_status(f"Error extracting content from {url}: {e}", is_error=True)
            print_status(f"Traceback: {error_details}", is_error=True)
        return None

def get_domain_specific_headers(domain: str) -> Dict[str, str]:
    """Get headers customized for specific domains to improve extraction."""
    # Default headers
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    # Add domain-specific headers if needed
    domain_specific = {
        'www.cybersecurity-insiders.com': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Referer': 'https://www.google.com/'
        },
        'www.bleepingcomputer.com': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Referer': 'https://www.google.com/'
        }
        # Add more domains as needed
    }
    
    return domain_specific.get(domain, default_headers)

def extract_by_containers(soup: BeautifulSoup, verbose: bool = True) -> Optional[str]:
    """Extract content using common article container selectors."""
    debug("Extracting content using container selectors")
    
    # Remove unwanted elements
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript', 'form']):
        element.decompose()
    
    # Look for common article containers
    selectors = [
        'article', 'main', '.post-content', '.article-content', '.entry-content', 
        '#content', '.content', '.post', '.article', '.story-body', '.story',
        '.post-body', '.news-article', '.blog-post', '.node-content',
        '[itemprop="articleBody"]', '.body', '.entry', '.story-text'
    ]
    
    for selector in selectors:
        content = soup.select(selector)
        if content:
            main_content = content[0]
            text = main_content.get_text(separator='\n')
            return clean_extracted_text(text)
    
    return None

def extract_by_paragraphs(soup: BeautifulSoup, verbose: bool = True) -> Optional[str]:
    """Extract content by finding and combining all paragraphs."""
    debug("Extracting content using paragraph elements")
    
    # Find all paragraphs that are likely part of the article
    paragraphs = soup.find_all('p')
    
    if not paragraphs:
        return None
    
    # Filter out short paragraphs that are likely navigation or other UI elements
    substantive_paragraphs = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20]
    
    if not substantive_paragraphs:
        return None
    
    # Combine paragraphs
    text = '\n\n'.join(substantive_paragraphs)
    return clean_extracted_text(text)

def extract_by_text_density(soup: BeautifulSoup, verbose: bool = True) -> Optional[str]:
    """Extract content by finding areas with high text density."""
    debug("Extracting content using text density analysis")
    
    # Remove noise elements
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        element.decompose()
    
    # Find all div elements
    divs = soup.find_all('div')
    
    # Calculate text density for each div
    div_density = []
    for div in divs:
        text = div.get_text(' ', strip=True)
        if not text:
            continue
            
        # Calculate text to HTML ratio as a simple density metric
        html_length = len(str(div))
        text_length = len(text)
        
        if html_length > 0:
            density = text_length / html_length
            word_count = len(text.split())
            
            # Only consider divs with substantial text
            if word_count > 50:
                div_density.append((div, density, text_length, word_count))
    
    if not div_density:
        return None
    
    # Sort by text length * density to favor longer, denser content
    div_density.sort(key=lambda x: x[2] * x[1], reverse=True)
    
    # Take the highest scoring div
    best_div = div_density[0][0]
    text = best_div.get_text('\n', strip=True)
    
    return clean_extracted_text(text)

def clean_extracted_text(text: str) -> str:
    """Clean up extracted text."""
    # Handle None input
    if text is None:
        return ""
        
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    text = '\n'.join(line for line in lines if line)
    
    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove common noise phrases
    noise_patterns = [
        r'Share this article',
        r'Share on:',
        r'Related articles',
        r'You might also like',
        r'Click to share',
        r'Comments \(\d+\)',
        r'Read more',
        r'Subscribe to our newsletter',
        r'Sign up for our newsletter',
        r'Advertisement',
    ]
    
    for pattern in noise_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text 