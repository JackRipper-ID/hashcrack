#!/usr/bin/env python3
"""
hashcrack.py - local hash cracker (CPU-only) with a fully animated TUI.
Works on Linux desktop and Android Termux.

  HASHCRACK by JackRipper-ID
  https://github.com/JackRipper-ID/hashcrack
"""

import argparse
import base64
import binascii
import hashlib
import itertools
import math
import multiprocessing as mp
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import zlib
from collections import deque


IS_TERMX = bool(os.environ.get("TERMUX_VERSION")) or "/com.termux" in os.environ.get("PREFIX", "")
IS_ANDROID = os.path.exists("/system/build.prop") or IS_TERMX


def _boost_cpu():
    if not (IS_ANDROID and os.getuid() == 0):
        return
    def _w(path, val):
        try:
            with open(path, "w") as f:
                f.write(val)
        except Exception:
            pass
    try:
        peak = int(open("/sys/devices/system/cpu/cpufreq/policy7/"
                        "cpuinfo_max_freq").read())
        _w("/sys/power/cpufreq_max_limit", str(peak))
    except Exception:
        pass
    import glob
    for pol in glob.glob("/sys/devices/system/cpu/cpufreq/policy*"):
        try:
            hw = int(open(pol + "/cpuinfo_max_freq").read())
            _w(pol + "/scaling_max_freq", str(hw))
        except Exception:
            pass

try:
    _CTX_NAME = "fork" if "fork" in mp.get_all_start_methods() else "spawn"
except Exception:
    _CTX_NAME = "spawn"


def cpu_count():
    try:
        n = len(os.sched_getaffinity(0))
        return max(1, n)
    except Exception:
        return os.cpu_count() or 1


def _stdout_tty():
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


_NO_COLOR = bool(os.environ.get("NO_COLOR")) or not _stdout_tty()


def _c(code):
    return "" if _NO_COLOR else code


RESET = _c("\033[0m")
BOLD = _c("\033[1m")
DIM = _c("\033[2m")
CYAN = _c("\033[96m")
BLUE = _c("\033[94m")
GREEN = _c("\033[92m")
YELLOW = _c("\033[93m")
RED = _c("\033[91m")
MAGENTA = _c("\033[95m")
GREY = _c("\033[90m")


def _fg(n):
    return "" if _NO_COLOR else f"\033[38;5;{n}m"


def tw():
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except Exception:
        return 80


def rule(ch="─", color=GREY, width=None):
    w = width or min(tw(), 78)
    print(f"{color}{ch * w}{RESET}")


def banner():
    w = min(tw(), 78)
    art = [
        "  ██╗  ██╗ █████╗ ███████╗██╗  ██╗ ██████╗██████╗  █████╗  ██████╗██╗  ██╗",
        "  ██║  ██║██╔══██╗██╔════╝██║  ██║██╔════╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝",
        "  ███████║███████║███████╗███████║██║     ██████╔╝███████║██║     █████╔╝ ",
        "  ██╔══██║██╔══██║╚════██║██╔══██║██║     ██╔══██╗██╔══██║██║     ██╔═██╗ ",
        "  ██║  ██║██║  ██║███████║██║  ██║╚██████╗██║  ██║██║  ██║╚██████╗██║  ██╗",
        "  ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝",
    ]
    if w >= 76:
        print()
        grad = [51, 45, 39, 33, 27, 21]
        for i, line in enumerate(art):
            print(f"{_fg(grad[i])}{line}{RESET}")
        env = " - termux" if IS_TERMX else (" - android" if IS_ANDROID else "")
        boosted = ""
        if IS_ANDROID and os.getuid() == 0:
            try:
                cur = int(open("/sys/devices/system/cpu/cpufreq/policy7/"
                               "scaling_max_freq").read())
                if cur >= 2500000:
                    boosted = " - boost"
            except Exception:
                pass
        print(f"{GREY}{'local - CPU-only - ' + str(cpu_count()) + ' core'
              + env + boosted:^{w}}{RESET}")
        print(f"{GREY}{'by JackRipper-ID':^{w}}{RESET}")
    else:
        print(f"\n{CYAN}{BOLD}  HASHCRACK{RESET}  "
              f"{GREY}local - CPU-only - by JackRipper-ID{RESET}")
    print()


def header(title, sub=""):
    print()
    rule("─", BLUE)
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    if sub:
        print(f"{GREY}  {sub}{RESET}")
    rule("─", BLUE)


def ok(msg):    print(f"{GREEN}  [OK] {msg}{RESET}")
def warn(msg):  print(f"{YELLOW}  ! {msg}{RESET}")
def err(msg):   print(f"{RED}  [X] {msg}{RESET}")
def info(msg):  print(f"{BLUE}  > {msg}{RESET}")
def kv(k, v, color=RESET):
    print(f"  {GREY}{k:<14}{RESET}{color}{v}{RESET}")


try:
    hashlib.new("md4", b"x")
    _HAVE_MD4 = True
except Exception:
    _HAVE_MD4 = False


def _md4_py(data):
    """Implementasi MD4 murni Python (fallback bila OpenSSL menolak md4)."""
    def lrot(x, n):
        x &= 0xFFFFFFFF
        return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF

    h = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476]
    ml = len(data) * 8
    data = data + b"\x80" + b"\x00" * ((56 - len(data) - 1) % 64) + (ml & 0xFFFFFFFF).to_bytes(4, "little") + b"\x00" * 4

    F = lambda x, y, z: (x & y) | (~x & z)
    G = lambda x, y, z: (x & y) | (x & z) | (y & z)
    H4 = lambda x, y, z: x ^ y ^ z

    for off in range(0, len(data), 64):
        X = list(int.from_bytes(data[off + i * 4: off + i * 4 + 4], "little") for i in range(16))
        a, b, c, d = h

        for s, k in [(3, 0), (7, 1), (11, 2), (19, 3), (3, 4), (7, 5), (11, 6), (19, 7),
                     (3, 8), (7, 9), (11, 10), (19, 11), (3, 12), (7, 13), (11, 14), (19, 15)]:
            a = lrot((a + F(b, c, d) + X[k]) & 0xFFFFFFFF, s)
            a, b, c, d = d, a, b, c

        for s, k in [(3, 0), (5, 4), (9, 8), (13, 12), (3, 1), (5, 5), (9, 9), (13, 13),
                     (3, 2), (5, 6), (9, 10), (13, 14), (3, 3), (5, 7), (9, 11), (13, 15)]:
            a = lrot((a + G(b, c, d) + X[k] + 0x5A827999) & 0xFFFFFFFF, s)
            a, b, c, d = d, a, b, c

        for s, k in [(3, 0), (9, 8), (11, 4), (15, 12), (3, 2), (9, 10), (11, 6), (15, 14),
                     (3, 1), (9, 9), (11, 5), (15, 13), (3, 3), (9, 11), (11, 7), (15, 15)]:
            a = lrot((a + H4(b, c, d) + X[k] + 0x6ED9EBA1) & 0xFFFFFFFF, s)
            a, b, c, d = d, a, b, c

        h[0] = (h[0] + a) & 0xFFFFFFFF
        h[1] = (h[1] + b) & 0xFFFFFFFF
        h[2] = (h[2] + c) & 0xFFFFFFFF
        h[3] = (h[3] + d) & 0xFFFFFFFF

    return b"".join(x.to_bytes(4, "little") for x in h)


def md4_digest(data):
    if _HAVE_MD4:
        return hashlib.new("md4", data).digest()
    return _md4_py(data)


HEX_LEN = {
    8: ["crc32"],
    16: ["mysql323", "des_crypt"],
    32: ["md5", "ntlm", "lm", "msdcc", "htdigest", "oracle11", "oracle10"],
    40: ["sha1", "ripemd160"],
    41: ["mysql41"],
    56: ["sha224", "sha3_224", "sha512_224"],
    64: ["sha256", "blake2s", "sha3_256", "sm3", "sha512_256", "msdcc2"],
    96: ["sha384", "sha3_384"],
    128: ["sha512", "blake2b", "sha3_512"],
}

SIMPLE_ALGOS = {"md5", "sha1", "sha224", "sha256", "sha384", "sha512",
                "sha3_224", "sha3_256", "sha3_384", "sha3_512",
                "blake2s", "blake2b", "ripemd160", "sm3",
                "sha512_224", "sha512_256", "mysql323", "mysql41",
                "ntlm", "lm", "mssql2000", "mssql2005"}

NEEDS_USER = {"msdcc", "msdcc2", "oracle10", "htdigest", "postgres_md5", "cisco_asa"}


def detect_kind(h):
    h = h.strip()

    if os.path.isfile(h) and h.lower().endswith(".zip"):
        return "zip", "zip", h

    if re.fullmatch(r"[0-9A-Fa-f]{16}", h):
        return "hex", "mysql323", None

    if re.fullmatch(r"\*[0-9A-F]{40}", h):
        return "hex", "mysql41", None

    CRYPT_MAP = [
        (r"^\$1\$", "md5_crypt"),
        (r"^\$apr1\$", "apr_md5_crypt"),
        (r"^\$5\$", "sha256_crypt"),
        (r"^\$6\$", "sha512_crypt"),
        (r"^\$2[abxy]\$", "bcrypt"),
        (r"^\$P\$|^\$H\$", "phpass"),
        (r"^\$pbkdf2-sha1\$", "pbkdf2_sha1"),
        (r"^\$pbkdf2-sha256\$", "pbkdf2_sha256"),
        (r"^\$pbkdf2-sha512\$", "pbkdf2_sha512"),
        (r"^\$pbkdf2\$", "pbkdf2_sha1"),
        (r"^\$bcrypt-sha256\$", "bcrypt_sha256"),
        (r"^\$scram\$", "scram"),
        (r"^\$md5,rounds=", "sun_md5_crypt"),
        (r"^\$3\$\$", "bsd_nthash"),
        (r"^\$p5k2\$", "dlitz_pbkdf2_sha1"),
        (r"^\{PKCS5S2\}", "atlassian_pbkdf2_sha1"),
        (r"^\{SSHA\}", "ldap_salted_sha1"),
        (r"^\{FSHP", "fshp"),
        (r"^grub\.pbkdf2\.sha512\.", "grub_pbkdf2_sha512"),
        (r"^pbkdf2_sha256\$", "django_pbkdf2_sha256"),
        (r"^pbkdf2_sha1\$", "django_pbkdf2_sha1"),
        (r"^\$sha1\$", "sha1_crypt"),
        (r"^sha1\$", "sha1_crypt"),
        (r"^_[0-9A-Za-z./]{19}$", "bsdi_crypt"),
        (r"^[0-9A-Za-z./]{24}$", "crypt16"),
        (r"^\*?[0-9A-F]{40}$", "mysql41"),
    ]
    for pat, name in CRYPT_MAP:
        if re.match(pat, h):
            return "crypt", name, None

    m = re.fullmatch(r"md5([0-9A-Fa-f]{32})", h)
    if m:
        return "hex", "postgres_md5", m.group(1)

    if re.fullmatch(r"0x[0-9A-Fa-f]{92}", h):
        return "hex_multi", ["mssql2000", "mssql2005"], None

    if re.fullmatch(r"[0-9A-Fa-f]+", h) and len(h) % 2 == 0:
        cands = HEX_LEN.get(len(h))
        if cands:
            if len(cands) == 1:
                return "hex", cands[0], None
            return "hex_multi", cands, None
        return "unknown", None, None

    return "unknown", None, None


def _mysql323(s):
    """MySQL 3.23 password hash (two 31-bit halves)."""
    import passlib.hash as ph
    return ph.mysql323.hash(s).upper()


def _nthash(s):
    """Windows NT hash (md4 of utf-16le)."""
    return md4_digest(s.encode("utf-16le")).hex()


def _lmhash(s):
    """Windows LM hash (uppercased, padded to 14 bytes)."""
    import passlib.hash as _ph
    return _ph.lmhash.hash(s[:14]) if hasattr(_ph, "lmhash") else ""


def _digest_for(algo, cand):
    """Get hex digest for a plain hex algorithm."""
    if algo == "md4":
        return md4_digest(cand.encode()).hex()
    if algo == "ntlm":
        return _nthash(cand)
    if algo == "mysql323":
        return _mysql323(cand)
    if algo == "mysql41":
        inner = hashlib.sha1(cand.encode()).digest()
        return "*" + hashlib.sha1(inner).hexdigest().upper()
    if algo == "lm":
        import passlib.hash as ph
        return ph.lmhash.hash(cand).upper()
    return hashlib.new(algo, cand.encode("utf-8", "surrogatepass")).hexdigest()


_target = _kind = _algo = _verifier = _counter = _extra = None
_algos = None


def _init_worker(target, kind, algo, counter, extra=None):
    global _target, _kind, _algo, _verifier, _counter, _extra, _algos
    _target, _kind, _algo, _counter, _extra = target, kind, algo, counter, extra
    _algos = algo if isinstance(algo, list) else [algo]
    _verifier = None
    if kind == "crypt":
        bc = next((a for a in _algos if a.startswith("bcrypt")), None)
        if bc:
            import bcrypt as _b
            tgt = target
            if tgt.startswith("$2y$") or tgt.startswith("$2x$"):
                tgt = "$2b$" + tgt[4:]
            _verifier = ("bcrypt", _b, tgt.encode())
        else:
            import passlib.hash as ph
            _verifier = ("passlib", ph, target)


def _check_with(cand, algo):
    """Like _check but against one specific algorithm."""
    global _algo
    if _kind == "hex_multi":
        old = _algo
        _algo = algo
        try:
            return _check(cand)
        finally:
            _algo = old
    return _check(cand)


def _check(cand):
    if _kind in ("hex", "hex_multi"):
        tgt = _target.lower().removeprefix("0x")
        if tgt.startswith("md5"):
            tgt = tgt[3:]
        if _algo in NEEDS_USER:
            import passlib.hash as ph
            obj = getattr(ph, _algo, None)
            if obj is None:
                return False
            try:
                if _algo == "htdigest":
                    return obj.verify(cand, _target, user=_extra or "user",
                                      realm=_extra or "realm")
                if _algo == "postgres_md5":
                    return hashlib.md5((cand + (_extra or "postgres")).encode()).hexdigest() == tgt
                return obj.verify(cand, _target, user=_extra or "user")
            except Exception:
                return False
        if _algo in ("mssql2000", "mssql2005"):
            import passlib.hash as ph
            try:
                return getattr(ph, _algo).verify(cand, _target)
            except Exception:
                return False
        if _algo in ("crc32", "des_crypt", "crypt16", "bsdi_crypt"):
            import passlib.hash as ph
            try:
                obj = getattr(ph, _algo)
                if _algo == "crc32":
                    return obj.hash(cand).lower() == tgt
                return obj.verify(cand, _target)
            except Exception:
                return False
        try:
            return _digest_for(_algo, cand).lower() == tgt
        except Exception:
            return False
    if _kind == "crypt":
        which, obj, tgt = _verifier
        try:
            if which == "bcrypt":
                return obj.checkpw(cand.encode("utf-8", "surrogatepass"), tgt)
            real = {"md5crypt": "md5_crypt", "sha256crypt": "sha256_crypt",
                    "sha512crypt": "sha512_crypt"}.get(_algo, _algo)
            hobj = getattr(obj, real, None)
            if hobj is None:
                return False
            if real == "htdigest":
                return hobj.verify(cand, tgt, user=_extra or "user",
                                   realm=_extra or "realm")
            if real in NEEDS_USER:
                return hobj.verify(cand, tgt, user=_extra or "user")
            return hobj.verify(cand, tgt)
        except Exception:
            return False
    return False


def worker_chunk(candidates):
    """Return (candidate, algo) if matched, else None."""
    checked = 0
    for cand in candidates:
        checked += 1
        for algo in _algos:
            if _check_with(cand, algo):
                _counter.value += checked
                return cand, algo
    _counter.value += checked
    return None


LEET = str.maketrans("aeiostAEIOST", "431057431057")
SUFFIXES = ("", "1", "12", "123", "1234", "12345", "0", "00", "007",
            "2020", "2021", "2022", "2023", "2024", "2025", "2026",
            "!", "!!", "@", "#", "$", "1!", "123!", "?", ".")


def apply_rules(word):
    base = {word, word.lower(), word.upper(), word.capitalize()}
    base |= {v.translate(LEET) for v in base}
    out, dedup = [], set()
    for v in base:
        for suf in SUFFIXES:
            c = v + suf
            if c not in dedup:
                dedup.add(c)
                out.append(c)
    return out


def gen_wordlist(path, rules=False):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            base = line.rstrip("\r\n")
            if not base:
                continue
            yield base
            if rules:
                for v in apply_rules(base):
                    if v != base:
                        yield v


def gen_combo(path1, path2, limit=200000):
    """All w1 + w2 combos (with a safety cap)."""
    with open(path1, "r", encoding="utf-8", errors="ignore") as f1, \
         open(path2, "r", encoding="utf-8", errors="ignore") as f2:
        w2 = [l.rstrip("\r\n") for l in f2 if l.strip()]
    count = 0
    with open(path1, "r", encoding="utf-8", errors="ignore") as f1:
        for a in f1:
            a = a.rstrip("\r\n")
            if not a:
                continue
            for b in w2:
                yield a + b
                count += 1
                if count >= limit:
                    return


MASK_SETS = {
    "l": "abcdefghijklmnopqrstuvwxyz",
    "u": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "d": "0123456789",
    "s": " !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~",
    "a": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~",
    "h": "0123456789abcdef",
    "H": "0123456789ABCDEF",
}


def parse_mask(mask):
    pools, i = [], 0
    while i < len(mask):
        if mask[i] == "?" and i + 1 < len(mask):
            nxt = mask[i + 1]
            if nxt in MASK_SETS:
                pools.append(MASK_SETS[nxt])
                i += 2
                continue
            if nxt == "?":
                pools.append("?")
                i += 2
                continue
        pools.append(mask[i])
        i += 1
    return pools


def mask_size(mask):
    total = 1
    for p in parse_mask(mask):
        total *= len(p)
    return total


def gen_mask(mask):
    for combo in itertools.product(*parse_mask(mask)):
        yield "".join(combo)


def gen_digits(max_len):
    for n in range(0, max_len + 1):
        for combo in itertools.product("0123456789", repeat=n):
            yield "".join(combo)


def chunks(it, size):
    buf = []
    for x in it:
        buf.append(x)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


def human_time(s):
    if s < 1:       return "0 s"
    if s < 60:      return f"{s:.0f} s"
    if s < 3600:    return f"{s / 60:.1f} min"
    if s < 86400:   return f"{s / 3600:.1f} h"
    if s < 31536000: return f"{s / 86400:.1f} d"
    return f"{s / 31536000:.1f} tahun"


def fmt_num(n):
    return f"{n:,}".replace(",", ".")


SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
WAVE = "▁▂▃▄▅▆▇█"
GRAD = (51, 45, 39, 33, 27, 21)


class LivePanel:
    """Live panel redrawn in place - no scrolling."""

    def __init__(self, total_hint, algo, detail="", enabled=True):
        self.total = total_hint
        self.algo = algo
        self.detail = detail
        self.enabled = enabled and _stdout_tty()
        self.counter = None
        self.t0 = time.time()
        self.frame = 0
        self.drawn = False
        self.stop_flag = None
        self.thread = None
        self.hist = deque(maxlen=32)
        self.last_done = 0
        self.mark_t = 0.0
        self.inst = 0.0

    def begin(self, counter, t0):
        self.counter = counter
        self.t0 = t0
        self.mark_t = t0
        if not self.enabled:
            return
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
        self._draw()
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def end(self):
        if self.stop_flag:
            self.stop_flag.set()
        if self.thread:
            self.thread.join(timeout=0.5)
        if not self.enabled:
            return
        self._draw(final=True)
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

    def _loop(self):
        while not self.stop_flag.wait(0.08):
            self._draw()

    def _draw(self, final=False):
        self.frame += 1
        done = self.counter.value if self.counter else 0
        now = time.time()
        elapsed = max(now - self.t0, 1e-6)
        rate = done / elapsed
        if now - self.mark_t >= 0.4:
            self.inst = (done - self.last_done) / (now - self.mark_t)
            self.last_done = done
            self.mark_t = now
            self.hist.append(max(self.inst, 0.0))

        W = max(60, min(tw(), 78))
        inner = W - 4
        bar_w = inner - 8
        spin = SPIN[self.frame % len(SPIN)]

        if self.total:
            frac = min(1.0, done / self.total)
            fill = int(round(bar_w * frac))
            pct = f"{frac * 100:5.1f}%"
            eta = (self.total - done) / rate if rate > 0 else 0
            eta_s = f"ETA {human_time(eta)}"
        else:
            frac = 0.0
            fill = int(bar_w * (0.5 + 0.5 * math.sin(self.frame * 0.18)))
            pct = "  ???"
            eta_s = human_time(elapsed)

        cells = []
        for i in range(bar_w):
            if i < fill:
                k = int((math.sin(i * 0.33 - self.frame * 0.16) + 1) / 2 * (len(GRAD) - 1))
                cells.append(f"{_fg(GRAD[k])}█{RESET}")
            else:
                cells.append(f"{_fg(238)}░{RESET}")
        bar = "".join(cells)

        hist = list(self.hist)[-26:] or [0.0]
        mx = max(hist) or 1.0
        spark = "".join(WAVE[min(len(WAVE) - 1, int(v / mx * (len(WAVE) - 1)))]
                        for v in hist)
        spark = f"{_fg(45)}{spark}{RESET}"

        title = "done" if final else "analyzing"
        head = f"  {_fg(51)}{spin}{RESET} {BOLD}{title}{RESET}  {GREY}{self.detail}{RESET}"
        stats = (f"  {BOLD}{_fg(51)}{pct.strip():>6}{RESET}   "
                 f"{GREY}{fmt_num(done)}"
                 f"{('/' + fmt_num(self.total)) if self.total else ''}{RESET}   "
                 f"{_fg(45)}{rate:,.0f} H/s{RESET}   "
                 f"{YELLOW}{eta_s}{RESET}")
        speed = (f"  {GREY}speed{RESET} {spark} "
                 f"{GREY}{fmt_num(int(self.inst))} H/s{RESET}   "
                 f"{GREY}time{RESET} {human_time(elapsed)}")

        lines = [
            f"  {_fg(39)}╭{'─' * inner}╮{RESET}",
            f"  {_fg(39)}│{RESET}{head}{' ' * max(0, inner - len(_strip(head)) - 1)} {_fg(39)}│{RESET}",
            f"  {_fg(39)}│{' ' * inner}│{RESET}",
            f"  {_fg(39)}│{RESET}  {bar}  {_fg(39)}│{RESET}",
            f"  {_fg(39)}│{RESET}{stats}{' ' * max(0, inner - len(_strip(stats)) - 1)} {_fg(39)}│{RESET}",
            f"  {_fg(39)}│{' ' * inner}│{RESET}",
            f"  {_fg(39)}│{RESET}{speed}{' ' * max(0, inner - len(_strip(speed)) - 1)} {_fg(39)}│{RESET}",
            f"  {_fg(39)}╰{'─' * inner}╯{RESET}",
        ]

        buf = []
        if self.drawn:
            buf.append(f"\033[{len(lines)}A")
        else:
            self.drawn = True
        for l in lines:
            buf.append("\033[2K" + l + "\n")
        sys.stdout.write("".join(buf))
        sys.stdout.flush()


def _strip(s):
    return re.sub(r"\033\[[0-9;]*m", "", s)


def run(target, kind, algo, stream, total_hint, workers, chunk_size,
        panel=None, detail="", extra=None):
    t0 = time.time()
    ctx = mp.get_context(_CTX_NAME)
    counter = ctx.Value("L", 0)
    pool = ctx.Pool(workers, initializer=_init_worker,
                    initargs=(target, kind, algo, counter, extra))
    found = None
    hit_algo = None
    if panel is not None:
        panel.detail = detail
        panel.begin(counter, t0)
    try:
        for res in pool.imap_unordered(worker_chunk, chunks(stream, chunk_size)):
            if res is not None:
                found, hit_algo = res
                break
    except KeyboardInterrupt:
        pool.terminate()
        if panel is not None:
            panel.end()
        raise
    finally:
        pool.close()
        pool.join()
    if panel is not None:
        panel.end()
    elapsed = time.time() - t0
    hit = hit_algo if found is not None else algo
    return found, counter.value, elapsed, hit


def _box(title, lines, color):
    w = min(tw(), 78) - 4
    inner = max([len(_strip(l)) for l in lines] + [len(title) + 2, 20])
    inner = min(inner, w - 2)
    print(f"{color}┌{'─' * (inner + 2)}┐{RESET}")
    tpad = inner - len(title)
    print(f"{color}│{RESET} {BOLD}{color}{title}{RESET}{' ' * max(0, tpad + 1)}{color}│{RESET}")
    print(f"{color}├{'─' * (inner + 2)}┤{RESET}")
    for l in lines:
        pad = max(0, inner - len(_strip(l)))
        print(f"{color}│{RESET} {l}{' ' * pad} {color}│{RESET}")
    print(f"{color}└{'─' * (inner + 2)}┘{RESET}")


def show_result(found, done, elapsed, target, algo):
    rate = done / elapsed if elapsed > 0 else 0
    print("\r\033[K", end="")
    print()
    if found is not None:
        _box("PASSWORD FOUND", [f"{BOLD}{CYAN}{found}{RESET}"], GREEN)
        print()
        kv("hash", target[:52] + ("..." if len(target) > 52 else ""), GREY)
        kv("algorithm", algo, CYAN)
        kv("time", f"{elapsed:.2f} s", GREEN)
        kv("candidates", f"{fmt_num(done)}  ({rate:,.0f} H/s)", GREEN)
        print()
        return True
    _box("NOT FOUND", [f"{YELLOW}{fmt_num(done)} candidates tested{RESET}",
                             f"{YELLOW}speed {rate:,.0f} H/s{RESET}"], RED)
    print()
    kv("time", human_time(elapsed), YELLOW)
    print(f"  {GREY}Hint: try a wordlist + mutations (-r), or a bigger wordlist.{RESET}")
    print()
    return False


COMMON = """123456 password 12345678 qwerty 123456789 12345 1234 111111 1234567 dragon
123123 baseball abc123 football monkey letmein 696969 shadow master 666666
qwertyuiop 123321 mustang 1234567890 michael 654321 superman 1qaz2wsx 7777777
121212 000000 qazwsx 123qwe killer trustno1 jordan jennifer zxcvbnm asdfgh
hunter buster soccer harley batman andrew tigger sunshine iloveyou 2000
charlie robert thomas hockey ranger daniel starwars klaster 112233 george
computer michelle jessica pepper 1111 zxcvbn 555555 11111111 131313 freedom
777777 pass maggie 159753 aaaaaa ginger princess joshua cheese amanda summer
love ashley nicole chelsea biteme matthew access yankees 987654321 dallas
austin thunder taylor matrix admin sayang cinta rahasia indonesia jakarta
bismillah password1 qwerty123 abc12345 admin123 root toor guest test testing
letmein1 welcome welcome1 changeme secret mypassword passw0rd p@ssw0rd""".split()


def find_wordlists():
    base = os.path.dirname(os.path.abspath(__file__))
    cands = [
        os.path.join(base, "top1m.txt"),
        os.path.expanduser("~/top1m.txt"),
        "/tmp/opencode/top1m.txt",
        "/usr/share/wordlists/rockyou.txt",
        "/usr/share/wordlists/rockyou.txt.gz",
        "/usr/share/dict/words",
    ]
    dirs = [os.path.expanduser("~/wordlists"), base,
            "/data/data/com.termux/files/home/wordlists",
            "/storage/emulated/0/wordlists"]
    for d in dirs:
        try:
            for name in sorted(os.listdir(d)):
                if name.lower().endswith((".txt", ".lst", ".dic", ".dict")):
                    cands.append(os.path.join(d, name))
        except OSError:
            pass

    out, seen = [], set()
    for c in cands:
        if not os.path.isfile(c):
            continue
        try:
            size = os.path.getsize(c)
        except OSError:
            continue
        real = os.path.realpath(c)
        if real in seen or size < 100:
            continue
        seen.add(real)
        out.append((c, size))
    out.sort(key=lambda t: t[1])
    return out


def ensure_deps():
    """Check optional modules and give install hints."""
    missing = []
    try:
        import bcrypt  # noqa: F401
    except ImportError:
        missing.append(("bcrypt", "pip install bcrypt"))
    try:
        import passlib  # noqa: F401
    except ImportError:
        missing.append(("passlib", "pip install passlib"))
    return missing


def ask(prompt, default=""):
    d = f" {GREY}[{default}]{RESET}" if default else ""
    try:
        v = input(f"{CYAN}  ? {RESET}{prompt}{d}: ").strip()
    except (EOFError, KeyboardInterrupt):
        return default
    return v or default


def ask_int(prompt, default, lo, hi):
    while True:
        v = ask(prompt, str(default))
        try:
            n = int(v)
            if lo <= n <= hi:
                return n
            warn(f"must be between {lo} and {hi}")
        except ValueError:
            warn("enter digit count")


ALGO_NOTE = {
    "md5": "sangat cepat", "md4": "sangat cepat (NTLM/LM)",
    "sha1": "cepat", "sha224": "cepat", "sha256": "cepat",
    "sha384": "cepat", "sha512": "cepat", "sha3": "sedang",
    "blake2s": "cepat", "blake2b": "cepat", "ripemd160": "cepat",
    "sm3": "cepat",
    "ntlm": "Windows login", "lm": "Windows lama (<= XP)",
    "mysql323": "MySQL versi < 4.1", "mysql41": "MySQL >= 4.1",
    "postgres_md5": "PostgreSQL (md5:user)", "oracle10": "Oracle < 11g",
    "oracle11": "Oracle >= 11g", "htdigest": "HTTP Digest Auth",
    "mssql2000": "MS SQL 2000", "mssql2005": "MS SQL 2005+",
    "msdcc": "MS domain cache v1", "msdcc2": "MS domain cache v2",
    "md5_crypt": "lambat (5000 putaran)",
    "apr_md5_crypt": "lambat (htpasswd)",
    "sha256_crypt": "lambat (5000+ putaran)",
    "sha512_crypt": "lambat (5000+ putaran)",
    "sha1_crypt": "lambat",
    "sun_md5_crypt": "sangat lambat",
    "bcrypt": "sangat lambat — sengaja",
    "bcrypt_sha256": "sangat lambat",
    "phpass": "lambat (WordPress/phpBB)",
    "pbkdf2_sha1": "sedang-lambat",
    "pbkdf2_sha256": "lambat",
    "pbkdf2_sha512": "lambat",
    "django_pbkdf2_sha256": "lambat (Django)",
    "django_pbkdf2_sha1": "sedang-lambat",
    "grub_pbkdf2_sha512": "sangat lambat (GRUB)",
    "scram": "lambat",
    "bsdi_crypt": "lambat",
    "des_crypt": "sangat cepat (13 char)",
    "cisco_type7": "instan (bukan hash asli)",
    "cisco_pix": "instan-ish",
    "cisco_asa": "instan-ish",
    "atlassian_pbkdf2_sha1": "lambat",
    "ldap_salted_sha1": "sedang",
    "fshp": "lambat",
    "bsdi_crypt2": "lambat",
    "crypt16": "lambat",
    "bigcrypt": "lambat",
    "dlitz_pbkdf2_sha1": "lambat",
    "cta_pbkdf2_sha1": "lambat",
    "zip": "ZipCrypto cepat / AES lambat",
    "sqlite": "verifikasi file",
}


def ident_mode():
    header("Identify Hash")
    h = ask("paste hash or zip file path/sqlite")
    if not h:
        return
    kind, algo, extra = detect_kind(h)
    if kind == "unknown":
        err("unknown format")
        print(f"  {GREY}hex 16/20/28/32/48/64, atau $1$ $apr1$ $2b$ $5$ $6$ "
              f"$P$ $pbkdf2$ etc{RESET}")
        return
    print()
    label = {"hex": "hex digest", "hex_multi": "hex (multiple candidates)",
             "crypt": "crypt / formatted", "zip": "ZIP file", "sqlite": "SQLite file"}
    kv("type", label.get(kind, kind), CYAN)
    kv("algorithm", ", ".join(algo) if isinstance(algo, list) else algo, GREEN)
    if kind == "zip":
        import zipfile
        try:
            with zipfile.ZipFile(extra) as z:
                names = z.namelist()
                kv("file", f"{len(names)} entri", RESET)
                kv("enkripsi", "AES" if any(i.compress_type == 51 for i in z.infolist())
                   else "ZipCrypto", YELLOW)
        except Exception as e:
            warn(f"cannot read: {e}")
    if kind in ("hex", "hex_multi"):
        kv("panjang", str(len(h)), RESET)
    if isinstance(algo, str) and algo.startswith("bcrypt"):
        try:
            cost = int(h.split("$")[2])
            kv("cost", f"{cost}  (2^{cost} = {2 ** cost} putaran)", YELLOW)
        except (IndexError, ValueError):
            pass
    note = ALGO_NOTE.get(algo if isinstance(algo, str) else "")
    if note:
        kv("note", note, GREY)
    print()


def bench_mode():
    header("Benchmark", "mengukur speed nyata di mesin ini")
    core = cpu_count()
    info(f"{core} cores available")
    print()
    for label, name in [("md5", "md5"), ("sha1", "sha1"), ("sha256", "sha256")]:
        h = hashlib.new(name, b"benchmark").hexdigest()
        stream = ("bench%07d" % i for i in range(60000))
        found, done, el, _hit = run(h, "hex", name, stream, 60000, core, 5000, panel=None)
        rate = done / el if el > 0 else 0
        print(f"  {label:<8} {GREEN}{'█' * 24}{RESET} {BOLD}{rate:>12,.0f} H/s{RESET}")
    print()
    try:
        import bcrypt as _b
        h = "$2b$10$" + _b.hashpw(b"x", _b.gensalt(rounds=10)).decode()[7:]
        stream = (f"b{i}" for i in range(40))
        found, done, el, _hit = run(h, "crypt", "bcrypt", stream, 40, core, 10, panel=None)
        rate = done / el if el > 0 else 0
        print(f"  {'bcrypt':<8} {YELLOW}{'█' * 6}{RESET} {BOLD}{rate:>12,.1f} H/s{RESET} "
              f"{GREY}(sengaja lambat){RESET}")
    except Exception:
        pass
    try:
        h = _nthash("benchmark")
        stream = ("nt%07d" % i for i in range(30000))
        found, done, el, _hit = run(h, "hex", "ntlm", stream, 30000, core, 5000, panel=None)
        rate = done / el if el > 0 else 0
        print(f"  {'ntlm':<8} {GREEN}{'█' * 20}{RESET} {BOLD}{rate:>12,.0f} H/s{RESET}")
    except Exception:
        pass
    print()


def help_mode():
    header("Bantuan")
    print(f"""  {BOLD}Metode serangan{RESET}
  {CYAN}1. Kamus{RESET}           coba kata dari file — selalu mulai dari sini
  {CYAN}2. Kamus + aturan{RESET}  kata dasar dimutasi (Kapital, digits, simbol, leet)
  {CYAN}3. Pola (mask){RESET}     brute-force terarah, mis. 3 huruf + 2 digits
  {CYAN}4. Angka{RESET}           PIN / OTP
  {CYAN}5. Kata tertentu{RESET}   uji beberapa kata langsung
  {CYAN}6. Kombinasi{RESET}       semua pasangan w1+w2 dari dua wordlist

  {BOLD}Mask codes{RESET}
  {CYAN}?l{RESET} huruf kecil   {CYAN}?u{RESET} huruf besar   {CYAN}?d{RESET} digits
  {CYAN}?s{RESET} simbol        {CYAN}?a{RESET} semua         {CYAN}?h{RESET} hex kecil
  {CYAN}?H{RESET} hex besar

  {BOLD}Format hash didukung{RESET}""")
    for k, v in ALGO_NOTE.items():
        print(f"  {CYAN}{k:<24}{RESET} {GREY}{v}{RESET}")
    print(f"""
  {BOLD}Batasan jujur{RESET}
  Mode ini murni CPU. bcrypt/scrypt hanya realistis lewat wordlist —
  brute-force bcrypt 8 karakter bisa memakan ratusan tahun, itu
  memang tujuannya. Gunakan hanya pada hash milik Anda sendiri
  atau sistem yang Anda uji dengan izin.

  {BOLD}Di Termux{RESET}
  pkg install python && pip install bcrypt passlib
  Lalu jalankan: python hashcrack.py
  Wordlist taruh di ~/wordlists/ atau /storage/emulated/0/wordlists/""")


def build_mask_interactive():
    header("Mask Builder", "compose character sets one by one")
    presets = [
        ("6 lowercase", "?l?l?l?l?l?l"),
        ("8 lowercase", "?l?l?l?l?l?l?l?l"),
        ("4 huruf + 2 digits", "?l?l?l?l?d?d"),
        ("6 huruf + 2 digits", "?l?l?l?l?l?l?d?d"),
        ("kata kecil + 4 digits", "?l?l?l?l?l?l?l?l?d?d?d?d"),
        ("4 digits (PIN)", "?d?d?d?d"),
        ("6 digits (PIN)", "?d?d?d?d?d?d"),
        ("8 digits", "?d?d?d?d?d?d?d?d"),
        ("6 lower+upper", "?l?u?l?u?l?u"),
        ("custom", None),
    ]
    print(f"  {GREY}Quick presets:{RESET}")
    for i, (name, m) in enumerate(presets, 1):
        extra = f"  {GREY}{fmt_num(mask_size(m))} possibilities{RESET}" if m else ""
        print(f"   {CYAN}{i}{RESET}. {name}{extra}")
    print()
    ch = ask_int("choose mask", 1, 1, len(presets))
    name, mask = presets[ch - 1]
    if mask:
        info(f"mask: {BOLD}{mask}{RESET}  ({name})")
        return mask
    print()
    print(f"  {GREY}Codes: {RESET}?l ?u ?d ?s ?a ?h ?H  {GREY}example: ?l?l?l?d?d{RESET}")
    while True:
        m = ask("mask")
        if m and mask_size(m) > 1:
            info(f"{fmt_num(mask_size(m))} possibilities")
            return m
        warn("invalid or too-short mask")


def pick_wordlist():
    header("Choose Wordlist", "candidate passwords")
    found = find_wordlists()
    print()
    n = 1
    options = []
    if found:
        for path, size in found:
            mb = size / 1048576
            print(f"   {CYAN}{n}{RESET}. {path}  {GREY}({mb:.1f} MB){RESET}")
            options.append(path)
            n += 1
    print(f"   {CYAN}{n}{RESET}. built-in common passwords  {GREY}(~130 words){RESET}")
    options.append("__common__")
    n += 1
    print(f"   {CYAN}{n}{RESET}. enter custom path")
    options.append("__manual__")
    print()
    ch = ask_int("choose", 1 if found else n - 2, 1, len(options))
    choice = options[ch - 1]
    if choice == "__manual__":
        while True:
            p = ask("file path")
            if os.path.isfile(p):
                return p
            err("file not found")
    if choice == "__common__":
        p = "/tmp/hashcrack_common.txt" if not IS_TERMX else os.path.expanduser(
            "~/hashcrack_common.txt")
        with open(p, "w") as f:
            f.write("\n".join(COMMON))
        return p
    return choice


def pick_algo_from_multi(cands):
    """
    Panjang hex cocok beberapa format. Default: test all at once
    (hasilnya tetap akurat karena dicocokkan per hitungan).
    """
    header("Multiple Algorithms Match", "hex length matches several formats")
    print()
    print(f"   {CYAN}0{RESET}. {BOLD}test all at once{RESET}  {GREY}(recommended){RESET}")
    for i, c in enumerate(cands, 1):
        note = ALGO_NOTE.get(c, "")
        print(f"   {CYAN}{i}{RESET}. {c:<16} {GREY}{note}{RESET}")
    print()
    ch = ask_int("choose", 0, 0, len(cands))
    if ch == 0:
        simple = [a for a in cands if a in SIMPLE_ALGOS]
        return simple or cands
    return cands[ch - 1]


def _is_slow_algo(algo):
    """True bila algorithm lambat (butuh chunk kecil)."""
    names = algo if isinstance(algo, list) else [algo]
    for a in names:
        if not isinstance(a, str):
            continue
        if a.startswith("bcrypt") or "pbkdf2" in a or a in (
                "scram", "grub_pbkdf2_sha512", "sun_md5_crypt", "scrypt"):
            return True
    return False


def crack_mode():
    header("Crack Hash / File")
    h = ask("paste hash or zip file path")
    if not h:
        return None
    kind, algo, extra = detect_kind(h)
    if kind == "unknown":
        err("unknown hash format")
        print(f"  {GREY}Try the 'Identify Hash' option first to see supported formats{RESET}")
        print()
        return None

    if kind == "zip":
        return crack_zip(extra)

    if kind == "hex_multi":
        algo = pick_algo_from_multi(algo)
        if isinstance(algo, list):
            kind = "hex_multi"
        else:
            kind = "hex"
        if isinstance(algo, str) and algo in ("oracle10", "htdigest", "msdcc",
                                               "msdcc2", "postgres_md5"):
            extra = ask(f"username/realm for {algo}", "user")
    elif kind == "hex" and algo in ("oracle10", "htdigest", "msdcc", "msdcc2"):
        extra = ask(f"username/realm for {algo}", "user")

    print()
    kv("algorithm", ", ".join(algo) if isinstance(algo, list) else algo, GREEN)
    if isinstance(algo, str) and algo.startswith("bcrypt"):
        warn("bcrypt is slow: ~44 H/s on this laptop, ~10 H/s on phones.")
    print()
    print(f"  {BOLD}Attack:{RESET}")
    print(f"   {CYAN}1{RESET}. Wordlist             {GREY}fast, try first{RESET}")
    print(f"   {CYAN}2{RESET}. Wordlist + mutations {GREY}often works{RESET}")
    print(f"   {CYAN}3{RESET}. Mask pattern         {GREY}when you know the shape{RESET}")
    print(f"   {CYAN}4{RESET}. Digits only (PIN)    {GREY}4-8 digit{RESET}")
    print(f"   {CYAN}5{RESET}. Specific words       {GREY}test directly{RESET}")
    print(f"   {CYAN}6{RESET}. Combine 2 wordlists    {GREY}word1+word2{RESET}")
    print()
    method = ask_int("method", 1, 1, 6)

    total_hint = None
    rules = False
    if method in (1, 2):
        path = pick_wordlist()
        if not os.path.isfile(path):
            err("wordlist not found")
            return None
        rules = method == 2
        try:
            with open(path, "rb") as f:
                lines = sum(1 for _ in f)
        except OSError:
            lines = 0
        total_hint = lines * (len(apply_rules("abc")) if rules else 1)
        info(f"wordlist: {path}  {GREY}({fmt_num(lines)} baris){RESET}")
        stream = gen_wordlist(path, rules)
    elif method == 3:
        mask = build_mask_interactive()
        total_hint = mask_size(mask)
        stream = gen_mask(mask)
    elif method == 4:
        n = ask_int("panjang digit maksimum", 6, 1, 10)
        total_hint = sum(10 ** k for k in range(0, n + 1))
        stream = gen_digits(n)
    elif method == 6:
        p1 = ask("first wordlist (path)")
        p2 = ask("second wordlist (path)")
        if not (os.path.isfile(p1) and os.path.isfile(p2)):
            err("one of the wordlists was not found")
            return None
        total_hint = None
        info("combo mode: capped at 200,000 candidates for safety")
        stream = gen_combo(p1, p2)
    else:
        raw = ask("test words, comma-separated")
        words = [w.strip() for w in raw.split(",") if w.strip()]
        if not words:
            return None
        total_hint = len(words)
        stream = iter(words)

    print()
    core = cpu_count()
    t = ask_int("number of cores", core, 1, core)
    if total_hint and isinstance(algo, str) and algo.startswith("bcrypt"):
        est = total_hint / (11 * t)
        if est > 60:
            warn(f"estimated time: {human_time(est)}")
            if ask("continue? (y/n)", "y").lower() != "y":
                return None
    print()
    rule("─", GREY)
    print(f"  {BOLD}{MAGENTA}▶ mulai memecahkan{RESET}")
    rule("─", GREY)
    print()

    chunk = 200 if _is_slow_algo(algo) else 5000
    panel = LivePanel(total_hint, algo)
    try:
        found, done, elapsed, hit_algo = run(
            h, kind, algo, stream, total_hint, t, chunk,
            panel=panel, detail=str(algo), extra=extra)
    except KeyboardInterrupt:
        print("\r\033[K")
        warn("stopped by user")
        return None
    return 0 if show_result(found, done, elapsed, h, hit_algo) else 1


_zip_path = None
_zip_entry = None
_zip_aes = False
_zip_counter = None


def _zip_init(path, entry_name, aes, counter):
    global _zip_path, _zip_entry, _zip_aes, _zip_counter
    _zip_path, _zip_entry, _zip_aes, _zip_counter = path, entry_name, aes, counter


def _zip_try(pw):
    if _zip_aes:
        seven = shutil.which("7z") or shutil.which("7za") or shutil.which("7zr")
        if not seven:
            return False
        try:
            r = subprocess.run([seven, "t", f"-p{pw}", _zip_path],
                               capture_output=True, timeout=30)
            return r.returncode == 0
        except Exception:
            return False
    try:
        import zipfile
        with zipfile.ZipFile(_zip_path) as z:
            with z.open(_zip_entry, pwd=pw.encode("utf-8", "surrogatepass")) as f:
                f.read(64)
            return True
    except Exception:
        return False


def _zip_worker(chunk):
    checked = 0
    for pw in chunk:
        checked += 1
        if _zip_try(pw):
            if _zip_counter is not None:
                _zip_counter.value += checked
            return pw
    if _zip_counter is not None:
        _zip_counter.value += checked
    return None


def crack_zip(path):
    """Pecahkan password file zip (ZipCrypto via stdlib, AES via 7z)."""
    header("Encrypted ZIP")
    info(f"file: {path}")
    import zipfile
    try:
        with zipfile.ZipFile(path) as z:
            entries = z.infolist()
            if not any(e.flag_bits & 0x1 for e in entries):
                ok("this zip is NOT encrypted")
                return None
            has_aes = any(e.compress_type == 99 for e in entries)
            encrypted = [e for e in entries if e.flag_bits & 0x1]
            test_entry = next((e for e in encrypted if not e.is_dir()), encrypted[0])
            kv("method", "AES (requires 7z)" if has_aes else "ZipCrypto",
               YELLOW)
            kv("test entry", test_entry.filename, RESET)
    except Exception as e:
        err(f"cannot open: {e}")
        return None

    if has_aes and not (shutil.which("7z") or shutil.which("7za")):
        err("ZIP AES perlu 7z: pkg install p7zip (Termux) / apt install p7zip-full")
        return None

    core = cpu_count()
    t = ask_int("number of cores", core, 1, max(1, core))
    print()
    print(f"  {BOLD}Attack:{RESET}  1. wordlist   2. mask   3. digits   4. literal")
    mode = ask("method", "1")

    total_hint = None
    if mode == "1":
        path_w = pick_wordlist()
        total_hint = sum(1 for _ in open(path_w, "rb"))
        stream = (l.rstrip("\r\n") for l in
                  open(path_w, encoding="utf-8", errors="ignore"))
    elif mode == "2":
        mask = build_mask_interactive()
        total_hint = mask_size(mask)
        stream = gen_mask(mask)
    elif mode == "3":
        n = ask_int("digit maks", 6, 1, 8)
        total_hint = sum(10 ** k for k in range(n + 1))
        stream = gen_digits(n)
    else:
        raw = ask("words, comma-separated")
        words = [w.strip() for w in raw.split(",") if w.strip()]
        total_hint = len(words)
        stream = iter(words)

    ctx = mp.get_context(_CTX_NAME)
    counter = ctx.Value("L", 0)
    panel = LivePanel(total_hint, "zip", detail="zip")
    t0 = time.time()
    found = None
    pool = ctx.Pool(t, initializer=_zip_init,
                    initargs=(path, test_entry.filename, has_aes, counter))
    panel.begin(counter, t0)
    try:
        for res in pool.imap_unordered(_zip_worker, chunks(stream, 50)):
            if res is not None:
                found = res
                break
    except KeyboardInterrupt:
        pass
    finally:
        pool.terminate()
        pool.join()
        panel.end()

    elapsed = time.time() - t0
    done = counter.value
    if found:
        _box("ZIP PASSWORD FOUND", [f"{BOLD}{CYAN}{found}{RESET}"], GREEN)
        info(f"open with: 7z x -p'{found}' '{path}'")
        return 0
    warn(f"not found ({fmt_num(done)}  candidates in {human_time(elapsed)})")
    return 1


def interactive():
    banner()
    miss = ensure_deps()
    if miss:
        warn("optional modules not installed:")
        for name, cmd in miss:
            print(f"    {YELLOW}{name}{RESET} {GREY}→ {cmd}{RESET}")
        print()
    while True:
        header("Main Menu")
        print(f"   {CYAN}1{RESET}. Crack a hash / zip    {GREY}(full wizard){RESET}")
        print(f"   {CYAN}2{RESET}. Identify hash type")
        print(f"   {CYAN}3{RESET}. Speed benchmark")
        print(f"   {CYAN}4{RESET}. Help & algorithm list")
        print(f"   {CYAN}0{RESET}. exit")
        print()
        ch = ask("choose", "1")
        if ch == "0":
            print(f"\n  {GREY}done.{RESET}\n")
            return 0
        if ch == "2":
            ident_mode()
        elif ch == "3":
            bench_mode()
        elif ch == "4":
            help_mode()
        else:
            rc = crack_mode()
            if rc is not None:
                again = ask("crack another hash? (y/n)", "n").lower()
                if again != "y":
                    print(f"\n  {GREY}done.{RESET}\n")
                    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Local hash / zip cracker (CPU-only). No arguments = interactive menu.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=("Mask codes: ?l ?u ?d ?s ?a ?h ?H\n"
                "Contoh: --mask '?l?l?l?d?d'  |  -w rockyou.txt -r\n"
                "Termux: pkg install python && pip install bcrypt passlib"))
    ap.add_argument("-H", "--hash", help="hash target atau file path zip")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("-w", "--wordlist", help="file wordlist")
    src.add_argument("--mask", help="mask brute-force")
    src.add_argument("--digits", type=int, metavar="N", help="digits 0..N digit")
    src.add_argument("--literal", help="test words, comma-separated")
    src.add_argument("--combo", nargs=2, metavar=("W1", "W2"),
                     help="combo dua wordlist")
    ap.add_argument("-r", "--rules", action="store_true", help="mutasi aturan")
    ap.add_argument("-t", "--threads", type=int, default=cpu_count())
    ap.add_argument("-c", "--chunk", type=int, default=None)
    ap.add_argument("-q", "--quiet", action="store_true")
    ap.add_argument("-i", "--identify", action="store_true",
                    help="identify hash type only")
    ap.add_argument("--no-banner", action="store_true")
    ap.add_argument("--user", help="username (postgres_md5, msdcc, oracle10, htdigest)")
    ap.add_argument("--algo", help="force hex algorithm (e.g. md5, ntlm, sha256)")

    args = ap.parse_args()

    if IS_ANDROID:
        _boost_cpu()

    if args.identify:
        if not args.hash:
            ap.error("--identify butuh -H")
        kind, algo, extra = detect_kind(args.hash.strip())
        if kind == "unknown":
            err("unknown format")
            return 2
        kv("type", kind, CYAN)
        kv("algorithm", ", ".join(algo) if isinstance(algo, list) else algo, GREEN)
        if extra:
            kv("extra", extra, GREY)
        return 0

    if not args.hash:
        return interactive()

    target = args.hash.strip()
    kind, algo, extra = detect_kind(target)

    if kind == "zip":
        return crack_zip(target)

    if not (args.wordlist or args.mask or args.digits is not None
            or args.literal or args.combo):
        ap.error("pick a source: -w / --mask / --digits / --literal / --combo")

    if args.algo:
        algo = [a.strip() for a in args.algo.split(",") if a.strip()]
        kind = "hex_multi" if len(algo) > 1 else "hex"
        algo = algo if len(algo) > 1 else algo[0]
        extra = args.user or extra
    elif kind == "hex_multi":
        algo = [a for a in algo if a in SIMPLE_ALGOS] or algo[0]
        if len(algo) == 1:
            algo = algo[0]
            kind = "hex"
        extra = args.user or extra
        print(f"{GREY}  > testing multiple formats: {', '.join(algo) if isinstance(algo, list) else algo}{RESET}")
    elif kind == "hex" and args.user:
        extra = args.user
    if extra is None and isinstance(algo, str) and algo in NEEDS_USER:
        extra = "postgres" if algo == "postgres_md5" else "user"

    if kind == "unknown":
        err("unknown hash format")
        return 2

    if not args.no_banner:
        banner()

    total_hint = None
    if args.wordlist:
        if not os.path.isfile(args.wordlist):
            err(f"wordlist not found: {args.wordlist}")
            return 2
        stream = gen_wordlist(args.wordlist, args.rules)
        if not args.rules:
            try:
                with open(args.wordlist, "rb") as f:
                    total_hint = sum(1 for _ in f)
            except OSError:
                pass
        mode = "wordlist" + (" + mutasi" if args.rules else "")
    elif args.mask:
        total_hint = mask_size(args.mask)
        stream = gen_mask(args.mask)
        mode = f"mask {args.mask}"
    elif args.digits is not None:
        total_hint = sum(10 ** n for n in range(0, args.digits + 1))
        stream = gen_digits(args.digits)
        mode = f"digits 0..{args.digits}"
    elif args.combo:
        p1, p2 = args.combo
        if not (os.path.isfile(p1) and os.path.isfile(p2)):
            err("one of the wordlists was not found")
            return 2
        stream = gen_combo(p1, p2)
        mode = f"combo {os.path.basename(p1)} + {os.path.basename(p2)}"
    else:
        words = [w.strip() for w in args.literal.split(",") if w.strip()]
        total_hint = len(words)
        stream = iter(words)
        mode = "literal"

    header("Cracking", "")
    kv("target", target[:50] + ("..." if len(target) > 50 else ""), GREY)
    kv("algorithm", str(algo), MAGENTA)
    kv("mode", mode, CYAN)
    kv("core", str(args.threads), RESET)
    if extra:
        kv("user", extra, GREY)
    print()
    rule("─", GREY)
    print()

    chunk = args.chunk or (200 if _is_slow_algo(algo) else 5000)
    panel = LivePanel(total_hint, str(algo), detail=str(algo),
                      enabled=not args.quiet)
    try:
        found, done, elapsed, hit_algo = run(
            target, kind, algo, stream, total_hint, args.threads, chunk,
            panel=panel, detail=str(algo), extra=extra)
    except KeyboardInterrupt:
        print("\r\033[K")
        warn("stopped by user")
        return 130
    okk = show_result(found, done, elapsed, target, str(hit_algo))
    return 0 if okk else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)
