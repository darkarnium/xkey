"""XKey."""

import logging

from xkey import codec, constant

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] %(message)s",
)
logger = logging.getLogger("xkey")

FIRMWARE_FILE = (
    "/home/darkarnium/Code/Jupyter/jupyterlab/work/Novation/SysEx/flkey-firmware-52.syx"
)


buffer = bytearray()
output = bytearray()

chunks = 0

with open(FIRMWARE_FILE, "rb") as fin:
    while True:
        buffer = bytearray(fin.read(2))
        if len(buffer) < 1:
            break

        if buffer[0] != constant.MIDI_SYSEX_SOX:
            logger.error("MIDI SysEx SOX not found. Is this a firmware file?")
            break

        # Read a two-byte Manufacturer ID if the first byte is 0x00.
        if buffer[1] == 0x0:
            buffer = bytearray(fin.read(2))

            try:
                manufacturer = codec.get_manufacturer_by_id(buffer[0:2])
            except ValueError as err:
                logger.error(f"{err} (0x{buffer[0]:02x} 0x{buffer[1]:02x}).")
                break

            offset = fin.tell() - len(buffer)
            logger.debug(
                f"Got MIDI SysEx message for manufacturer '{manufacturer}' at {offset}"
            )

        # Read and process the command.
        buffer = bytearray(fin.read(2))
        message = None

        for candidate in MIDI_SYSEX_MESSAGES:
            if candidate.identifier == buffer:
                message = candidate

        if message is None:
            logger.error(
                f"Unknown MIDI SysEx command (0x{buffer[0]:02x} 0x{buffer[1]:02x})."
            )
            break

        # Read the required number of bytes to get the body of the message.
        buffer = bytearray(fin.read(struct.calcsize(message.structure)))
        parser = namedtuple(message.name, " ".join(message.fields))
        parsed = parser._make(struct.unpack(message.structure, bytes(buffer)))

        logger.debug(f"Processing MIDI SysEx message '{message.name}'")

        if message.name in [MIDI_SYSEX_NOVATION_DATA, MIDI_SYSEX_NOVATION_DEND]:
            candidate = codec.decoder(parsed.chunk)

            # Messages with 'command' 0x73 are at the end of the SysEx, but appear
            # to be the data for the first chunk in the firmware.
            if message.name == MIDI_SYSEX_NOVATION_DEND:
                candidate.extend(output)
                output = candidate

            if message.name == MIDI_SYSEX_NOVATION_DATA:
                output.extend(candidate)

        # Ensure the next byte is an EOX.
        buffer = fin.read(1)
        if buffer[0] != MIDI_SYSEX_EOX:
            logger.error(f"MIDI SysEx EOX not found. Malformed or corrupt file?")
            break

        chunks += 1
