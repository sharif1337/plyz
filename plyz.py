import requests
import argparse
import sys
from tqdm import tqdm
from fake_useragent import UserAgent
from collections import defaultdict

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

def scan_hidden_params(url, session, wordlist, method, test_value="sharif1337"):
    print(f"[+] Scanning URL: {url} using {method.upper()}")
    try:
        baseline_resp = session.request(method.upper(), url, timeout=10)
        baseline_length = len(baseline_resp.text)
    except Exception as e:
        print(f"[-] Failed to get baseline response: {e}")
        return [], {}, 0

    length_diff_map = defaultdict(list)
    param_response_lengths = {}

    for param in tqdm(wordlist, desc="Scanning"):
        try:
            data = {param: test_value}
            if method == "get":
                resp = session.get(url, params=data, timeout=10)
            elif method == "post":
                resp = session.post(url, data=data, timeout=10)
            else:
                print(f"[-] Method '{method}' not supported.")
                sys.exit(1)

            if resp.status_code == 200:
                resp_length = len(resp.text)
                length_diff = abs(resp_length - baseline_length)
                length_diff_map[length_diff].append(param)
                param_response_lengths[param] = resp_length
        except Exception as e:
            print(f"[-] Error scanning param '{param}': {e}")

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

def main():
    parser = argparse.ArgumentParser(description="Hidden Parameter Scanner")
    parser.add_argument("-u", "--url", required=True, help="Target URL (e.g., https://example.com/page)")
    parser.add_argument("-w", "--wordlist", required=True, help="Path to wordlist file")
    parser.add_argument("-m", "--method", default="get", help="HTTP method to use (get or post)")
    parser.add_argument("-vt", "--value-type", choices=["n", "a", "x"], default="x",
                        help="Test value type: n = number, a = alphabet, x = alphanumeric (default)")

    args = parser.parse_args()
    url = args.url
    wordlist_path = args.wordlist
    method = args.method.lower()

    # ✅ Allow only 'get' and 'post' methods
    if method not in ("get", "post"):
        print(f"[-] Method '{method}' not found. Only 'get' or 'post' allowed.")
        sys.exit(1)

    # ✅ Set test value based on value type
    if args.value_type == "n":
        test_value = "1337"
    elif args.value_type == "a":
        test_value = "sharif"
    else:
        test_value = "sharif1337"

    # ✅ Load wordlist
    wordlist = load_wordlist(wordlist_path)
    if not wordlist:
        print("[-] Wordlist is empty or not found.")
        return

    # ✅ Setup session with random User-Agent
    session = requests.Session()
    try:
        ua = UserAgent()
        user_agent = ua.random
    except Exception:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"

    session.headers.update({'User-Agent': user_agent})

    try:
        response = session.get(url, timeout=10)
        #print(f"[+] Using User-Agent: {user_agent}")
        cookies = session.cookies.get_dict()
        '''if cookies:
            print(f"[+] Session cookies: {cookies}")
        else:
            print("[!] No cookies received from server.")'''
        print(f"[+] URL status code: {response.status_code}")
    except Exception as e:
        print(f"[-] Failed to connect to URL: {e}")
        return

    # ✅ Start scanning
    hidden, others, baseline_length = scan_hidden_params(url, session, wordlist, method, test_value)

    print("\n=== Scan Complete ===")

    # ✅ Print results as table
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

    if hidden:
        print_table("Hidden parameters found", hidden)
    else:
        print("[-] No hidden parameters found.")

    if others:
        print_table("Other tested parameters", others)
    else:
        print("[-] No other parameters with differing response lengths.")

if __name__ == "__main__":
    main()
