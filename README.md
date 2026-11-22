<div align="center">

```
  ██╗  ██╗ █████╗ ███████╗██╗  ██╗ ██████╗██████╗  █████╗  ██████╗██╗  ██╗
  ██║  ██║██╔══██╗██╔════╝██║  ██║██╔════╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
  ███████║███████║███████╗███████║██║     ██████╔╝███████║██║     █████╔╝ 
  ██╔══██║██╔══██║╚════██║██╔══██║██║     ██╔══██╗██╔══██║██║     ██╔═██╗ 
  ██║  ██║██║  ██║███████║██║  ██║╚██████╗██║  ██║██║  ██║╚██████╗██║  ██╗
  ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚╚═════╝╚═╝  ╚═╝
```

### Animated local hash cracker — CPU-only, no GPU needed

**by [JackRipper-ID](https://github.com/JackRipper-ID)** · [MIT License](LICENSE)

![python](https://img.shields.io/badge/python-3.8%2B-blue)
![platform](https://img.shields.io/badge/platform-linux%20%7C%20termux%20%7C%20kali-success)
![license](https://img.shields.io/badge/license-MIT-green)
![deps](https://img.shields.io/badge/required%20deps-zero-orange)
![formats](https://img.shields.io/badge/hash%20formats-39%2B-9cf)

</div>

---

> **Ethical use only.** Use on hashes you own or are authorized to test
> (your own accounts, sanctioned pentests, CTFs). Unauthorized access to
> other people's systems is illegal.

---

## Features

| | |
|---|---|
| **39+ hash formats** | auto-detected — ambiguous hex lengths tested against *all* matching algorithms at once |
| **Fully animated TUI** | live panel redrawn in place (no scrolling): braille spinner, flowing gradient bar, real-time sparkline |
| **6 attack modes** | wordlist · wordlist+rules · mask · PIN · literal · 2-wordlist combo |
| **Encrypted ZIP** | ZipCrypto (pure Python) and AES-256 (via `7z`) |
| **All cores** | multiprocessing with automatic `spawn` fallback |
| **Android CPU boost** | lifts the thermal cpufreq cap on rooted devices (~+25-80% on SD865) |
| **Auto wordlist discovery** | drop any `.txt`/`.lst` in `~/wordlists/` — it appears in the menu |
| **Zero required deps** | pure Python stdlib; optional `bcrypt`/`passlib` unlock more formats |

Live panel preview (redrawn in place, never scrolls):

```
  ██╗  ██╗ █████╗ ███████╗██╗  ██╗ ██████╗██████╗  █████╗  ██████╗██╗  ██╗
  ██║  ██║██╔══██╗██╔════╝██║  ██║██╔════╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
  ███████║███████║███████╗███████║██║     ██████╔╝███████║██║     █████╔╝ 
  ██╔══██║██╔══██║╚════██║██╔══██║██║     ██╔══██╗██╔══██║██║     ██╔═██╗ 
  ██║  ██║██║  ██║███████║██║  ██║╚██████╗██║  ██║██║  ██║╚██████╗██║  ██╗
  ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚╚═════╝╚═╝  ╚═╝
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   . menganalisis   ['sha256', 'blake2s', 'sha3_256']        │
│                                                             │
│   ████████████████████████████░░░░░░░░░░  62.4%             │
│                                                             │
│   kecepatan ▄▂▁▄▅▃▆▇▅▄▆█▇▅▄  82 H/s   ETA 1.2 menit         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Install

### Kali Linux / Debian / Ubuntu / Parrot / Fedora / Arch

```bash
git clone https://github.com/JackRipper-ID/hashcrack.git
cd hashcrack
sudo bash install-linux.sh    # installs deps + the `hashcrack` command
```

Or manually:

```bash
git clone https://github.com/JackRipper-ID/hashcrack.git
cd hashcrack
chmod +x hashcrack.py

# optional — unlocks bcrypt & 30+ crypt formats
sudo apt install python3-bcrypt python3-passlib p7zip-full

./hashcrack.py
```

<details>
<summary><b>Install as a system command (<code>hashcrack</code> anywhere)</b></summary>

```bash
sudo cp hashcrack.py /usr/local/bin/hashcrack
sudo chmod +x /usr/local/bin/hashcrack
hashcrack --identify -H '<hash>'
```

</details>

<details>
<summary><b>Kali one-liner (all deps)</b></summary>

```bash
sudo apt install -y python3-bcrypt python3-passlib p7zip-full && \
git clone https://github.com/JackRipper-ID/hashcrack.git && \
cd hashcrack && ./hashcrack.py
```

Kali already ships `wordlists` at `/usr/share/wordlists/` — hashcrack
finds `rockyou.txt` there automatically.

</details>

### Termux (Android)

```bash
# copy hashcrack.py + install-termux.sh to the phone first, then:
bash install-termux.sh
hashcrack
```

The installer sets up python, p7zip, bcrypt, passlib, the `hashcrack`
command, and `~/wordlists/`. On **rooted** phones the tool auto-boosts
CPU clocks while cracking.

## Usage

```bash
./hashcrack.py                    # interactive menu (guided)
./hashcrack.py --identify -H '<hash>'   # detect hash type only
```

| Attack | Command |
|---|---|
| Wordlist | `hashcrack -H <hash> -w rockyou.txt` |
| Wordlist + mutations | `hashcrack -H <hash> -w rockyou.txt -r` |
| Mask (4 letters + 2 digits) | `hashcrack -H <hash> --mask "?l?l?l?l?d?d"` |
| 6-digit PIN | `hashcrack -H <hash> --digits 6` |
| Test candidates | `hashcrack -H <hash> --literal "pass,test123"` |
| Two-wordlist combo | `hashcrack -H <hash> --combo names.txt numbers.txt` |
| Encrypted ZIP | `hashcrack -H file.zip` |
| Force algorithm | `hashcrack -H <hash> -w wl.txt --algo ntlm` |
| Username formats | `hashcrack -H <hash> -w wl.txt --user postgres` |

### Mask codes

| `?l` | `?u` | `?d` | `?s` | `?a` | `?h`/`?H` |
|:--:|:--:|:--:|:--:|:--:|:--:|
| lowercase | uppercase | digits | symbols | all | hex |

## Supported formats

<details>
<summary><b>Plain hex digests</b></summary>

MD4 · MD5 · SHA-1 · SHA-224 · SHA-256 · SHA-384 · SHA-512
SHA3-224/256/384/512 · BLAKE2s · BLAKE2b · RIPEMD-160 · SM3
SHA-512/224 · SHA-512/256 · NTLM · LM · MySQL 3.23 · MySQL 4.1
PostgreSQL md5 · Oracle 10/11 · MS SQL 2000/2005 · MS Domain Cache v1/v2
HTTP Digest · CRC32

</details>

<details>
<summary><b>Crypt / formatted hashes</b></summary>

bcrypt (`$2a/$2b/$2y/$2x`) · bcrypt-sha256 · md5crypt (`$1$`)
apr1/htpasswd (`$apr1$`) · sha256crypt (`$5$`) · sha512crypt (`$6$`)
sha1crypt (`$sha1$`) · sun-md5 (`$md5,rounds=`) · phpass (`$P$`/`$H$`)
PBKDF2 (sha1/sha256/sha512) · Django PBKDF2 · GRUB PBKDF2 · SCRAM
bsdi-crypt (`_...`) · crypt16 · DES · Atlassian `{PKCS5S2}` · LDAP `{SSHA}`
FSHP · Cisco PIX/ASA · and more

</details>

## Wordlists

hashcrack scans `~/wordlists/` and its own folder (smallest first):

- [rockyou.txt](https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt) — 14M passwords, the classic
- [SecLists](https://github.com/danielmiessler/SecLists) — language-specific common passwords
- [Indonesian passwords](https://github.com/elliottophellia/wordlist) — 10M real ID passwords
- Kali users: `/usr/share/wordlists/rockyou.txt` is found automatically

## Typical performance

| Device | SHA-256 | bcrypt cost 10 |
|:--|--:|--:|
| Laptop 4-core (i7-7600U) | ~300k H/s | ~40 H/s |
| Phone 8-core (SD865, Termux, boosted) | ~116k H/s | ~75-82 H/s |

> bcrypt is intentionally slow — big wordlists take hours on any CPU-only
> setup. On Android run `termux-wake-lock` so the process survives screen-off.

## Files

```
hashcrack.py         main tool — single file, stdlib only
install-linux.sh     automated installer for Kali/Debian/Ubuntu/Fedora/Arch
install-termux.sh    automated Termux (Android) installer
LICENSE              MIT © JackRipper-ID
```

---

<div align="center">

**HASHCRACK** · crafted by **JackRipper-ID**

*if this repo helped you, a star is appreciated*

</div>
