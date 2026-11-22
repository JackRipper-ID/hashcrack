# ⚡ HASHCRACK

**by JackRipper-ID** · [MIT License](LICENSE)

`python3` `termux` `hash-cracker` `bcrypt` `pentest` `offline` `cpu`

Local hash cracker (CPU-only) with a fully animated TUI. Works on **Linux
desktop** and **Android Termux**.

```
  ██╗  ██╗ █████╗ ███████╗██╗  ██╗ ██████╗██████╗  █████╗  ██████╗██╗  ██╗
  ██║  ██║██╔══██╗██╔════╝██║  ██║██╔════╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
  ███████║███████║███████╗███████║██║     ██████╔╝███████║██║     █████╔╝ 
  ██╔══██║██╔══██║╚════██║██╔══██║██║     ██╔══██╗██╔══██║██║     ██╔═██╗ 
  ██║  ██║██║  ██║███████║██║  ██║╚██████╗██║  ██║██║  ██║╚██████╗██║  ██╗
  ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
```

> ⚠️ Use only on hashes you own or are authorized to test (your own accounts,
> sanctioned pentests, CTFs). Unauthorized access to other people's systems is
> illegal.

## Features

- **39+ hash formats** with automatic detection (full list below)
- **Live animated panel** redrawn in place (no scrolling): spinner, flowing
  gradient progress bar, real-time speed sparkline
- **6 attack modes**: wordlist, wordlist + rules/mutations, mask, PIN,
  literal candidates, two-wordlist combo
- **Encrypted ZIP cracking** — ZipCrypto (stdlib) and AES-256 (via `7z`)
- **All CPU cores** via multiprocessing; automatic `spawn` fallback on Termux
- **CPU boost on rooted Android** — lifts the thermal cpufreq cap
  (`/sys/power/cpufreq_max_limit`) for up to +80% throughput
- **Auto wordlist discovery** — anything in `~/wordlists/` or the tool's
  folder shows up in the menu automatically
- **Guided interactive menu** + fast CLI mode

## Supported formats

**Plain hex:** MD4, MD5, SHA-1/224/256/384/512, SHA3-224/256/384/512,
BLAKE2s/BLAKE2b, RIPEMD-160, SM3, SHA-512/224, SHA-512/256, NTLM, LM,
MySQL 3.23, MySQL 4.1, PostgreSQL md5, Oracle 10/11, MS SQL 2000/2005,
MS Domain Cache v1/v2, HTTP Digest, CRC32

**Crypt / formatted:** bcrypt (`$2a/$2b/$2y/$2x`), bcrypt-sha256, md5crypt
(`$1$`), apr1/htpasswd (`$apr1$`), sha256crypt (`$5$`), sha512crypt (`$6$`),
sha1crypt, sun-md5, phpass (WordPress/phpBB `$P$`/`$H$`), PBKDF2
(sha1/sha256/sha512), Django PBKDF2, GRUB PBKDF2, SCRAM, bsdi-crypt,
crypt16, DES, Atlassian `{PKCS5S2}`, LDAP `{SSHA}`, FSHP, and more.

Ambiguous hex lengths (e.g. 32-char) are tested against **all matching
algorithms at once** — no guessing needed.

## Quick start

### Linux desktop

```bash
pip install bcrypt passlib
./hashcrack.py
```

### Termux (Android)

Copy `hashcrack.py` and `install-termux.sh` to the phone (e.g. via
`termux-setup-storage` then copy from Download), then:

```bash
bash install-termux.sh
```

The installer sets up python, p7zip, bcrypt, passlib, creates the
`hashcrack` command, and prepares `~/wordlists/`.

On a **rooted** device the tool also auto-boosts CPU clocks while running
(~+25–80% on Snapdragon 865-class SoCs).

### One-liner tests

```bash
# identify a hash
./hashcrack.py --identify -H '<hash>'

# wordlist attack
./hashcrack.py -H 5f4dcc3b5aa765d61d8327deb882cf99 -w wordlist.txt

# wordlist + mutations (capital first letter, trailing digits, leet, years)
./hashcrack.py -H <hash> -w rockyou.txt -r

# mask: 4 lowercase letters + 2 digits
./hashcrack.py -H <hash> --mask "?l?l?l?l?d?d"

# 6-digit PIN
./hashcrack.py -H <hash> --digits 6

# test specific candidates
./hashcrack.py -H <hash> --literal "password,test123"

# combine two wordlists (word1 + word2)
./hashcrack.py -H <hash> --combo names.txt numbers.txt

# force algorithm / supply username where needed
./hashcrack.py -H <hash> -w wl.txt --algo ntlm
./hashcrack.py -H 'md5<32hex>' -w wl.txt --user postgres

# encrypted zip (ZipCrypto & AES-256)
./hashcrack.py -H file.zip
```

Interactive menu (no arguments) walks through everything: paste hash → pick
algorithm → pick attack → pick wordlist → watch the animated panel.

### Mask codes

| Code | Meaning |
|:--|:--|
| `?l` | lowercase |
| `?u` | uppercase |
| `?d` | digits |
| `?s` | symbols |
| `?a` | all printable |
| `?h` / `?H` | hex lower / upper |

## Wordlists

The tool scans (smallest first) anything matching `*.txt`/`*.lst`/`*.dic`
in `~/wordlists/` and the tool's own folder. Recommended:

- [rockyou.txt](https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt) — 14M passwords
- Indonesian passwords: [elliottophellia/wordlist](https://github.com/elliottophellia/wordlist)
- [SecLists](https://github.com/danielmiessler/SecLists) — language-specific common passwords

## Typical performance

| Device | SHA-256 | bcrypt cost 10 |
|:--|--:|--:|
| Laptop 4-core (i7-7600U) | ~300k H/s | ~40 H/s |
| Phone 8-core (SD865, Termux, boosted) | ~116k H/s | ~75–82 H/s |

bcrypt is intentionally slow — large wordlists take hours on any CPU-only
setup. Use `termux-wake-lock` on Android so the process isn't frozen when
the screen turns off.

## Files

```
hashcrack.py          main tool (single file, no required deps)
install-termux.sh     automated Termux installer
top1m.txt             1M-password wordlist (optional)
```

## License

MIT © JackRipper-ID
