"""xKey - Novation SysEx utilities."""

import argparse
import logging
import pathlib
import sys

from xkey.sysex.novation import codec, constant, message


def encode(filename: str, model: str, build: int) -> int:
    """Encodes Encodes a binary file to Novation compatible SysEx."""
    logger = logging.getLogger(__name__)

    buffer = bytearray()
    output = bytearray()
    in_path = pathlib.Path(filename).resolve()

    logger.info(f"Generating update for {model}, build v{build}")

    # We have to do a dance to get the build number into a zero padded integer here.
    build_number = bytearray(6)

    for index, byte in enumerate(bytearray([int(digit) for digit in str(build)])[::-1]):
        build_number[5 - index] = byte

    # Construct the start message.
    start = message.Start()
    start.manufacturer = constant.MANUFACTURER_IDS["Novation"]
    start.model = constant.MODEL_IDS[model]
    start.build = build_number

    # Construct the metadata message.
    metadata = message.Metadata()
    metadata.unknown0 = bytearray(1)
    metadata.build = bytearray(str(build).rjust(6, "0"), "utf-8")
    metadata.chunk = bytearray(16)

    try:
        logger.info(f"Reading binary from {in_path}")

        with open(in_path, "rb") as fin:
            pass
    except (OSError, ValueError) as err:
        logger.fatal(f"Unable to read binary from file {in_path}: {err}")
        return 1


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
        logger.info(f"Reading SysEx from {in_path}")

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

                # Handle start messages appropriately.
                if type(handler) == message.Start:
                    model = "UNKNOWN"
                    manufacturer = "UNKNOWN"

                    for name, value in constant.MANUFACTURER_IDS.items():
                        if handler.manufacturer == value:
                            manufacturer = name
                            break

                    for name, value in constant.MODEL_IDS.items():
                        if handler.model == value:
                            model = name

                    logger.info(f"SysEx file appears to be for {manufacturer} {model}")

                # Handle metadata appropriately.
                if type(handler) == message.Metadata:
                    build = str(handler.build, "utf-8")
                    logger.info(f"SysEx file appears to contain build {build}")

                # Handle the chunk appropriately.
                if type(handler) == message.Data:
                    chunk = codec.decoder(handler.chunk)
                    output.extend(chunk)

                # The contents of the last message is the first chunk.
                if type(handler) == message.End:
                    chunk = codec.decoder(handler.chunk)
                    output = chunk + output

    except (OSError, ValueError) as err:
        logger.fatal(f"Unable to read SysEx from file {in_path}: {err}")
        return 1

    try:
        logger.info(f"Writing decoded SysEx to {out_path}")

        with open(out_path, "wb") as fout:
            fout.write(output)
    except OSError as err:
        logger.fatal(f"Unable to write binary to file {out_path}: {err}")
        return 1

    return 0


if __name__ == "__main__":
    """xKey - Novation SysEx utilities."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--debug", help="Enables debug logging", action="store_true", default=False
    )
    subparser = parser.add_subparsers(dest="subparser")

    # Encoding sub-command specific arguments.
    encoder = subparser.add_parser("encode", help="Encode binary to SysEx.")
    encoder.add_argument("filename", help="The path to the file to process")
    encoder.add_argument(
        "--model",
        help="The model to generate the SysEx update for.",
        choices=constant.MODEL_IDS.keys(),
        required=True,
    )
    encoder.add_argument(
        "--build",
        type=int,
        help="The build number to embed in the update.",
        required=True,
    )

    # Decoding sub-command specific arguments.
    decoder = subparser.add_parser("decode", help="Decode SysEx to binary.")
    decoder.add_argument("filename", help="The path to the file to process")

    # Parse.
    arguments = parser.parse_args()

    # Configure logging.
    logging.basicConfig(
        level=logging.DEBUG if arguments.debug else logging.INFO,
        format="%(asctime)s - [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("xKey")

    # Dispatch.
    if arguments.subparser == "encode":
        sys.exit(encode(arguments.filename, arguments.model, arguments.build))

    if arguments.subparser == "decode":
        sys.exit(decode(arguments.filename))

    parser.print_help()
    sys.exit(1)
