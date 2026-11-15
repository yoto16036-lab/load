#!/usr/bin/env python3

from pathlib import Path
import base64, gzip, hashlib, struct, zlib, zipfile
import xml.etree.ElementTree as ET

# =========================
# NEBULA VIP CONFIG
# =========================

IN = Path("/storage/emulated/0/mlbb/encode")
OUT = Path("/storage/emulated/0/mlbb/decode")

INPUT = IN / "Documents.unity3d"
OUTPUT = IN / "Document.unity3d"
LOSSLESS = IN / "Document_lossless.unity3d"

MAGIC = b"MLBB"

Y = "\033[93m"
G = "\033[92m"
R = "\033[91m"
C = "\033[96m"
W = "\033[97m"
D = "\033[90m"
B = "\033[1m"
X = "\033[0m"


def clear_terminal():
    # Clears visible terminal output/scrollback where supported.
    print("\033[3J\033[2J\033[H", end="", flush=True)


def banner():
    print(Y + B + r"""
███╗   ██╗███████╗██████╗ ██╗   ██╗██╗      █████╗
████╗  ██║██╔════╝██╔══██╗██║   ██║██║     ██╔══██╗
██╔██╗ ██║█████╗  ██████╔╝██║   ██║██║     ███████║
██║╚██╗██║██╔══╝  ██╔══██╗██║   ██║██║     ██╔══██║
██║ ╚████║███████╗██████╔╝╚██████╔╝███████╗██║  ██║
╚═╝  ╚═══╝╚══════╝╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝
                    V I P
              M L B B   R E P A C K E R
""" + X)


def progress(label, current, total, width=30):
    total=max(total,1)
    pct=min(100,int(current*100/total))
    filled=int(width*pct/100)
    bar="█"*filled+"░"*(width-filled)
    print(Y+f"[ {label:<7} ] "+W+f"{bar} {pct:3d}% "+C+f"{current}/{total}"+X, flush=True)


def u32(d, p):
    if p + 4 > len(d):
        raise ValueError("Unexpected EOF")
    return struct.unpack_from("<I", d, p)[0], p + 4


def parse(d):
    if len(d) < 8 or d[:4] != MAGIC:
        raise ValueError("Not an MLBB container")

    count, p = u32(d, 4)
    rs = []

    for i in range(count):
        n, p = u32(d, p)

        if p + n > len(d):
            raise ValueError(f"Resource {i}: invalid name")

        try:
            name = d[p:p+n].decode()
        except:
            raise ValueError(f"Resource {i}: bad name")

        p += n
        size, p = u32(d, p)
        off, p = u32(d, p)

        rs.append({
            "index": i,
            "name": name,
            "size": size,
            "offset": off
        })

    total = sum(r["size"] for r in rs)

    if p + total > len(d):
        raise ValueError("Payload exceeds file")

    return p, rs


def decode(d):
    cur = d
    seen = set()

    for _ in range(8):
        if cur in seen:
            break

        seen.add(cur)
        s = cur.strip()

        # XML
        if (
            s.startswith(b"<?xml")
            or s.startswith(b"<root")
            or (s.startswith(b"<") and b">" in s[:256])
        ):
            return cur

        # Base64
        try:
            b = b"".join(s.split())

            if len(b) >= 8 and len(b) % 4 == 0:
                z = base64.b64decode(b, validate=True)

                if z and z != cur:
                    cur = z
                    continue
        except:
            pass

        # GZIP
        try:
            z = gzip.decompress(cur)

            if z != cur:
                cur = z
                continue
        except:
            pass

        # ZLIB
        try:
            z = zlib.decompress(cur)

            if z != cur:
                cur = z
                continue
        except:
            pass

        break

    return cur


def encode(original, modified):
    s = original.strip()

    try:
        z = base64.b64decode(
            b"".join(s.split()),
            validate=True
        )

        if z == decode(original):
            return base64.b64encode(modified)
    except:
        pass

    try:
        if gzip.decompress(original) == modified:
            return gzip.compress(modified)
    except:
        pass

    try:
        if zlib.decompress(original) == modified:
            return zlib.compress(modified)
    except:
        pass

    return modified


def build(rs, payload):
    o = bytearray(MAGIC)
    o += struct.pack("<I", len(rs))

    for r in rs:
        n = r["name"].encode()
        o += struct.pack("<I", len(n))
        o += n
        o += struct.pack("<I", r["size"])
        o += struct.pack("<I", r["offset"])

    return bytes(o) + payload


# =========================
# DECODE
# =========================

def decode_xml(all_xml=False):
    if not INPUT.exists():
        print(R + "[ERROR] Input not found" + X)
        return

    try:
        data = INPUT.read_bytes()
        base, rs = parse(data)
    except Exception as e:
        print(R + f"[ERROR] {e}" + X)
        return

    OUT.mkdir(parents=True, exist_ok=True)

    wanted = None if all_xml else {
        "BattleSystemConfig.xml",
        "SystemConfig.xml"
    }

    ok = bad = 0
    total_xml = sum(1 for r in rs if r["name"].lower().endswith(".xml") and (wanted is None or r["name"] in wanted))

    print(Y + B + "\n=== UNPACK ===" + X)

    for r in rs:
        name = r["name"]

        if not name.lower().endswith(".xml"):
            continue

        if wanted is not None and name not in wanted:
            continue

        try:
            a = base + r["offset"]
            b = a + r["size"]

            if a < base or b > len(data):
                raise ValueError("Resource out of bounds")

            result = decode(data[a:b])

            p = OUT / Path(name).name
            p.write_bytes(result)

            ok += 1
            progress("UNPACK", ok, total_xml, width=28)
            print(G + "[ UNPACK ] " + X + name)

        except Exception as e:
            print(
                Y + "[SKIP] "
                + X + f"{name}: {e}"
            )
            bad += 1
            continue

    print(
        C + f"\nDecoded: {ok} | Skipped: {bad}"
        + X
    )


# =========================
# ENCODE
# =========================

def valid_xml(p):
    try:
        ET.fromstring(p.read_bytes())
        return True
    except:
        return False


def delete_decoded_xml():
    if not OUT.exists(): return
    deleted=failed=0
    for p in OUT.glob("*.xml"):
        try:
            p.unlink(); deleted+=1
        except Exception as e:
            print(R+f"[CLEANUP] Failed to delete {p.name}: {e}"+X); failed+=1
    print(C+f"[CLEANUP] XML files deleted: {deleted} | Failed: {failed}"+X)


def ask_make_zip():
    while True:
        try: answer=input(Y+"\nGenerate ZIP package? [Y/N]: "+X).strip().lower()
        except (KeyboardInterrupt,EOFError): print(); return
        if answer in ("y","yes"): create_zip_package(); return
        if answer in ("n","no"): print(Y+"[ZIP] Skipped."+X); return
        print(Y+"Please enter Y or N."+X)


def create_zip_package():
    if not OUTPUT.exists():
        print(R+"[ZIP] Repacked Document.unity3d not found."+X); return
    try: zip_name=input(Y+"ZIP name (without .zip): "+X).strip()
    except (KeyboardInterrupt,EOFError): print(); return
    if not zip_name:
        print(Y+"[ZIP] Cancelled: empty name."+X); return
    if not zip_name.lower().endswith(".zip"): zip_name += ".zip"
    zip_path=IN/zip_name
    root="files/dragon2017/assets/Document/android"
    try:
        with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr(root+"/Document.unity3d.res_check_fix/",b"")
            z.writestr(root+"/Document.unity3d.res_check_fix.temp/",b"")
            z.write(OUTPUT,root+"/Document.unity3d")
        print(G+f"[ZIP] Created: {zip_path.name}"+X)
    except Exception as e:
        print(R+f"[ZIP] Failed: {e}"+X)


def encode_xml():
    if not INPUT.exists():
        print(R + "[ERROR] Input not found" + X)
        return

    try:
        original = INPUT.read_bytes()
        base, rs = parse(original)
    except Exception as e:
        print(R + f"[ERROR] {e}" + X)
        return

    if not OUT.exists():
        print(R + "[ERROR] Decode directory not found" + X)
        return

    files = list(OUT.glob("*.xml"))

    if not files:
        print(Y + "[WARNING] No XML files found" + X)
        return

    replacements = {}
    ok = bad = missing = 0

    print(Y + B + "\n=== REPACK ===" + X)
    total_files = len(files)

    for p in files:
        name = p.name

        try:
            if not valid_xml(p):
                raise ValueError("Malformed XML")

            r = next(
                (
                    x for x in rs
                    if x["name"] == name
                    or Path(x["name"]).name == name
                ),
                None
            )

            if r is None:
                print(
                    Y + "[SKIP] "
                    + X + f"{name}: resource not found"
                )
                missing += 1
                continue

            a = base + r["offset"]
            b = a + r["size"]

            if a < base or b > len(original):
                raise ValueError("Original resource out of bounds")

            old = original[a:b]
            new = encode(old, p.read_bytes())

            replacements[r["name"]] = new

            ok += 1
            progress("REPACK", ok, total_files, width=28)
            print(G + "[ REPACK ] " + X + f"{name}: {len(p.read_bytes()):,} -> {len(new):,} bytes")

        except Exception as e:
            print(
                Y + "[SKIP] "
                + X + f"{name}: {e}"
            )
            bad += 1
            continue

    if not replacements:
        print(Y + "\nNothing was encoded." + X)
        return

    parts = []
    new_rs = []
    offset = 0

    try:
        for r in rs:
            name = r["name"]
            a = base + r["offset"]
            b = a + r["size"]

            if a < base or b > len(original):
                raise ValueError(
                    f"Critical resource bounds error: {name}"
                )

            # Modified resource or original byte-for-byte
            data = replacements.get(
                name,
                original[a:b]
            )

            nr = dict(r)
            nr["size"] = len(data)
            nr["offset"] = offset

            new_rs.append(nr)
            parts.append(data)
            offset += len(data)

        rebuilt = build(
            new_rs,
            b"".join(parts)
        )

        OUTPUT.write_bytes(rebuilt)

    except Exception as e:
        print(
            R
            + f"\n[ERROR] Rebuild failed: {e}"
            + X
        )
        return

    print()
    print(G + B + "=== REPACK COMPLETE ===" + X)
    print(W + f"Output : {OUTPUT.name}" + X)
    print(W + f"Original: {len(original):,} bytes" + X)
    print(W + f"Output  : {len(rebuilt):,} bytes" + X)
    print(W + f"Change  : {len(rebuilt)-len(original):+,} bytes" + X)
    print(G + f"Repacked: {ok}" + X)
    print(Y + f"Skipped : {bad}" + X)
    print(Y + f"Missing : {missing}" + X)

    ask_make_zip()
    delete_decoded_xml()

# =========================
# LOSSLESS TEST
# =========================

def lossless():
    if not INPUT.exists():
        print(R + "[ERROR] Input not found" + X)
        return

    try:
        original = INPUT.read_bytes()
        base, rs = parse(original)

        rebuilt = build(
            rs,
            original[base:]
        )

        LOSSLESS.write_bytes(rebuilt)

        if rebuilt == original:
            print(
                G + B
                + "\nSUCCESS: BYTE-IDENTICAL"
                + X
            )
            print(
                W + f"Output: {LOSSLESS}"
                + X
            )
        else:
            pos = next(
                (
                    i for i, (a, b)
                    in enumerate(zip(original, rebuilt))
                    if a != b
                ),
                min(len(original), len(rebuilt))
            )

            print(
                Y
                + f"\nNOT BYTE-IDENTICAL: 0x{pos:X}"
                + X
            )

    except Exception as e:
        print(R + f"[ERROR] {e}" + X)


# =========================
# MENU
# =========================

def main():
    while True:
        banner()

        print(Y + B + "NEBULA VIP MENU" + X)
        print()
        print(Y + "1." + X + " Smart Encode")
        print(Y + "2." + X + " Decode")
        print(Y + "3." + X + " Lossless Test")
        print(Y + "0." + X + " Exit")
        print()

        try:
            c = input(
                Y + B + "Select: " + X
            ).strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return

        if c == "1":
            encode_xml()

        elif c == "2":
            print()
            print("1. Decode All XML")
            print("2. Decode Only 2 XML")
            print("0. Back")

            x = input(
                Y + "Select: " + X
            ).strip()

            if x == "1":
                decode_xml(True)
            elif x == "2":
                decode_xml(False)

        elif c == "3":
            lossless()

        elif c == "0":
            print(
                Y + "\nNEBULA VIP - Exiting..."
                + X
            )
            break

        else:
            print(
                Y + "[WARNING] Invalid choice."
                + X
            )

        try:
            input(
                D + "\nPress ENTER to back to menu..." + X
            )
        except (KeyboardInterrupt, EOFError):
            pass

        clear_terminal()


if __name__ == "__main__":
    main()