import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "scripts/requirements.txt"])
sys.path.insert(0, "scripts")
from datetime import date
from zber_zmluvy_mc import dalsi_dostupny_den
print(dalsi_dostupny_den(date(2026, 7, 17), date(2026, 11, 3)), dalsi_dostupny_den(date(2026, 10, 21), date(2026, 11, 3)))
print("HOTOVO")
