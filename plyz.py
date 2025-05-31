import requests
import argparse
import sys
from tqdm import tqdm
from fake_useragent import UserAgent
from collections import defaultdict
from bs4 import BeautifulSoup
import re

logo = r'''
 _______  _              _______ 
(  ____ )( \   |\     /|/ ___   )
| (    )|| (   ( \   / )\/   )  |
| (____)|| |    \ (_) /     /   )
|  _____)| |     \   /     /   / 
| (      | |      ) (     /   /  
| )      | (____/\| |    /   (_/\
|/       (_______/\_/   (_______/
    Github: sharif1337
    Facebook: sharifansari00
'''
print(logo)


def load_wordlist(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"[-] Failed to load wordlist: {e}")
        return []

def extract_params_from_response(response_text):
    found_params = set()
    soup = BeautifulSoup(response_text, "html.parser")

    # 1. HTML form input names
    for input_tag in soup.find_all("input"):
        name = input_tag.get("name")
        if name:
            found_params.add(name)

    # 2. Query parameters in URLs (?param= or &param=)
    found_params.update(re.findall(r"[?&]([a-zA-Z0-9_]+)=", response_text))

    # 3. JS assignments: param = 'value' or param: 'value'
    found_params.update(re.findall(r'([a-zA-Z0-9_]+)\s*[:=]\s*[\'"]', response_text))

    # 4. JS variable declarations: var param = ...
    found_params.update(re.findall(r"\bvar\s+([a-zA-Z0-9_]+)\s*=", response_text))

    # 5. JS let/const declarations: let/const param = ...
    found_params.update(re.findall(r"\b(?:let|const)\s+([a-zA-Z0-9_]+)\s*=", response_text))

    # 6. JSON-style keys: "param":
    found_params.update(re.findall(r'"([a-zA-Z0-9_]+)"\s*:', response_text))
    print(list(found_params))

    return list(found_params)

def scan_hidden_params(url, session, wordlist, method, test_value="sharif1337"):
    print(f"[+] Scanning URL: {url} using {method.upper()}")
    try:
        baseline_resp = session.request(method.upper(), url, timeout=10)
        baseline_length = len(baseline_resp.text)
    except Exception as e:
        print(f"[-] Failed to get baseline response: {e}")
        return {}, {}, 0

    length_diff_map = defaultdict(list)
    param_response_lengths = {}

    for param in tqdm(wordlist, desc="Scanning"):
        try:
            data = {param: test_value}
            if method == "get":
                resp = session.get(url, params=data, timeout=10)
            else:
                resp = session.post(url, data=data, timeout=10)

            if resp.status_code == 200:
                resp_length = len(resp.text)
                diff = abs(resp_length - baseline_length)
                length_diff_map[diff].append(param)
                param_response_lengths[param] = resp_length
        except Exception:
            continue

    hidden_params = {}
    other_params = {}

    for diff, params in length_diff_map.items():
        if len(params) == 1:
            param = params[0]
            hidden_params[param] = param_response_lengths[param]
        else:
            for param in params:
                other_params[param] = param_response_lengths[param]

    return hidden_params, other_params, baseline_length

def parse_cookies(raw_cookie):
    cookies = {}
    for item in raw_cookie.split(';'):
        if '=' in item:
            key, val = item.strip().split('=', 1)
            cookies[key.strip()] = val.strip()
    return cookies

def save_hidden_to_file(hidden_dict, filename):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for param in hidden_dict:
                f.write(param + '\n')
        print(f"[+] Hidden parameters saved to: {filename}")
    except Exception as e:
        print(f"[-] Failed to save file: {e}")

def print_table(title, data_dict):
    print(f"\n[+] {title}")
    header = f"| {'Parameters'.center(20)} | {'Response Length'.center(20)} |"
    line = "-" * len(header)
    print(line)
    print(header)
    print(line)
    for param, length in sorted(data_dict.items(), key=lambda x: x[1]):
        print(f"| {param.center(20)} | {str(length).center(20)} |")
    print(line)

def main():
    parser = argparse.ArgumentParser(description="Hidden Parameter Scanner with Cookie Support")
    parser.add_argument("-u", "--url", required=True, help="Target URL (e.g., https://example.com/page)")
    parser.add_argument("-w", "--wordlist", required=True, help="Path to wordlist file")
    parser.add_argument("-m", "--method", default="get", help="HTTP method to use (get or post)")
    parser.add_argument("-vt", "--value-type", choices=["n", "a", "x"], default="x",
                        help="Test value type: n = number, a = alphabet, x = alphanumeric (default)")
    parser.add_argument("-c", "--cookie", help="Manually set session cookie")
    parser.add_argument("-o", "--output", help="Output file to save hidden parameters")

    args = parser.parse_args()

    method = args.method.lower()
    if method not in ("get", "post"):
        print("[-] Method must be GET or POST")
        sys.exit(1)

    # Value to test
    test_value = {
        "n": "1337",
        "a": "sharif",
        "x": "sharif1337"
    }.get(args.value_type, "sharif1337")

    # Load wordlist
    wordlist = load_wordlist(args.wordlist)
    if not wordlist:
        return

    # Setup session
    session = requests.Session()
    try:
        ua = UserAgent()
        session.headers.update({"User-Agent": ua.random})
    except:
        session.headers.update({"User-Agent": "Mozilla/5.0"})

    # Add manual cookie if provided
    if args.cookie:
        session.cookies.update(parse_cookies(args.cookie))

    # Get page and extract parameters
    try:
        response = session.get(args.url, timeout=10)
        print(f"[+] URL status: {response.status_code}")
        extracted = extract_params_from_response(response.text)
        print(f"[+] Extracted {len(extracted)} parameters from source")
        print(f"[+] Testing {len(wordlist)} parameters from {args.wordlist}")
        wordlist = list(set(wordlist + extracted))
    except Exception as e:
        print(f"[-] Failed to load URL: {e}")
        return

    # Scan parameters
    hidden, others, base = scan_hidden_params(args.url, session, wordlist, method, test_value)

    print("\n=== Scan Complete ===")
    if hidden:
        print_table("Hidden Parameters Found", hidden)
        if args.output:
            save_hidden_to_file(hidden, args.output)
    else:
        print("[-] No hidden parameters found.")

    if others:
        print_table("Other Parameters Tested", others)

if __name__ == "__main__":
    main()
