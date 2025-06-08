import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Iterable, Literal, Optional

from fpdf import FPDF

from helpers.helpers import get_root_dir


class HVPSReport(FPDF):
    def __init__(
        self,
        serial_number: str,
        occupied_channels: list[str],
        readbacks: dict[str, list[str]],
        measurements: dict[str, list[str]],
        orientation: Literal['portrait'] = 'portrait',
        unit: Literal['mm'] = 'mm',
        format: Literal['Letter'] = 'Letter',
    ) -> None:
        super().__init__(orientation, unit, format)
        self.serial_number = serial_number
        self.occupied_channels = occupied_channels
        self.readbacks = readbacks
        self.measurements = measurements
        self.set_margin(20.3)  # set all margins to the same value
        self.add_page()
        self.cell_widths = [30, 18, 30, 30]
        self.row_height = 5.5
        self.create_report()

    def add_title_bar(self) -> None:
        self.set_y(self.t_margin / 2)  # center the cursor within the header height
        root_dir: Path = get_root_dir()
        logo_path: Path = root_dir / 'assets' / 'op_logo.png'
        if logo_path.exists():
            self.image(
                logo_path,
                x=self.r_margin / 2,
                y=self.t_margin / 2,
                h=self.t_margin / 4,
                keep_aspect_ratio=True,
            )
        self.set_font(family='Helvetica', style='B', size=int(self.t_margin))
        self.cell(
            text=f'HVPS Test Results ({self.serial_number})', align='C', center=True
        )

    def add_table_header(self) -> None:
        self.set_font('Helvetica', 'B', 12)

        # Set the cursor 5 mm below the title bar
        self.set_xy(self.l_margin, self.t_margin + self.row_height)
        headers = ['Channel', 'Setting', 'Readback', 'Measurement']
        for i, header in enumerate(headers):
            self.cell(self.cell_widths[i], self.row_height, header, border=1, align='C')
        self.ln(self.row_height)

    def add_table_data(self) -> None:
        self.set_font('Helvetica', '', 12)

        # set the cursor below the table header row
        self.set_xy(self.l_margin, self.t_margin + 2 * self.row_height)

        channels: dict[str, list[str]] = {
            'Beam': ['100 V', '500 V', '1000 V', '-100 V', '-500 V', '-1000 V'],
            'Extractor': ['100 V', '500 V', '1000 V', '-100 V', '-500 V', '-1000 V'],
            'Lens 1': ['100 V', '500 V', '1000 V', '-100 V', '-500 V', '-1000 V'],
            'Lens 2': ['100 V', '500 V', '1000 V', '-100 V', '-500 V', '-1000 V'],
            'Lens 3': ['100 V', '500 V', '1000 V', '-100 V', '-500 V', '-1000 V'],
            'Lens 4': ['100 V', '500 V', '1000 V', '-100 V', '-500 V', '-1000 V'],
            'Solenoid': ['0.30 A', '1.20 A', '2.50 A'],
        }

        for (channel, settings), (_, readings), (_, measurements) in zip(
            channels.items(), self.readbacks.items(), self.measurements.items()
        ):
            y_start = self.get_y()
            x_start = self.get_x()

            # Draw the channel name with row span
            total_height = self.row_height * len(settings)
            self.multi_cell(
                self.cell_widths[0], total_height, channel, border=1, align='C'
            )

            # Go back to the right of the channel cell
            self.set_xy(x_start + self.cell_widths[0], y_start)

            # Draw the settings and placeholders
            y_pos = self.get_y()
            for setting, reading, measurement in zip(settings, readings, measurements):
                self.set_xy(x_start + self.cell_widths[0], y_pos)
                self.cell(
                    self.cell_widths[1],
                    self.row_height,
                    text=setting,
                    border=1,
                    align='R',
                )
                self.cell(
                    self.cell_widths[2],
                    self.row_height,
                    text=reading,
                    border=1,
                    align='C',
                )  # Readback placeholder
                self.cell(
                    self.cell_widths[3],
                    self.row_height,
                    text=measurement,
                    border=1,
                    align='C',
                )  # Measurement placeholder

                # Move to the beginning of the next line for the 2nd+3rd+4th columns
                y_pos += self.row_height
                self.set_x(x_start + self.cell_widths[0])
                self.set_y(y_pos)

    def footer(self) -> None:
        self.set_y(-20.3 / 2)  # center the cursor within the footer height
        self.set_x(self.l_margin)
        self.set_font(family='Helvetica', style='I', size=8)
        self.cell(text=f'Tested: {datetime.now():%Y-%m-%d}', align='C')

    def create_report(self) -> None:
        self.add_title_bar()
        self.add_table_header()
        self.add_table_data()

    def open(self) -> None:
        temp_dir = tempfile.gettempdir()
        pdf_path = Path(temp_dir) / 'HVPS_test_results.pdf'

        self.output(str(pdf_path))

        # Open the PDF file using the default PDF viewer
        subprocess.run(
            ['start', '', str(pdf_path)],
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


if __name__ == '__main__':
    serial_number = 'SN-1048'
    occupied_channels = ['BM', 'EX', 'L1', 'SL']
    readbacks = {
        'BM': ['100', '500', '1000', '-100', '-500', '-1000'],
        'EX': ['100', '500', '1000', '-100', '-500', '-1000'],
        'L1': ['100', '500', '1000', '-100', '-500', '-1000'],
        'L2': ['100', '500', '1000', '-100', '-500', '-1000'],
        'L3': ['100', '500', '1000', '-100', '-500', '-1000'],
        'L4': ['100', '500', '1000', '-100', '-500', '-1000'],
        'SL': ['0.30', '1.20', '2.50'],
    }
    measurements = {
        'BM': ['100', '500', '1000', '-100', '-500', '-1000'],
        'EX': ['100', '500', '1000', '-100', '-500', '-1000'],
        'L1': ['100', '500', '1000', '-100', '-500', '-1000'],
        'L2': ['100', '500', '1000', '-100', '-500', '-1000'],
        'L3': ['100', '500', '1000', '-100', '-500', '-1000'],
        'L4': ['100', '500', '1000', '-100', '-500', '-1000'],
        'SL': ['0.30', '1.20', '2.50'],
    }
    pdf = HVPSReport(serial_number, occupied_channels, readbacks, measurements)
    pdf.output('hvps_test_report.pdf')
    print("PDF report 'hvps_test_report.pdf' created successfully.")
