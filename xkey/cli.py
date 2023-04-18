"""xKey - Novation FLKey and LaunchKey SysEx utilities."""

import argparse
import logging
import pathlib
import sys

from xkey.sysex.novation import codec, message


def encode(filename: str) -> int:
    """Encodes Encodes a binary file to Novation compatible SysEx."""
    buffer = bytearray()
    output = bytearray()
    logger = logging.getLogger(__name__)


def decode(filename: str) -> int:
    """Decodes Novation compatible SysEx to a binary file."""
    logger = logging.getLogger(__name__)

    buffer = bytearray()
    output = bytearray()
    in_path = pathlib.Path(filename).resolve()
    out_path = f"{in_path}.bin"

    # Supported message types.
    messages = [message.Start, message.End, message.Metadata, message.Data]

    try:
        logger.info(f"Reading SysEx from '{in_path}'")

        with open(in_path, "rb") as fin:
            while True:
                # All messages have a 6-byte header.
                offset = fin.tell()
                buffer = bytearray(fin.read(6))
                if len(buffer) < 1:
                    break

                # Determine the message type.
                for candidate in messages:
                    handler = None

                    if buffer[4:6] == candidate.identifier:
                        handler = candidate()

                        # Read in the whole message, including the trailing SysEx EOX.
                        buffer.extend(bytearray(fin.read(handler.size())))
                        buffer.extend(bytearray(fin.read(1)))
                        handler.from_bytes(buffer)
                        logger.debug(f"Found '{handler.name}' {offset}-bytes into file")
                        break

                # No handler? No support for this message.
                if not handler:
                    raise ValueError("Unsupported SysEx message type encountered")

                # Handle the chunk appropriately.
                if type(handler) == message.Data:
                    chunk = codec.decoder(handler.chunk)
                    output.extend(chunk)

                # The contents of the last message is the first chunk.
                if type(handler) == message.End:
                    chunk = codec.decoder(handler.chunk)
                    output = chunk + output

    except (OSError, ValueError) as err:
        logger.fatal(f"Unable to read in SysEx from file: {err}")
        return 1

    try:
        logger.info(f"Writing decoded SysEx to '{out_path}'")

        with open(out_path, "wb") as fout:
            fout.write(output)
    except OSError as err:
        logger.fatal(f"Unable to write binary to file: {err}")
        return 1

    return 0


if __name__ == "__main__":
    """xKey - Novation FLKey and LaunchKey SysEx utilities."""
    parser = argparse.ArgumentParser(description=__doc__)
    method = parser.add_mutually_exclusive_group(required=True)
    method.add_argument("--encode", action="store_true", help="Encode binary to SysEx")
    method.add_argument("--decode", action="store_true", help="Decode SysEx to binary")
    parser.add_argument("filename", help="The path to the file to process")
    parser.add_argument(
        "--debug",
        help="Enables debug level logging",
        action="store_true",
        default=False,
    )
    arguments = parser.parse_args()

    # Configure logging.
    logging.basicConfig(
        level=logging.DEBUG if arguments.debug else logging.INFO,
        format="%(asctime)s - [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("xKey")

    # Dispatch.
    if arguments.encode:
        sys.exit(encode(arguments.filename))

    if arguments.decode:
        sys.exit(decode(arguments.filename))
