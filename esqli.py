#!/usr/bin/env python3
import os
import requests
import time
import random
import argparse
import concurrent.futures

class Color:
    BLUE = '\033[94m'
    GREEN = '\033[1;92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

class BSQLI:
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Version/14.1.2 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.70",
        "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
    ]

    SQL_ERROR_PATTERNS = {
        'MySQL': ["you have an error in your sql syntax", "warning: mysql", "mysql_fetch", "sql syntax near", "unexpected end of SQL", "Warning: mysql_", "pg_connect()", "OLE DB Provider for SQL Server"],
        'PostgreSQL': ["syntax error at or near", "pg_query", "psql:"],
        'MSSQL': ["unclosed quotation mark after the character string", "sql server", "microsoft ole db"],
        'Oracle': ["ora-", "oracle", "pl/sql:"],
    }

    def __init__(self, verbose=False):
        self.vulnerabilities_found = 0
        self.total_tests = 0
        self.verbose = verbose
        self.vulnerable_urls = []
        self.db_type = None

    def get_random_user_agent(self):
        return random.choice(self.USER_AGENTS)

    def detect_sql_errors(self, response_text):
        if not self.db_type:  # Check all DB types if we haven't fingerprinted yet
            for db, errors in self.SQL_ERROR_PATTERNS.items():
                if any(error.lower() in response_text.lower() for error in errors):
                    self.db_type = db
                    return True
        else:  # Only check against the detected database type
            errors = self.SQL_ERROR_PATTERNS.get(self.db_type, [])
            return any(error.lower() in response_text.lower() for error in errors)
        return False

    def identify_backend(self, response_headers):
        if "x-powered-by" in response_headers:
            x_powered_by = response_headers.get("x-powered-by", "").lower()
            if "php" in x_powered_by:
                self.db_type = 'MySQL'
            elif "asp" in x_powered_by:
                self.db_type = 'MSSQL'
            elif "java" in x_powered_by:
                self.db_type = 'Oracle'

    def perform_request(self, url, payload, cookie):
        url_with_payload = f"{url}{payload}"
        start_time = time.time()
        headers = {'User-Agent': self.get_random_user_agent()}
        try:
            response = requests.get(url_with_payload, headers=headers, cookies={'cookie': cookie} if cookie else None)
            response.raise_for_status()
            response_time = time.time() - start_time

            # Identify the backend technology
            if not self.db_type:
                self.identify_backend(response.headers)
            
            # Detect SQL errors in response text
            if self.detect_sql_errors(response.text):
                return True, url_with_payload, response_time, response.status_code, None  # Vulnerability detected
            return False, url_with_payload, response_time, response.status_code, None
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            return False, url_with_payload, response_time, None, str(e)

    def log_result(self, success, url_with_payload, response_time, status_code):
        if success:
            self.vulnerabilities_found += 1
            self.vulnerable_urls.append(url_with_payload)
            if self.verbose:
                print(f"{Color.GREEN}✓ SQLi Found! URL: {url_with_payload} - ErrorSQLi - Status Code: {status_code}{Color.RESET}")
            else:
                print(f"{Color.GREEN}✓ Vulnerable URL: {url_with_payload}{Color.RESET}")
        else:
            if self.verbose:
                print(f"{Color.RED}✗ Not Vulnerable: {url_with_payload} - ErrorSQLi - Status Code: {status_code}{Color.RESET}")

    def read_file(self, path):
        try:
            with open(path) as file:
                return [line.strip() for line in file if line.strip()]
        except Exception as e:
            print(f"{Color.RED}Error reading file {path}: {e}{Color.RESET}")
            return []

    def save_vulnerable_urls(self, filename):
        try:
            with open(filename, 'w') as file:
                for url in self.vulnerable_urls:
                    file.write(f"{url}\n")
            print(f"{Color.GREEN}Vulnerable URLs saved to {filename}{Color.RESET}")
        except Exception as e:
            print(f"{Color.RED}Error saving vulnerable URLs to file: {e}{Color.RESET}")

    def run_scan(self, urls, payloads, cookie, threads):
        try:
            if threads == 0:
                for url in urls:
                    for payload in payloads:
                        self.total_tests += 1
                        success, url_with_payload, response_time, status_code, error_message = self.perform_request(url, payload, cookie)
                        self.log_result(success, url_with_payload, response_time, status_code)
            else:
                with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                    futures = [executor.submit(self.perform_request, url, payload, cookie) for url in urls for payload in payloads]
                    for future in concurrent.futures.as_completed(futures):
                        self.total_tests += 1
                        success, url_with_payload, response_time, status_code, error_message = future.result()
                        self.log_result(success, url_with_payload, response_time, status_code)
        except KeyboardInterrupt:
            print(f"{Color.YELLOW}Scan interrupted by user.{Color.RESET}")

def main():
    parser = argparse.ArgumentParser(description="ESQLI Tool - SQL Injection Scanner")
    parser.add_argument('-u', '--urls', type=str, required=True, help="Path to URL list file or a single URL")
    parser.add_argument('-p', '--payloads', type=str, required=True, help="Path to the payload file")
    parser.add_argument('-t', '--threads', type=int, default=0, help="Number of concurrent threads (0-10)")
    parser.add_argument('-o', '--save', type=str, default="", help="Filename to save vulnerable URLs")
    parser.add_argument('-v', '--verbose', action='store_true', help="Enable verbose mode")
    parser.add_argument('-V', '--version', action='version', version='BSQLI Scanner 1.0', help="Show version")

    args = parser.parse_args()

    scanner = BSQLI(verbose=args.verbose)

    # Read URLs
    urls = [args.urls] if not os.path.isfile(args.urls) else scanner.read_file(args.urls)
    if not urls:
        print(f"{Color.RED}No valid URLs provided.{Color.RESET}")
        return

    # Read payloads
    payloads = scanner.read_file(args.payloads)
    if not payloads:
        print(f"{Color.RED}No valid payloads found in file: {args.payloads}{Color.RESET}")
        return

    print(f"{Color.PURPLE}Starting Error Based Scan...{Color.RESET}")
    scanner.run_scan(urls, payloads, None, args.threads)  # Cookie set to None, can be added

    print(f"\n{Color.BLUE}Scan Complete.{Color.RESET}")
    print(f"{Color.YELLOW}Total Tests: {scanner.total_tests}{Color.RESET}")
    print(f"{Color.GREEN}Error SQLi Found: {scanner.vulnerabilities_found}{Color.RESET}")

    if args.save:
        scanner.save_vulnerable_urls(args.save)

if __name__ == "__main__":
    main()
