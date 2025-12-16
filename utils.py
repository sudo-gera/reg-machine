import io
import typing
import argparse

import fa


class ThrowingArgumentParser(argparse.ArgumentParser):

    def exit(self,
             status: int = 0,
             message: str | None = None) -> typing.NoReturn:
        raise argparse.ArgumentError(None, str(message))


debug: typing.IO[str]

try:
    debug = open('/dev/tty', 'w')
except Exception:
    debug = io.StringIO()
