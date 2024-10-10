#!/usr/bin/env python3
import re
import subprocess
import time
from termcolor import colored
import argparse
from concurrent.futures import ThreadPoolExecutor
import random
import sys
from datetime import datetime

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

def random_delay():
    if args.silent:
        time.sleep(60 / 12)
    else:
        base_delay = 1
        jitter = random.uniform(0.5, 1.5)
        time.sleep(base_delay * jitter)

# Create the argument parser and add arguments
parser = argparse.ArgumentParser(description="SQLi Error-Based Tool")
parser.add_argument("-u", "--urls", required=True, help="Provide a URLs list for testing", type=str)
parser.add_argument("-p", "--payloads", required=True, help="Provide a list of SQLi payloads for testing", type=str)
parser.add_argument("-s", "--silent", action="store_true", help="Rate limit to 12 requests per second")
parser.add_argument("-t", "--threads", type=int, choices=range(1, 21), required=False, help="Number of threads (1-20)")
parser.add_argument("-o", "--output", help="File to save only positive results")
parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {VERSION}", help="Display version information and exit")

args = parser.parse_args()

# Check if required arguments are missing
if not args.urls or not args.payloads:
    parser.error("the following arguments are required: -u/--urls, -p/--payloads")

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

def fetch_url(command, retries=3):
    for _ in range(retries):
        try:
            return subprocess.check_output(command, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            time.sleep(1)  # Small delay before retry
    return None

def scan_with_payload(url):
    base_url, query_string = url.split('?', 1) if '?' in url else (url, '')
    pairs = query_string.split('&')

    # Loop through each parameter
    for i in range(len(pairs)):
        # Keep track if SQL errors were found for this parameter
        found_sql_error = False
        
        # Loop through each payload for the current parameter
        for payload in payloads:
            modified_pairs = pairs.copy()
            if '=' in modified_pairs[i]:
                key, value = modified_pairs[i].split('=', 1)
                modified_pairs[i] = f"{key}={payload}"  # Replace value with the current payload
            url_modified = f"{base_url}?{'&'.join(modified_pairs)}"
            
            print(colored(f"Testing URL: {url_modified}", 'cyan'))  # Debug output
            
            user_agent = random.choice(user_agents)  # Randomly choose a user agent
            command = ['curl', '-s', '-i', '--url', url_modified, '-A', user_agent, '--max-time', '10']
            
            output_bytes = fetch_url(command)
            if output_bytes is not None:
                output_str = output_bytes.decode('utf-8', errors='ignore')
                sql_matches = [error for error in sql_errors if error in output_str]
                if sql_matches:
                    message = f"\n{colored('SQL ERROR FOUND', 'white')} ON {colored(url_modified, 'red', attrs=['bold'])} with payload {colored(payload, 'yellow')}"
                    print(message)
                    # Immediately save the positive result
                    with open(output_file, 'a') as file:
                        file.write(url_modified + '\n')
                    found_sql_error = True  # Mark that we found an SQLi error
                    break  # Stop checking other payloads for this parameter

        # If an SQLi error was found, break out of the payload loop and go to the next parameter
        if found_sql_error:
            continue  # Skip to the next parameter

def scan_url(url):
    global progress  # Declare 'progress' as global here
    # For each URL, run payload scans in parallel
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        executor.submit(scan_with_payload, url)  # Directly pass the url to scan_with_payload

# Main execution with graceful shutdown
try:
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        # Iterate through URLs and scan
        for url in urls:
            executor.submit(scan_url, url)

            # Increment progress
            progress += len(payloads)  # Update the progress for the total payloads for this URL

            # Print progress every 10 requests
            if progress % 10 == 0:
                elapsed_seconds = time.time() - start_time
                remaining_seconds = (total_requests - progress) * (elapsed_seconds / progress) if progress > 0 else 0
                remaining_hours = int(remaining_seconds // 3600)
                remaining_minutes = int((remaining_seconds % 3600) // 60)
                percent_complete = round(progress / total_requests * 100, 2)
                print(f"{colored('Progress:', 'blue')} {progress}/{total_requests} ({percent_complete}%) - {remaining_hours}h:{remaining_minutes:02d}m")

except KeyboardInterrupt:
    print(colored("\nScan interrupted by user. Saving results...", 'yellow'))

end_time = time.time()
total_time = end_time - start_time
print(colored(f"\nTotal Time: {total_time:.2f} seconds", 'yellow'))
