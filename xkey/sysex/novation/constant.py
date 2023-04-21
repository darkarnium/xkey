"""Novation specific constants."""

# It's unknown whether this is actually a manufacturer identifier, or part of the model
# identifier.
MANUFACTURER_IDS = {
    "Novation": bytearray([0x02]),
}

# These are based on Novation firmware analysis, and may not be exact.
MODEL_IDS = {
    "flkey": bytearray([0x11]),
    "launchkey-mk3": bytearray([0x0F]),
}


# Size of fields used by models.
FIELD_BUILD_SIZE = 6
FIELD_CHUNK_SIZE = 32
