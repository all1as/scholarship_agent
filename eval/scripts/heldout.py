"""Отложенная часть eval: шифрование, расшифровка и проверка хэша (design doc, раздел 7.5).

  python eval/scripts/heldout.py encrypt <plain.jsonl>   — шифрует в eval/heldout/heldout.enc, пишет SHA256 открытого файла
  python eval/scripts/heldout.py verify  <plain.jsonl>   — сверяет открытый файл с SHA256
  python eval/scripts/heldout.py decrypt <out.jsonl>     — расшифровывает (только на КТ4)

Ключ — переменная HELDOUT_KEY в .env (не в git). Новый ключ: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import hashlib
import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "eval" / "heldout"
ENC, SHA = DIR / "heldout.enc", DIR / "SHA256"

load_dotenv(ROOT / ".env")


def main() -> None:
    cmd, path = sys.argv[1], Path(sys.argv[2])
    if cmd == "verify":
        ok = hashlib.sha256(path.read_bytes()).hexdigest() == SHA.read_text().split()[0]
        print("совпадает" if ok else "НЕ совпадает")
        sys.exit(0 if ok else 1)
    fernet = Fernet(os.environ["HELDOUT_KEY"].encode())
    if cmd == "encrypt":
        data = path.read_bytes()
        DIR.mkdir(parents=True, exist_ok=True)
        ENC.write_bytes(fernet.encrypt(data))
        SHA.write_text(f"{hashlib.sha256(data).hexdigest()}  {path.name}\n")
        print(f"зашифровано: {ENC}, sha256 записан в {SHA}")
    elif cmd == "decrypt":
        path.write_bytes(fernet.decrypt(ENC.read_bytes()))
        print(f"расшифровано в {path}")


if __name__ == "__main__":
    main()
