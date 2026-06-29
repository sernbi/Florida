from pathlib import Path
import re
import subprocess
import sys


def run(*args):
    subprocess.run(args, check=True)


def replace_file(path, old, new, required=True):
    p = Path(path)
    text = p.read_text()
    if old not in text:
        if required:
            raise SystemExit(f"missing text in {path}: {old!r}")
        return False
    p.write_text(text.replace(old, new))
    return True


def apply_rpc_patch():
    path = Path("lib/base/rpc.vala")
    text = path.read_text()

    if "getRpcStr" not in text:
        pattern = re.compile(
            r"(\n[ \t]*public RpcClient \(Peer peer\) \{\n"
            r"[ \t]*Object \(peer: peer\);\n"
            r"[ \t]*\}\n)"
        )
        method = (
            r"\1\n"
            "\t\tpublic string getRpcStr(bool quote){\n"
            "\t\t\tstring result = (string) GLib.Base64.decode((string) GLib.Base64.decode(\"Wm5KcFpHRTZjbkJq\"));\n"
            "\t\t\tif(quote){\n"
            "\t\t\t\treturn \"\\\"\" + result + \"\\\"\";\n"
            "\t\t\t}else{\n"
            "\t\t\t\treturn result;\n"
            "\t\t\t}\n"
            "\t\t}\n"
        )
        text, count = pattern.subn(method, text, count=1)
        if count != 1:
            raise SystemExit("Cannot insert getRpcStr into lib/base/rpc.vala")

    replacements = {
        '.add_string_value ("frida:rpc")': '.add_string_value (getRpcStr(false))',
        'json.index_of ("\\"frida:rpc\\"")': 'json.index_of (getRpcStr(true))',
        'type != "frida:rpc"': 'type != getRpcStr(false)',
    }
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)

    required = ["getRpcStr", "getRpcStr(false)", "getRpcStr(true)"]
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit(f"rpc patch incomplete, missing: {missing}")

    path.write_text(text)
    run("git", "add", "lib/base/rpc.vala")
    run("git", "commit", "-m", "Florida: string_frida_rpc")


def write_anti_anti_frida():
    Path("src/anti-anti-frida.py").write_text(
        """import lief
import sys
import random
import os

if __name__ == "__main__":
    input_file = sys.argv[1]
    print(f"[*] Patch frida-agent: {input_file}")
    random_name = "".join(random.sample("ABCDEFGHIJKLMNO", 5))
    print(f"[*] Patch `frida` to `{random_name}``")

    binary = lief.parse(input_file)

    if not binary:
        exit()

    for symbol in binary.symbols:
        if symbol.name == "frida_agent_main":
            symbol.name = "main"

        if "frida" in symbol.name:
            symbol.name = symbol.name.replace("frida", random_name)

        if "FRIDA" in symbol.name:
            symbol.name = symbol.name.replace("FRIDA", random_name)

    binary.write(input_file)
"""
    )


def apply_symbol_patch():
    for folder in ("src", "tests"):
        root = Path(folder)
        if not root.exists():
            continue
        for path in root.rglob("*.vala"):
            text = path.read_text()
            new_text = text.replace('"frida_agent_main"', '"main"')
            if new_text != text:
                path.write_text(new_text)

    write_anti_anti_frida()
    run("git", "add", ".")
    run("git", "commit", "-m", "Florida: symbol_frida_agent_main")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_florida_17_15_3.py rpc|symbol")

    if sys.argv[1] == "rpc":
        apply_rpc_patch()
    elif sys.argv[1] == "symbol":
        apply_symbol_patch()
    else:
        raise SystemExit(f"unknown patch name: {sys.argv[1]}")


if __name__ == "__main__":
    main()
