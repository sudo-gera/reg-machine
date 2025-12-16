import io
import typing

debug: typing.IO[str]

try:
    debug = open('/dev/tty', 'w')
except Exception:
    debug = io.StringIO()
