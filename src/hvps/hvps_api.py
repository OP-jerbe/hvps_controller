import socket
from socket import SocketType
from typing import Literal

Channels = Literal['BM', 'EX', 'L1', 'L2', 'L3', 'L4', 'SL']

NAKS = {
    'NAK': 'No Error',
    'NAK0': 'No Error',
    'NAK1': 'Invalid Command',
    'NAK2': 'Invalid Parameter',
    'NAK3': 'Session Expired',
    'NAK4': 'Time Out',
}


class HVPSv3:
    def __init__(
        self,
        sock: SocketType,
        occupied_channels: tuple[Channels, ...] = (
            'BM',
            'EX',
            'L1',
            'L2',
            'L3',
            'L4',
            'SL',
        ),
    ) -> None:
        self.sock = sock
        self.occupied_channels = occupied_channels
        self.all_channels: tuple[Channels, ...] = (
            'BM',
            'EX',
            'L1',
            'L2',
            'L3',
            'L4',
            'SL',
        )

    def send_query(self, query: str) -> str:
        """Sends a command to the HVPS and returns the response"""
        if not self.sock:
            raise ConnectionError('Socket is not connected')
        # print(f'Command: {query}')
        if not query.endswith('\n'):
            query += '\n'

        try:
            self.sock.sendall(query.encode())
            response = self.sock.recv(1024)
            return response.decode().strip()

        except socket.error as e:
            raise ConnectionError(f'Socket communication error {e}')

    def set_solenoid_current(self, current: str) -> str | None:
        """
        Sets the solenoid current. Max current is 3.0 A.
        Command must be STSLT00n.nn. So input must be converted to ensure the n.nn format.
        """

        ##### LOGIC #####
        # Check to make sure solenoid is installed in the HVPS.
        # Handle empty string arguement
        # Convert the current argument to a float to make sure input has a decimal point.
        # Convert the float back to a string with two decimal places.
        # Input the current value into the command.

        if 'SL' not in self.occupied_channels:
            return

        if current == '':
            current = '0'

        num = float(current)
        current = f'{num:.2f}'
        command = f'STSLT00{current}'
        response = self.send_query(command)
        # print(f'set_solenoid_current response: "{response}"')
        return response

    def set_voltage(self, channel: str, voltage: str) -> str:
        """Sets the voltage of the specified channel in the HVPS"""

        ##### LOGIC #####
        # Check to make sure the channel is installed into the HVPS
        # Disallow setting the solenoid voltage.
        # Handle empty string arguement
        # Set the prefix of the command.
        # Get the sign used to set the voltage then remove it from the voltage string.
        # With the sign removed, pad the front of the string with zeros so voltage has 5 characters.
        # Put together the command with the prefix, sign, and voltage setting.
        # Send the query then print and return the response.

        if channel not in self.occupied_channels:
            raise ValueError(
                f'"{channel}" is not a valid channel. Valid channels: {self.occupied_channels}'
            )
        if channel == 'SL':
            raise ValueError('"SL" is not a valid channel for setting voltage.')

        command_prefix = f'ST{channel}T'

        if voltage == '':
            voltage = '0'

        if '-' in voltage:
            sign = '-'
            voltage = voltage.replace('-', '')
        else:
            sign = '+'
            voltage = voltage.replace('+', '')

        voltage = voltage.zfill(5)
        command = f'{command_prefix}{sign}{voltage}'
        response = self.send_query(command)
        # print(f'set_voltage response: "{response}"')
        return response

    def get_voltage(self, channel: str) -> str:
        "Queries the current voltage of a channel in the HVPS"
        if channel not in self.occupied_channels:
            raise ValueError(
                f'"{channel}" is not a valid channel. Valid channels: {self.occupied_channels}'
            )
        command = f'RD{channel}V'
        response = self.send_query(command)
        # print(f'get_voltage response: "{response}"')
        return response

    def get_current(self, channel: str) -> str:
        "Queries the current electric-current of a channel in the HVPS"
        if channel not in self.occupied_channels:
            raise ValueError(
                f'"{channel}" is not a valid channel. Valid channels: {self.occupied_channels}'
            )
        command = f'RD{channel}C'
        response = self.send_query(command)
        # print(f'get_current response: "{response}"')
        return response

    def enable_high_voltage(self) -> str:
        """Enables high voltage to be turned on"""
        command = 'STHV1'
        response = self.send_query(command)
        # print(f'enable_high_voltage response: "{response}"')
        return response

    def disable_high_voltage(self) -> str:
        """Turns off high voltage"""
        command = 'STHV0'
        response = self.send_query(command)
        # print(f'disable_high_voltage response: "{response}"')
        return response

    def enable_solenoid_current(self) -> str:
        """Enables the solenoid current to be turned on"""
        command = 'STSL1'
        response = self.send_query(command)
        # print(f'enable_solenoid response: "{response}"')
        return response

    def disable_solenoid_current(self) -> str:
        """Turns off solenoid current."""
        command = 'STSL0'
        response = self.send_query(command)
        # print(f'disable_solenoid response: "{response}"')
        return response

    def enable_wobble(self, channel: str, amplitude: str) -> str | None:
        """Enables wobbling of EX, L1, L2, L3, or L4 channels. Acceptable amplitude values: 0-999"""

        valid_channels = [s for s in self.occupied_channels if s not in ('BM', 'SL')]
        if channel not in self.occupied_channels:
            raise ValueError(
                f'"{channel}" is not a valid channel. Valid channels: {valid_channels}'
            )

        amplitude = amplitude.zfill(3)

        command = f'ST{channel}WE1A{amplitude}'
        response = self.send_query(command)
        # print(f'enable_wobble response: "{response}"')
        return response

    def disable_wobble(self, channel: str) -> str | None:
        """Disables wobbling"""

        valid_channels = [s for s in self.occupied_channels if s not in ('BM', 'SL')]
        if channel not in self.occupied_channels:
            raise ValueError(
                f'"{channel}" is not a valid channel. Valid channels: {valid_channels}'
            )

        command = f'ST{channel}WEA0000'
        response = self.send_query(command)
        # print(f'disable_wobble response: "{response}"')
        return response

    def get_state(self) -> str:
        """
        Gets the enable state of the HV and solenoid

        Possible states:
            HV off / sol off returns 'STATE0000'
            HV off / sol on returns 'STATE0010'
            HV on / sol off returns 'STATE0001'
            HV on / sol on returns 'STATE0011'
        """
        command = 'RDSTA'
        response = self.send_query(command)
        # print(f'get_state response: "{response}"')
        return response
