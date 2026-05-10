from besoccer_scraper.shared.hashing import sha256_hex


def test_sha256_hex_with_str():
    assert sha256_hex("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_sha256_hex_with_bytes():
    assert sha256_hex(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
