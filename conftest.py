"""
conftest.py — konfiguracja pytest dla ADRION 369 push_staging.
Dodaje katalog główny do sys.path, żeby testy mogły importować
pakiety: ecosystem, core itp.
"""
import sys
import pathlib

# Katalog, w którym leży ten conftest.py
ROOT = pathlib.Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
