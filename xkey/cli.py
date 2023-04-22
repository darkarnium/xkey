"""xKey - Novation SysEx utilities.

Provides encoding and decoding of Novation SysEx format firmware updates. This utility
is intended to enable analysis and modification of firmware for supported Novation
devices.

Currently supported devices include:

    * Novation Launchkey MK3
    * Novation FLKey

"""

import argparse
import logging
import pathlib
import sys

from xkey.sysex.novation import codec, constant, message


# mypy: disable-error-code="attr-defined"
def encode(filename: str, model: str, build: int) -> int:
    """Encodes Encodes a binary file to Novation compatible SysEx.

    :param filename: The name and path to the file to encode.
    :param model: A supported Novation model name.
    :param build: The build number to encode in this SysEx file.

    :return: An exit code indicating if the operation was successful or not. Zero
        means success, any other value failure.
    """
    logger = logging.getLogger(__name__)
    buffer = bytearray()
    decoded = bytearray()
    encoded = bytearray()

    # Required to be calculated for metadata.
    crc = int()
    size = int()

    in_path = pathlib.Path(filename).resolve()
    out_path = f"{in_path}.syx"

    # Do horrible things with integers to get them into the desired format.
    build_string = str(build).rjust(constant.FIELD_BUILD_SIZE, "0")
    build_number = bytearray(constant.FIELD_BUILD_SIZE)

    logger.info(f"Starting encoding of SysEx for {model}, build {build_string}")
    for index, byte in enumerate(bytearray([int(digit) for digit in str(build)])[::-1]):
        build_number[(len(build_number) - 1) - index] = byte

    # Construct the start message.
    start = message.Start()
    start.manufacturer = constant.MANUFACTURER_IDS["Novation"]
    start.model = constant.MODEL_IDS[model]
    start.build = build_number

    try:
        logger.info(f"Reading binary from {in_path}")

        with open(in_path, "rb") as fin:
            # First chunk is handled last - to account for the final "carry".
            fin.seek(constant.FIELD_CHUNK_SIZE)

            while True:
                buffer = bytearray(fin.read(constant.FIELD_CHUNK_SIZE))
                if len(buffer) < 1:
                    break

                # Track the raw / unencoded value - as this will be required for both
                # size and CRC later.
                decoded.extend(buffer)

                # Add a data message to the output buffer for each chunk.
                data = message.Data()
                data.chunk = codec.encoder(buffer)
                encoded.extend(data.to_bytes())

            # Handle the first chunk last.
            fin.seek(0)
            end = message.End()
            buffer = bytearray(fin.read(constant.FIELD_CHUNK_SIZE))

            # Add this chunk to the START of the original buffer.
            decoded = bytearray(buffer) + decoded

            end.chunk = codec.encoder(buffer)
            encoded.extend(end.to_bytes())
    except (OSError, ValueError) as err:
        logger.fatal(f"Unable to read binary from file {in_path}: {err}")
        return 1

    # Construct the metadata message.
    size = len(decoded)
    crc = codec.crc32(decoded)

    metadata = message.Metadata()
    metadata.chunk = bytearray(8 * 2)
    metadata.payload_size = codec.bytes_to_nibbles(
        bytearray(size.to_bytes(4, byteorder="big"))
    )
    metadata.crc = codec.bytes_to_nibbles(
        bytearray(crc.to_bytes(4, byteorder="big")),
    )
    metadata.build = bytearray(
        str(build).rjust(constant.FIELD_BUILD_SIZE, "0"), "utf-8"
    )

    # Build the SysEx file.
    logger.info(f"Input binary file size {size}-bytes (CRC32 0x{crc:08x})")
    encoded = bytearray(metadata.to_bytes()) + encoded
    encoded = bytearray(start.to_bytes()) + encoded

    try:
        logger.info(f"Writing encoded SysEx to {out_path}")

        with open(out_path, "wb") as fout:
            fout.write(encoded)
    except OSError as err:
        logger.fatal(f"Unable to write SysEx to file {out_path}: {err}")
        return 1

    return 0


# mypy: disable-error-code="attr-defined"
def decode(filename: str) -> int:
    """Decodes Novation compatible SysEx to a binary file.

    :param filename: The name and path to the file to decode.

    :return: An exit code indicating if the operation was successful or not. Zero
        means success, any other value failure.
    """
    logger = logging.getLogger(__name__)
    buffer = bytearray()
    output = bytearray()
    in_path = pathlib.Path(filename).resolve()
    out_path = f"{in_path}.bin"

    # Supported message types.
    messages = [message.Start, message.End, message.Metadata, message.Data]

    # This information will be extracted from metadata.
    crc = int()
    size = int()

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
                    raise ValueError(
                        f"Unsupported SysEx message found {offset}-bytes into file"
                    )

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
                    size = int.from_bytes(
                        codec.nibbles_to_bytes(handler.payload_size), byteorder="big"
                    )
                    crc = int.from_bytes(
                        codec.nibbles_to_bytes(handler.crc), byteorder="big"
                    )
                    logger.info(f"SysEx file appears to contain build {build}")
                    logger.info(f"Encoded file size {size}-bytes (CRC32 0x{crc:08x})")

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
            fout.write(output[0:size])
    except OSError as err:
        logger.fatal(f"Unable to write binary to file {out_path}: {err}")
        return 1

    return 0


def entrypoint():
    """The main xKey CLI entrypoint."""

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
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

    # Dispatch.
    if arguments.subparser == "encode":
        sys.exit(encode(arguments.filename, arguments.model, arguments.build))

    if arguments.subparser == "decode":
        sys.exit(decode(arguments.filename))

    parser.print_help()
    sys.exit(1)
