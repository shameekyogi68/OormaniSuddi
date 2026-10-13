"""The test package — and the gate every test run passes through.

`unittest discover` imports this package before any test module, so an
unusable interpreter fails HERE — once, with the fix — instead of surfacing
as thirty confusing import errors inside individual suites. The machine this
repo lives on has two Pythons: the homebrew one with the rendering
dependencies (/opt/homebrew/bin/python3.14) and a bare system python3
without numpy or Pillow. The guard exists for the second one.
"""
import sys

if sys.version_info < (3, 11):
    raise RuntimeError(
        f'The tests need Python 3.11 or newer; this interpreter is '
        f'{sys.version.split()[0]} ({sys.executable}).\n'
        f'Run them with the homebrew interpreter, which has the '
        f'dependencies:\n'
        f'    /opt/homebrew/bin/python3.14 -m unittest discover tests'
    )

for _dep in ('numpy', 'PIL'):
    try:
        __import__(_dep)
    except ImportError as _e:
        raise RuntimeError(
            f'The tests need {_dep}, which this interpreter cannot import '
            f'({_e}).\n'
            f'Run them with the homebrew interpreter, which has the '
            f'dependencies:\n'
            f'    /opt/homebrew/bin/python3.14 -m unittest discover tests'
        ) from _e

del _dep
