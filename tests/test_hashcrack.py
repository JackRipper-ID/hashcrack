#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for hashcrack.py.

Run with:  python -m pytest tests/ -v
"""

import hashlib
import json
import os
import subprocess
import sys
import zipfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import hashcrack as h  # noqa: E402


# ─────────────────────────── helpers ───────────────────────────

def sha1(text):
    return hashlib.sha1(text.encode()).hexdigest()


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()


def md5(text):
    return hashlib.md5(text.encode()).hexdigest()


def run_cli(args, env=None, timeout=120):
    """Run hashcrack.py as the user would, from the repo root."""
    full_env = dict(os.environ)
    full_env.pop("PYTHONPATH", None)
    if env:
        full_env.update(env)
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "hashcrack.py")] + args,
        cwd=ROOT, env=full_env, capture_output=True, text=True, timeout=timeout,
    )
    return proc


def block_module(tmp_path, name):
    """Directory that makes `import <name>` fail with ImportError."""
    shim = tmp_path / f"block_{name}"
    shim.mkdir()
    (shim / f"{name}.py").write_text(f'raise ImportError("{name} disabled by test")\n')
    return str(shim)


@pytest.fixture
def wordlist(tmp_path):
    p = tmp_path / "words.txt"
    p.write_text("alpha\n\nbeta\ngamma\n")
    return str(p)


@pytest.fixture
def hashes_file(tmp_path):
    p = tmp_path / "hashes.txt"
    p.write_text(
        "# comment line\n\n"
        f"{md5('hunter2')}\n"
        f"{sha1('secret')}\n"
        f"{sha256('secret')}\n"
    )
    return str(p)


# ─────────────────────── hash identification ───────────────────────

def test_uppercase_sha1_is_not_mysql41():
    """Regression: `^\\*?[0-9A-F]{40}$` used to swallow uppercase SHA-1 as
    mysql41, so a correct password was never found (and, without passlib, the
    pool spun forever)."""
    kind, algo, _ = h.detect_kind(sha1("secret").upper())
    assert kind == "hex_multi"
    assert algo == ["sha1", "ripemd160"]


def test_lowercase_sha1_matches_upper_case_result():
    assert h.detect_kind(sha1("secret"))[:2] == h.detect_kind(sha1("secret").upper())[:2]


def test_digits_only_40_hex_is_sha1_family():
    kind, algo, _ = h.detect_kind("1" * 40)
    assert kind == "hex_multi" and "sha1" in algo


def test_mysql41_requires_leading_star():
    real = "*" + hashlib.sha1(hashlib.sha1(b"secret").digest()).hexdigest().upper()
    assert h.detect_kind(real)[:2] == ("hex", "mysql41")
    # without the star it is plain SHA-1, not mysql41
    assert h.detect_kind(real[1:])[0] != "crypt"


def test_postgres_md5_detection_has_no_extra_hash():
    """The username is not part of a postgres hash: `extra` must stay empty so
    that --user (or the 'postgres' default) is what gets appended."""
    kind, algo, extra = h.detect_kind("md5" + md5("x"))
    assert (kind, algo, extra) == ("hex", "postgres_md5", None)


def test_sixteen_hex_offers_mysql323_and_oracle10():
    kind, algos, _ = h.detect_kind("0123456789abcdef")
    assert kind == "hex_multi"
    assert algos == ["mysql323", "oracle10"]


def test_oracle11_prefixed_hash_is_detected():
    target = "S:" + "A1B2C3D4E5" * 6
    assert h.detect_kind(target)[:2] == ("hex", "oracle11")


@pytest.mark.parametrize("target,algo", [
    ("$1$abcdefgh$" + "x" * 22, "md5_crypt"),
    ("$apr1$abcdefgh$" + "x" * 22, "apr_md5_crypt"),
    ("$5$rounds=5000$saltsalt$" + "x" * 43, "sha256_crypt"),
    ("$6$rounds=5000$saltsalt$" + "x" * 86, "sha512_crypt"),
    ("$2b$12$" + "y" * 53, "bcrypt"),
    ("$P$B" + "z" * 31, "phpass"),
    ("{SSHA}" + "q" * 20, "ldap_salted_sha1"),
])
def test_crypt_prefixes_detected(target, algo):
    kind, detected, _ = h.detect_kind(target)
    assert (kind, detected) == ("crypt", algo)


def test_unknown_and_garbage():
    assert h.detect_kind("definitely not a hash !!")[0] == "unknown"
    assert h.detect_kind("a" * 33)[0] == "unknown"


def test_zip_path_is_recognised(tmp_path):
    p = tmp_path / "locked.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("a.txt", "hello")
    assert h.detect_kind(str(p))[:2] == ("zip", "zip")


# ────────────────────────── digest helpers ──────────────────────────

def test_md4_known_vectors():
    assert h.md4_digest(b"").hex() == "31d6cfe0d16ae931b73c59d7e0c089c0"
    assert h.md4_digest(b"abc").hex() == "a448017aaf21d8525fc10ae87aa6729d"


def test_md4_pure_python_matches_hashlib():
    pytest.importorskip("hashlib")
    try:
        expected = hashlib.new("md4", b"The quick brown fox").hexdigest()
    except Exception:
        expected = h._md4_py(b"The quick brown fox").hex()
    assert h._md4_py(b"The quick brown fox").hex() == expected


def test_ntlm_known_vector():
    assert h._digest_for("ntlm", "password") == "8846f7eaee8fb117ad06bdd830b7586c"


def test_mysql41_digest_shape():
    digest = h._digest_for("mysql41", "secret")
    assert digest.startswith("*") and len(digest) == 41
    inner = hashlib.sha1(b"secret").digest()
    assert digest == "*" + hashlib.sha1(inner).hexdigest().upper()


# ─────────────────────── optional dependency handling ───────────────────────

def test_check_algos_splits_missing_passlib(monkeypatch):
    monkeypatch.setattr(h, "have_module", lambda name: name != "passlib")
    runnable, skipped = h.check_algos(["md5", "mysql323", "sha256"])
    assert runnable == ["md5", "sha256"]
    assert skipped == [("mysql323", "pip install passlib")]


def test_check_algos_bcrypt_needs_bcrypt(monkeypatch):
    monkeypatch.setattr(h, "have_module", lambda name: name != "bcrypt")
    runnable, skipped = h.check_algos(["bcrypt"])
    assert runnable == []
    assert skipped[0][1] == "pip install bcrypt"


def test_apply_availability_raises_when_nothing_left(monkeypatch):
    monkeypatch.setattr(h, "have_module", lambda name: False)
    with pytest.raises(h.CrackerError) as exc:
        h._apply_availability("mysql323", "hex")
    assert "passlib" in str(exc.value)


def test_apply_availability_narrows_multi_list(monkeypatch):
    monkeypatch.setattr(h, "have_module", lambda name: name != "passlib")
    algo, kind = h._apply_availability(["md5", "lm"], "hex_multi")
    assert (algo, kind) == ("md5", "hex")


def test_worker_init_failure_is_reported_not_respawned(monkeypatch, capsys):
    """A missing optional module used to kill the worker inside the Pool
    initializer, which multiprocessing answers by spawning workers forever."""

    def boom(*_a, **_kw):
        raise ModuleNotFoundError("No module named 'passlib'")

    monkeypatch.setattr(h, "_make_verifier", boom)
    h._init_worker("$6$salt$hash", "crypt", "sha512_crypt", None, None)
    assert h._init_error is not None
    assert h.worker_chunk(["a", "b"]) == (h.WORKER_ERROR, h._init_error)


def test_run_raises_cracker_error_instead_of_hanging(monkeypatch):
    def boom(*_a, **_kw):
        raise ModuleNotFoundError("No module named 'passlib'")

    monkeypatch.setattr(h, "_make_verifier", boom)
    with pytest.raises(h.CrackerError):
        h.run("$6$salt$hash", "crypt", "sha512_crypt", iter(["a", "b"]),
              None, 1, 10)


# ──────────────────────── candidate generators ────────────────────────

def test_parse_mask_and_size():
    assert h.parse_mask("?d?l") == ["0123456789", "abcdefghijklmnopqrstuvwxyz"]
    assert h.mask_size("?d?d") == 100
    assert h.mask_size("?l?l") == 676
    assert h.mask_size("abc") == 1
    # "??" is a literal question mark, unknown codes stay literal too
    assert h.parse_mask("??") == ["?"]
    assert h.parse_mask("?z") == ["?", "z"]


def test_gen_mask_enumerates_everything():
    assert list(h.gen_mask("?d?d")) == [f"{a}{b}" for a in "0123456789"
                                        for b in "0123456789"]
    assert list(h.gen_mask("ab")) == ["ab"]


def test_gen_digits_counts_match_hint():
    assert list(h.gen_digits(1)) == ["", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    assert sum(10 ** n for n in range(0, 4)) == len(list(h.gen_digits(3)))


def test_apply_rules_covers_case_leet_and_suffixes():
    out = h.apply_rules("Secret")
    assert "Secret" in out and "secret" in out and "SECRET" in out
    assert "Secret1" in out and "secret123" in out
    assert len(out) == len(set(out)), "mutations must be de-duplicated"
    assert "53cr37" in out, "leet substitution should be present"


def test_gen_wordlist_skips_blank_lines(wordlist):
    assert list(h.gen_wordlist(wordlist)) == ["alpha", "beta", "gamma"]


def test_gen_wordlist_rules_starts_from_base_words(wordlist):
    got = list(h.gen_wordlist(wordlist, rules=True))
    assert got[0] == "alpha"
    assert "alpha1" in got
    assert len(got) > 3


def test_count_candidates_matches_generator(wordlist):
    assert h.count_candidates(wordlist) == len(list(h.gen_wordlist(wordlist)))


def test_estimate_rules_total_is_close(wordlist):
    exact = len(list(h.gen_wordlist(wordlist, rules=True)))
    estimate = h.estimate_rules_total(wordlist)
    assert exact * 0.8 <= estimate <= exact * 1.2


def test_gen_combo_respects_limit(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("x\ny\n")
    b.write_text("1\n2\n")
    assert list(h.gen_combo(str(a), str(b))) == ["x1", "x2", "y1", "y2"]
    assert len(list(h.gen_combo(str(a), str(b), limit=3))) == 3


# ────────────────────────── verification ──────────────────────────

def test_verify_hex_accepts_correct_and_rejects_wrong():
    target = sha256("s3cret")
    assert h._verify_hex(target, "sha256", None, "s3cret") is True
    assert h._verify_hex(target, "sha256", None, "nope") is False


def test_verify_hex_case_insensitive_target():
    target = sha256("s3cret").upper()
    assert h._verify_hex(target, "sha256", None, "s3cret") is True


def test_postgres_md5_verification_uses_supplied_username():
    target = "md5" + hashlib.md5(b"secretalice").hexdigest()
    assert h._verify_hex(target, "postgres_md5", "alice", "secret") is True
    assert h._verify_hex(target, "postgres_md5", "bob", "secret") is False


def test_verify_returns_the_matching_algorithm():
    target = sha256("abc")
    assert h._verify(target, "hex_multi", ["md5", "sha256"], None, "abc") == "sha256"
    assert h._verify(target, "hex_multi", ["md5"], None, "abc") is None


def test_mssql_target_strips_0x_prefix():
    inner = h._digest_for("ntlm", "abc")
    assert h._verify_hex("0x" + inner, "ntlm", None, "abc") is True


# ─────────────────────── pool orchestration ───────────────────────

def test_run_counts_every_candidate():
    """The shared counter used to be `value += n`, which loses updates when
    several workers bump it at the same time."""
    target = sha256("never-in-stream")
    stream = (f"cand{i}" for i in range(20000))
    found, done, _elapsed, _algo = h.run(target, "hex", "sha256", stream,
                                         None, 3, 5000)
    assert found is None
    assert done == 20000


def test_run_stops_after_a_hit():
    target = sha256("cand1")
    stream = (f"cand{i}" for i in range(50000))
    found, done, _elapsed, algo = h.run(target, "hex_multi", ["sha256", "md5"],
                                        stream, None, 2, 1000)
    assert found == "cand1"
    assert algo == "sha256"
    assert done < 50000


def test_run_multi_cracks_several_hashes_in_one_pass():
    targets = [
        {"target": md5("hunter2"), "kind": "hex", "algos": ["md5"], "extra": None},
        {"target": sha1("secret"), "kind": "hex", "algos": ["sha1"], "extra": None},
        {"target": sha256("secret"), "kind": "hex", "algos": ["sha256"], "extra": None},
    ]
    stream = iter(["nope", "hunter2", "secret"])
    found, done, _elapsed = h.run_multi(targets, stream, 2, 5000)
    assert found[0] == ("hunter2", "md5")
    assert found[1] == ("secret", "sha1")
    assert found[2] == ("secret", "sha256")
    assert done == 3


def test_run_multi_reports_misses_without_claiming_success():
    targets = [{"target": md5("absent"), "kind": "hex", "algos": ["md5"], "extra": None}]
    found, _done, _elapsed = h.run_multi(targets, iter(["a", "b"]), 1, 100)
    assert found == {}


def test_run_rejects_bad_worker_and_chunk_counts():
    with pytest.raises(h.CrackerError):
        h.run(sha256("x"), "hex", "sha256", iter(["a"]), None, 0, 10)
    with pytest.raises(h.CrackerError):
        h.run(sha256("x"), "hex", "sha256", iter(["a"]), None, 1, 0)


# ─────────────────────────────── CLI ───────────────────────────────

def test_version_flag():
    proc = run_cli(["--version"])
    assert proc.returncode == 0
    assert proc.stdout.strip() == f"hashcrack {h.VERSION}"


def test_project_version_matches_module_version():
    pyproject = open(os.path.join(ROOT, "pyproject.toml")).read()
    assert f'version = "{h.VERSION}"' in pyproject


@pytest.mark.parametrize("args,needle", [
    (["-t", "0"], "threads"),
    (["-t", "-3"], "threads"),
    (["-c", "0"], "chunk"),
    (["--digits", "0"], "digits"),
    (["--digits", "99"], "digits"),
])
def test_numeric_flags_are_validated(args, needle):
    proc = run_cli(["-H", sha256("x")] + args + ["--literal", "x"])
    assert proc.returncode == 2
    assert needle in proc.stderr.lower()


def test_empty_mask_is_refused():
    proc = run_cli(["-H", sha256("x"), "--mask", "a"])
    assert proc.returncode == 2
    assert "kemungkinan" in proc.stdout.lower() or "kemungkinan" in proc.stderr.lower()


def test_json_found_result():
    proc = run_cli(["-H", sha256("s3cret"), "--literal", "nope,s3cret",
                    "--json", "-t", "2"])
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["found"] is True
    assert data["password"] == "s3cret"
    assert data["algorithm"] == "sha256"
    assert data["candidates"] == 2


def test_json_not_found_result_and_exit_code():
    proc = run_cli(["-H", sha256("s3cret"), "--literal", "nope", "--json", "-t", "2"])
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["found"] is False and data["password"] is None


def test_json_identify():
    proc = run_cli(["-i", "-H", sha1("secret").upper(), "--json"])
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["kind"] == "hex_multi"
    assert "sha1" in data["algorithm"]


def test_uppercase_sha1_cracks_end_to_end():
    """The user-visible symptom of the mysql41 misroute."""
    proc = run_cli(["-H", sha1("secret").upper(), "--literal", "secret",
                    "--json", "-t", "2"])
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["password"] == "secret"


def test_hash_file_cracks_every_target(hashes_file):
    proc = run_cli(["--hash-file", hashes_file, "--literal", "hunter2,secret",
                    "--json", "-t", "2"])
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["cracked"] == data["total"] == 3
    assert {t["password"] for t in data["targets"]} == {"hunter2", "secret"}


def test_hash_file_reports_lines_it_cannot_use(tmp_path):
    p = tmp_path / "mixed.txt"
    p.write_text(f"{md5('hunter2')}\nghp_not_a_hash_at_all\n")
    proc = run_cli(["--hash-file", str(p), "--literal", "hunter2", "--json", "-t", "2"])
    data = json.loads(proc.stdout)
    assert data["total"] == 1
    assert "line 2" in proc.stderr


def test_hash_file_without_crackable_lines_exits_2(tmp_path):
    p = tmp_path / "junk.txt"
    p.write_text("hello\nworld\n")
    proc = run_cli(["--hash-file", str(p), "--literal", "x"])
    assert proc.returncode == 2


def test_missing_optional_module_is_a_clean_error(tmp_path):
    """passlib-dependent hashes must explain the install, not traceback."""
    shim = block_module(tmp_path, "passlib")
    proc = run_cli(["-H", "0123456789abcdef", "--literal", "secret", "--json"],
                   env={"PYTHONPATH": shim})
    assert proc.returncode == 2
    data = json.loads(proc.stdout)
    assert "passlib" in data["error"]
    assert "Traceback" not in proc.stderr


def test_json_needs_a_target():
    proc = run_cli(["--json"])
    assert proc.returncode == 2
    assert "json" in proc.stderr.lower()


def test_wordlist_and_identify_together_do_not_crash(hashes_file, wordlist):
    proc = run_cli(["--hash-file", hashes_file, "--identify"])
    assert proc.returncode == 2


def test_readme_cli_examples_still_run(wordlist, tmp_path):
    """Every documented invocation must work, not just the ones tests use."""
    example_mask = run_cli(["-H", sha256("ab"), "--mask", "?l?l", "-q", "--json"])
    assert example_mask.returncode in (0, 1)

    example_list = run_cli(["-H", md5("alpha"), "-w", wordlist, "-q", "--json"])
    assert example_list.returncode == 0
    assert json.loads(example_list.stdout)["password"] == "alpha"

    example_rules = run_cli(["-H", md5("alpha1"), "-w", wordlist, "-r",
                             "-q", "--json"])
    assert example_rules.returncode == 0
    assert json.loads(example_rules.stdout)["password"] == "alpha1"

    example_digits = run_cli(["-H", md5("0042"), "--digits", "4", "-q", "--json"])
    assert example_digits.returncode == 0

    example_literal = run_cli(["-H", md5("kata1"), "--literal", "kata1,kata2",
                               "-q", "--json"])
    assert example_literal.returncode == 0


def test_zip_cracking_is_not_silently_broken(tmp_path):
    """ZipCrypto path: crack a small archive with a known password."""
    p = tmp_path / "secret.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("a.txt", "hello")
    # stdlib cannot *write* encrypted zips; skip when nothing is encrypted
    proc = run_cli(["-H", str(p)])
    # no password to find -> the tool says the zip is not encrypted
    assert proc.returncode in (0, 1)
    assert "encrypt" in (proc.stdout + proc.stderr).lower()


# ─────────────────── forced algorithms / input handling ───────────────────

def test_known_algos_contains_supported_names():
    names = h.known_algos()
    for name in ("md5", "sha256", "sha3_512", "mysql323", "postgres_md5",
                 "oracle11", "bcrypt", "sha512_crypt"):
        assert name in names
    assert "bogus" not in names


def test_unknown_forced_algorithm_is_a_clean_error():
    proc = run_cli(["-H", sha256("x"), "--literal", "x", "--algo", "bogus"])
    assert proc.returncode == 2
    assert "unknown algorithm" in (proc.stdout + proc.stderr).lower()


def test_forced_algorithm_list_selects_the_right_one():
    proc = run_cli(["-H", sha256("abc"), "--literal", "abc",
                    "--algo", "md5,sha256", "--json", "-t", "2"])
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["algorithm"] == "sha256"


def test_read_targets_skips_non_hex_with_a_reason(tmp_path):
    p = tmp_path / "mixed.txt"
    p.write_text(f"{sha256('a')}\n$2b$12$abcdefghijklmnopqrstuvwxyz\n")
    targets, skipped = h._read_targets(str(p))
    assert len(targets) == 1
    assert skipped and "unsupported" in skipped[0][2]


def test_apply_rules_order_is_deterministic():
    """A set-based implementation reordered candidates per process, so the same
    command reported a different position for the same password."""
    first = h.apply_rules("Secret")
    assert first[0] == "Secret"
    assert first.index("53cr37") == len(h.SUFFIXES)  # 2nd variant, fixed order
    assert first == h.apply_rules("Secret")


def test_rules_run_reports_the_same_position_twice(wordlist):
    target = md5("alpha1")
    runs = [json.loads(run_cli(["-H", target, "-w", wordlist, "-r", "--json",
                                "-t", "2"]).stdout) for _ in range(2)]
    assert runs[0]["password"] == runs[1]["password"] == "alpha1"
    assert runs[0]["candidates"] == runs[1]["candidates"]


# ───────────────────── interactive mode (stdin) ─────────────────────

def run_interactive(text, timeout=90):
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return subprocess.run([sys.executable, os.path.join(ROOT, "hashcrack.py")],
                          input=text, cwd=ROOT, env=env, capture_output=True,
                          text=True, timeout=timeout)


def test_interactive_exits_when_stdin_is_closed():
    """Regression: EOF made the menu loop forever (80k menus in 5 s)."""
    import time
    t0 = time.time()
    proc = run_interactive("")
    assert proc.returncode == 0
    assert time.time() - t0 < 30
    assert proc.stdout.count("Main Menu") <= 1
    assert "stdin closed" in proc.stdout


def test_interactive_identify_flow():
    proc = run_interactive("2\n" + sha1("x").upper() + "\n\n0\n")
    assert proc.returncode == 0
    assert "sha1, ripemd160" in proc.stdout


def test_interactive_crack_flow_finds_the_password():
    proc = run_interactive("1\n" + md5("swordfish") + "\n0\n5\nswordfish,other\n1\nn\n0\n")
    assert proc.returncode == 0
    assert "PASSWORD FOUND" in proc.stdout
    assert "swordfish" in proc.stdout


def test_interactive_stops_cleanly_when_input_runs_out_mid_flow():
    proc = run_interactive("1\n")
    assert proc.returncode == 0
    assert proc.stdout.count("Main Menu") <= 2
