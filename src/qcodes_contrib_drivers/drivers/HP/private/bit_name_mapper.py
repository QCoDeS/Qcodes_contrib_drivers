class BitNameMapper:
    """
    Manages mappings between integer values and corresponding bit names.

    Attributes:
        bit_map (dict): Maps bit positions to bit names.
        Example:
            self._map_STB = BitNameMapper({
                2: 'Event Status Register B Summary Bit',
                3: 'Questionable Status Register Summary Bit',
                4: 'Message in Output Queue A',
                5: 'Standard Event Status Register Summary Bit',
                6: 'Request Service',
                7: 'Operation Status Register Summary Bit'
            })

    Methods:
        value_to_bitnames: Converts an integer to a list of bit names.
        bitnames_to_value: Converts a list of bit names to an integer value.
        docstring: Generates a docstring listing the available bit names.
    """

    def __init__(self, bit_map: dict):
        """
        Initialize the BitNameMapper with a mapping dictionary.

        Args:
            bit_map (dict): A dictionary mapping bit positions to names.
        """
        self.bit_map = bit_map

    @property
    def bit_map(self) -> dict:
        """Returns the current bit position to name mapping."""
        return self._bit_map

    @bit_map.setter
    def bit_map(self, bit_map: dict) -> None:
        """Sets the bit mapping and creates an inverse mapping."""
        self._bit_map = bit_map
        self._inverse_bit_map = {name: position for position, name in bit_map.items()}

    def value_to_bitnames(
        self,
        value: int,
        disabled_bits: list[int] = []
    ) -> list[str]:
        """
        Converts an integer value to a list of corresponding bit names.

        Args:
            value (int): The integer value to convert.
            disabled_bits (list[int]): A list of bit positions to ignore.

        Returns:
            list[str]: The names of the bits set in the value.

        Raises:
            ValueError: If a disabled bit is set in the value.
            KeyError: If a bit position in the value has no corresponding name.
        """
        bit_names = []
        for bit_position in range(value.bit_length()):
            if value & 1:
                if bit_position in disabled_bits:
                    raise ValueError(f"Bit position {bit_position} is disabled")
                if bit_position in self._bit_map:
                    bit_names.append(self._bit_map[bit_position])
                else:
                    raise KeyError(f"Unmapped bit at position: {bit_position}")
            value >>= 1
        return bit_names

    def bitnames_to_value(self, bit_names: list[str]) -> int:
        """
        Converts a list of bit names to their corresponding integer value.

        Args:
            bit_names (list[str]): The list of bit names to convert.

        Returns:
            int: The integer value represented by the bit names.
        """
        value = 0
        for bit_name in bit_names:
            bit_position = self._inverse_bit_map.get(bit_name)
            if bit_position is None:
                raise KeyError(f"Unmapped bit name: {bit_name}")
            value += 2 ** bit_position
        return value

    def docstring(self, disabled_bits: list[int] = []) -> str:
        """
        Generates a docstring listing the available bit names, excluding any disabled bits.

        Args:
            disabled_bits (list[int]): A list of bit positions to exclude from the docstring.

        Returns:
            str: A formatted string listing the available bit names.
        """
        docstring = ""
        for bit_index, bit_name in self._bit_map.items():
            if bit_index not in disabled_bits:
                docstring += f" * '{bit_name}'\n"
        return docstring
