#!/usr/bin/env python3
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import sys
from datetime import datetime
import requests
from termcolor import colored
from urllib.parse import quote

VERSION = "v1.2"

def print_banner():
    banner = """"""  # You can add your banner text here
    print(banner)
    animated_text("Project ESQLi Error-Based Tool", 'blue')

def animated_text(text, color='white', speed=0):
    for char in text:
        sys.stdout.write(colored(char, color))
        sys.stdout.flush()
        time.sleep(speed)
    print()

# Create the argument parser and add arguments
parser = argparse.ArgumentParser(description="SQLi Error-Based Tool")
parser.add_argument("-u", "--urls", required=True, help="Provide a URLs list for testing", type=str)
parser.add_argument("-p", "--payloads", required=True, help="Provide a list of SQLi payloads for testing", type=str)
parser.add_argument("-s", "--silent", action="store_true", help="Rate limit to 12 requests per second")
parser.add_argument("-t", "--threads", type=int, choices=range(1, 21), required=False, help="Number of threads (1-20)")
parser.add_argument("-o", "--output", help="File to save only positive results")
parser.add_argument("--parallel", action="store_true", help="Enable parallel mode for parameter scanning")
parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {VERSION}", help="Display version information and exit")

args = parser.parse_args()

print_banner()

with open(args.urls, 'r') as f:
    urls = f.read().splitlines()

with open(args.payloads, 'r') as f:
    payloads = f.read().splitlines()

# User agents list
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Version/14.1.2 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.70",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Mobile Safari/537.36",
]

sql_errors = [
    "Syntax error", "Fatal error", "MariaDB", "corresponds", "Database Error", "syntax",
    "/usr/www", "public_html", "database error", "on line", "RuntimeException", "mysql_", 
    "MySQL", "PSQLException", "at line", "You have an error in your SQL syntax", 
    "mysql_query()", "pg_connect()", "SQLiteException", "ORA-", "invalid input syntax for type", 
    "unterminated quoted string", "PostgreSQL query failed:", "unrecognized token:", 
    "binding parameter", "undeclared variable:", "SQLSTATE", "constraint failed", 
    "ORA-00936: missing expression", "ORA-06512:", "PLS-", "SP2-", "dynamic SQL error", 
    "SQL command not properly ended", "T-SQL Error", "Msg ", "Level ", 
    "Unclosed quotation mark after the character string", "quoted string not properly terminated", 
    "Incorrect syntax near", "An expression of non-boolean type specified in a context where a condition is expected", 
    "Conversion failed when converting", "Unclosed quotation mark before the character string", 
    "SQL Server", "OLE DB", "Unknown column", "Access violation", "No such host is known", 
    "server error", "syntax error at or near", "column does not exist", "could not prepare statement", 
    "no such table:", "near \"Syntax error\": syntax error", "unknown error", 
    "unexpected end of statement", "ambiguous column name", "database is locked", 
    "permission denied", "attempt to write a readonly database", "out of memory", 
    "disk I/O error", "cannot attach the file", "operation is not allowed in this state", 
    "data type mismatch", "cannot open database", "table or view does not exist", 
    "index already exists", "index not found", "division by zero", "value too large for column", 
    "deadlock detected", "invalid operator", "sequence does not exist", 
    "duplicate key value violates unique constraint", "string data, right truncated", 
    "insufficient privileges", "missing keyword", "too many connections", 
    "configuration limit exceeded", "network error while attempting to read from the file", 
    "cannot rollback - no transaction is active", "feature not supported", 
    "system error", "object not in prerequisite state", "login failed for user", 
    "remote server is not known"
]

total_requests = len(urls) * len(payloads) * max(url.count('&') + 1 for url in urls)
progress = 0
start_time = time.time()

# Determine output file name
output_file = args.output if args.output else f"positive_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

def save_results(url_modified):
    with open(output_file, 'a') as file:
        file.write(url_modified + '\n')

def fetch_url(url, retries=3):
    session = requests.Session()
    for _ in range(retries):
        try:
            response = session.get(url, headers={"User-Agent": random.choice(user_agents)}, timeout=10)
            if response.status_code == 200:
                return response.text
        except requests.RequestException:
            time.sleep(1)
    return None

def report_progress(progress, total_requests, start_time):
    if progress % 10 == 0:
        elapsed_seconds = time.time() - start_time
        remaining_seconds = (total_requests - progress) * (elapsed_seconds / progress) if progress > 0 else 0
        remaining_hours = int(remaining_seconds // 3600)
        remaining_minutes = int((remaining_seconds % 3600) // 60)
        percent_complete = round(progress / total_requests * 100, 2)
        print(f"{colored('Progress:', 'blue')} {progress}/{total_requests} ({percent_complete}%) - {remaining_hours}h:{remaining_minutes:02d}m")

def test_payload(base_url, key, payload, sql_errors):
    url_modified = f"{base_url}?{key}={quote(payload)}"
    print(colored(f"Testing URL: {url_modified}", 'cyan'))

    output_str = fetch_url(url_modified)
    if output_str:
        if any(error in output_str for error in sql_errors):
            message = f"\n{colored('SQL ERROR FOUND', 'white')} ON {colored(url_modified, 'red', attrs=['bold'])} with payload {colored(payload, 'yellow')}"
            print(message)
            return url_modified
    return None

def scan_with_payload(url):
    base_url, query_string = url.split('?', 1) if '?' in url else (url, '')
    pairs = query_string.split('&')

    for i in range(len(pairs)):
        found_sql_error = False
        key = pairs[i].split('=', 1)[0] if '=' in pairs[i] else pairs[i]

        # If parallel mode is enabled, scan each payload in parallel
        if args.parallel:
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = [executor.submit(test_payload, base_url, key, payload, sql_errors) for payload in payloads]
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        save_results(result)
                        found_sql_error = True
                        break  # Stop testing other payloads for this parameter and move to next URL
        else:
            # Sequential mode: test payloads one by one
            for payload in payloads:
                result = test_payload(base_url, key, payload, sql_errors)
                if result:
                    save_results(result)
                    found_sql_error = True
                    break  # Stop testing and jump to next URL
        
        if found_sql_error:
            break  # Move to next URL after finding SQLi error

def scan_url(url):
    global progress
    scan_with_payload(url)
    progress += len(payloads)
    report_progress(progress, total_requests, start_time)

# Main execution with graceful shutdown
try:
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        executor.map(scan_url, urls)
except KeyboardInterrupt:
    print(colored("\nScan interrupted by user. Saving results...", 'yellow'))

end_time = time.time()
total_time = end_time - start_time
print(colored(f"\nTotal Time: {total_time:.2f} seconds", 'yellow'))
