"""`python3 -m templates` — inspect or dump the registry."""
import sys
from . import TEMPLATES, dump_json

if '--dump' in sys.argv:
    print('wrote', dump_json())
else:
    print(f'{len(TEMPLATES)} templates\n')
    for k, s in TEMPLATES.items():
        print(f'  {k:16s} {s.size[0]}×{s.size[1]:<5} takes={s.takes:8s} {s.summary}')
    print('\n--dump  write templates/registry.json')
