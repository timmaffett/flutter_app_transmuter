import os
import sys

# The engine lives inside the package's lib/ so it ships with the pub archive.
ENGINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      'lib', 'python', 'brandtool')
sys.path.insert(0, ENGINE)
# The tests dir itself (for `from fakes import ...`).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
