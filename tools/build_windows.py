"""一鍵建置 Windows 安裝檔：
1. 確認內附的 MariaDB（packaging/mariadb）
2. 產生資料庫腳本、圖示、語音說明（已存在且沒變則略過）
3. flet pack（PyInstaller）打包到 dist/ZMSMRP2
4. Inno Setup 產生 dist-installer/ZMSMRP2-Setup-<版本>.exe

用法：.venv\\Scripts\\python tools\\build_windows.py
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from mrp import APP_ID, APP_NAME, APP_VERSION, AUTHOR  # noqa: E402

ISCC = [os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe", r"C:\Program Files\Inno Setup 6\ISCC.exe"]
PY = os.path.join(HERE, ".venv", "Scripts", "python.exe")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")


def prepare():
    if not os.path.isfile(os.path.join(HERE, "packaging", "mariadb", "bin", "mariadbd.exe")):
        raise SystemExit("缺少 packaging/mariadb（請複製 MariaDB 10.11 的 bin 與 share 最小檔案）")
    subprocess.run([PY, "db/schema_spec.py"], cwd=HERE, check=True, env=ENV)
    shutil.copy2(os.path.join(HERE, "db", "sample_data.sql"), os.path.join(HERE, "mrp", "demo_data.sql"))
    if not os.path.isfile(os.path.join(HERE, "assets", "icon.png")):
        subprocess.run([PY, "tools/make_icon.py"], cwd=HERE, check=True, env=ENV)
    subprocess.run([PY, "tools/make_voice.py"], cwd=HERE, check=False, env=ENV)


def pack():
    flet = os.path.join(HERE, ".venv", "Scripts", "flet.exe")
    shutil.rmtree(os.path.join(HERE, "dist"), ignore_errors=True)
    cmd = [flet, "pack", "main.py", "-D", "-y", "-n", APP_ID, "-i", "packaging/icon.ico", "--distpath", "dist",
           "--add-data", "assets:assets", "--add-data", "mrp/schema.sql:mrp", "--add-data", "mrp/demo_data.sql:mrp",
           "--hidden-import", "edge_tts", "--hidden-import", "pymysql",
           "--product-name", APP_NAME, "--file-description", APP_NAME, "--product-version", APP_VERSION,
           "--file-version", APP_VERSION + ".0", "--company-name", AUTHOR, "--copyright", "© 2026 " + AUTHOR]
    subprocess.run(cmd, cwd=HERE, check=True, env=ENV)


def installer():
    iscc = next((p for p in ISCC if os.path.isfile(p)), None)
    if not iscc:
        raise SystemExit("找不到 Inno Setup 6（ISCC.exe）")
    subprocess.run([iscc, "/DAppVer=" + APP_VERSION, os.path.join(HERE, "packaging", "installer.iss")], check=True)
    out = os.path.join(HERE, "dist-installer", "%s-Setup-%s.exe" % (APP_ID, APP_VERSION))
    sha = hashlib.sha256(open(out, "rb").read()).hexdigest()
    print("完成：%s（%.1f MB）\nSHA256 %s" % (out, os.path.getsize(out) / 1e6, sha))


if __name__ == "__main__":
    prepare()
    pack()
    installer()
