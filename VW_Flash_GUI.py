import asyncio
import glob
from pathlib import Path
import wx
import os.path as path
import logging
import json
import threading
import sys
import serial
import serial.tools.list_ports

from zipfile import ZipFile
from datetime import datetime

from lib import extract_flash
from lib import binfile
from lib import flash_uds
from lib import simos_flash_utils
from lib import dsg_flash_utils
from lib import dq381_flash_utils
from lib import constants
from lib import simos_hsl
from lib.esp import flash_esp

from lib.modules import (
    simos8,
    simos10,
    simos12,
    simos122,
    simos18,
    simos1810,
    simos184,
    dq250mqb,
    dq381,
    simos16,
    simosshared,
)

if sys.platform == "win32":
    try:
        import winreg
    except:
        print("module winreg not found")

# Get an instance of logger, which we'll pull from the config file
logger = logging.getLogger("VWFlash")

try:
    currentPath = path.dirname(path.abspath(__file__))
except NameError:  # We are the main py2exe script, not a module
    currentPath = path.dirname(path.abspath(sys.argv[0]))

logging.config.fileConfig(path.join(currentPath, "logging.conf"))


def write_config(paths):
    with open("gui_config.json", "w") as config_file:
        json.dump(paths, config_file)


def module_selection_is_dq250(selection_index):
    return selection_index == 2


def module_selection_is_dq381(selection_index):
    return selection_index == 3


def split_interface_name(interface_string: str):
    parts = interface_string.split("_", 1)
    interface = parts[0]
    interface_name = parts[1] if len(parts) > 1 else None
    return (interface, interface_name)


async def async_scan_for_ble_devices():
    interfaces = []
    try:
        # We have to import this from the correct thread. No joke.
        from bleak import BleakScanner

        devices = await BleakScanner.discover(
            service_uuids=[constants.BLE_SERVICE_IDENTIFIER]
        )
    except:
        return interfaces
    for d in devices:
        interfaces.append((d.name, "BLEISOTP_" + d.address))
    return interfaces


def scan_for_ble_devices(callback):
    threading.Thread(
        target=lambda cb: cb(asyncio.run(async_scan_for_ble_devices())), args=[callback]
    ).start()


def get_dlls_from_registry():
    # Interfaces is a list of tuples (name: str, interface specifier: str)
    interfaces = []
    try:
        BaseKey = winreg.OpenKeyEx(
            winreg.HKEY_LOCAL_MACHINE, r"Software\\PassThruSupport.04.04\\"
        )
    except:
        logger.error("No J2534 DLLs found in HKLM PassThruSupport. Continuing anyway.")
        return interfaces

    for i in range(winreg.QueryInfoKey(BaseKey)[0]):
        DeviceKey = winreg.OpenKeyEx(BaseKey, winreg.EnumKey(BaseKey, i))
        Name = winreg.QueryValueEx(DeviceKey, "Name")[0]
        FunctionLibrary = winreg.QueryValueEx(DeviceKey, "FunctionLibrary")[0]
        interfaces.append((Name, "J2534_" + FunctionLibrary))
    return interfaces


def socketcan_ports():
    return [("SocketCAN can0", "SocketCAN_can0")]


def poll_interfaces():
    # this is a list of tuples (name: str, interface_specifier: str) where interface_specifier is something like USBISOTP_/dev/ttyUSB0
    interfaces = []

    if sys.platform == "win32":
        interfaces += get_dlls_from_registry()
    if sys.platform == "linux":
        interfaces += socketcan_ports()

    serial_ports = serial.tools.list_ports.comports()
    for port in serial_ports:
        interfaces.append(
            (port.name + " : " + port.description, "USBISOTP_" + port.device)
        )
    return interfaces


class FlashPanel(wx.Panel):
    input_blocks: dict[str, constants.BlockData]

    def __init__(self, parent):
        super().__init__(parent)

        try:
            with open("gui_config.json", "r") as config_file:
                self.options = json.load(config_file)
        except:
            logger.critical("No config file present, creating one")
            self.options = {
                "cal": "",
                "flashpack": "",
                "bins": "",
                "logger": "",
                "interface": "",
                "singlecsv": False,
                "logmode": "3E",
                "activitylevel": "INFO",
            }
            write_config(self.options)

        self.interfaces = poll_interfaces()

        # Pick first interface if none already selected.
        if (len(self.options["interface"])) == 0:
            if len(self.interfaces) > 0:
                self.options["interface"] = self.interfaces[0][1]
                write_config(self.options)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        folder_sizer = wx.BoxSizer(wx.HORIZONTAL)
        actions_sizer = wx.BoxSizer(wx.HORIZONTAL)
        selections_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Create a drop down menu

        self.flash_info = simos18.s18_flash_info
        available_modules = [
            "Simos 18.1/6",
            "Simos 18.10",
            "DQ250-MQB DSG",
            "DQ381 DSG UNTESTED",
        ]
        self.module_choice = wx.Choice(self, choices=available_modules)
        self.module_choice.SetSelection(0)
        self.module_choice.Bind(wx.EVT_CHOICE, self.on_module_changed)

        available_actions = [
            "Calibration Flash Unlocked",
            "FlashPack ZIP flash",
            "Full Flash Unlocked (BIN/FRF)",
            "Unlock ECU (FRF)",
            "Flash Stock (Re-Lock) / Unmodified BIN/FRF",
        ]
        self.action_choice = wx.Choice(self, choices=available_actions)
        self.action_choice.SetSelection(0)
        self.action_choice.Bind(wx.EVT_CHOICE, self.update_bin_listing)

        # Create a button for choosing the folder
        self.folder_button = wx.Button(self, label="Open Folder...")
        self.folder_button.Bind(wx.EVT_BUTTON, self.GetParent().on_open_folder)

        folder_sizer.Add(self.folder_button, 0, wx.ALL | wx.LEFT, 5)

        self.progress_bar = wx.Gauge(self, range=100, style=wx.GA_HORIZONTAL)

        self.row_obj_dict = {}

        self.list_ctrl = wx.ListCtrl(
            self, size=(-1, 250), style=wx.LC_REPORT | wx.BORDER_SUNKEN
        )
        self.list_ctrl.InsertColumn(0, "Filename", width=400)
        self.list_ctrl.InsertColumn(1, "Modify time", width=100)

        self.feedback_text = wx.TextCtrl(
            self, size=(-1, 300), style=wx.TE_READONLY | wx.TE_LEFT | wx.TE_MULTILINE
        )

        flash_button = wx.Button(self, label="Flash")
        flash_button.Bind(wx.EVT_BUTTON, self.on_flash)

        dtc_button = wx.Button(self, label="Read Trouble Codes")
        dtc_button.Bind(wx.EVT_BUTTON, self.on_read_dtcs)

        get_info_button = wx.Button(self, label="Get Ecu Info")
        get_info_button.Bind(wx.EVT_BUTTON, self.on_get_info)

        actions_sizer.Add(self.module_choice, 0, wx.LEFT, 5)
        actions_sizer.Add(get_info_button, 0, wx.LEFT | wx.RIGHT, 5)
        actions_sizer.Add(dtc_button, 0, wx.RIGHT, 5)

        selections_sizer.Add(self.action_choice, 0, wx.EXPAND | wx.ALL, 5)
        selections_sizer.Add(flash_button, 0, wx.EXPAND | wx.ALL, 5)

        main_sizer.Add(self.feedback_text, 0, wx.ALL | wx.EXPAND, 5)
        main_sizer.Add(actions_sizer, 0, wx.TOP, 5)
        main_sizer.Add(folder_sizer, 0, wx.ALIGN_RIGHT, 5)
        main_sizer.Add(self.list_ctrl, 0, wx.ALL | wx.EXPAND, 5)
        main_sizer.Add(self.progress_bar, 0, wx.EXPAND, 5)
        main_sizer.Add(selections_sizer)

        self.SetSizer(main_sizer)

        if self.options["cal"] != "":
            self.current_folder_path = self.options["cal"]
            self.update_bin_listing()

    def on_module_changed(self, event):
        module_number = self.module_choice.GetSelection()
        self.flash_info = [
            simos18.s18_flash_info,
            simos1810.s1810_flash_info,
            dq250mqb.dsg_flash_info,
            dq381.dsg_flash_info,
        ][module_number]

    def on_get_info(self, event):
        (interface, interface_path) = split_interface_name(self.options["interface"])
        ecu_info = flash_uds.read_ecu_data(
            self.flash_info,
            interface=interface,
            callback=self.update_callback,
            interface_path=interface_path,
        )

        [
            self.feedback_text.AppendText(did + " : " + ecu_info[did] + "\n")
            for did in ecu_info
        ]

    def on_read_dtcs(self, event):
        (interface, interface_path) = split_interface_name(self.options["interface"])
        dtcs = flash_uds.read_dtcs(
            self.flash_info,
            interface=interface,
            callback=self.update_callback,
            interface_path=interface_path,
        )
        [
            self.feedback_text.AppendText(str(dtc) + " : " + dtcs[dtc] + "\n")
            for dtc in dtcs
        ]

    def flash_unlock(self, selected_file):
        if module_selection_is_dq250(
            self.module_choice.GetSelection()
        ) or module_selection_is_dq381(self.module_choice.GetSelection()):
            self.feedback_text.AppendText("SKIPPED: Unlocking is unnecessary for DSG\n")
            return

        input_bytes = Path(self.row_obj_dict[selected_file]).read_bytes()
        if str.endswith(self.row_obj_dict[selected_file], ".frf"):
            self.feedback_text.AppendText("Extracting FRF for unlock...\n")
            (flash_data, allowed_boxcodes,) = extract_flash.extract_flash_from_frf(
                input_bytes,
                self.flash_info,
                is_dsg=module_selection_is_dq250(self.module_choice.GetSelection()),
            )
            self.input_blocks = {}
            for i in self.flash_info.block_names_frf.keys():
                filename = self.flash_info.block_names_frf[i]
                self.input_blocks[filename] = constants.BlockData(
                    i, flash_data[filename]
                )

            cal_block = self.input_blocks[self.flash_info.block_names_frf[5]]
            file_box_code = str(
                cal_block.block_bytes[
                    self.flash_info.box_code_location[5][
                        0
                    ] : self.flash_info.box_code_location[5][1]
                ].decode()
            )
            if (
                file_box_code.strip()
                != self.flash_info.patch_info.patch_box_code.split("_")[0].strip()
            ):
                self.feedback_text.AppendText(
                    f"Boxcode mismatch for unlocking. Got box code {file_box_code} but expected {self.flash_info.patch_box_code}. Please don't try to be clever. Supply the correct file and the process will work."
                )
                return

            self.input_blocks["UNLOCK_PATCH"] = constants.BlockData(
                self.flash_info.patch_info.patch_block_index + 5,
                Path(self.flash_info.patch_info.patch_filename).read_bytes(),
            )
            key_order = list(
                map(lambda i: self.flash_info.block_names_frf[i], [1, 2, 3, 4, 5])
            )
            key_order.insert(4, "UNLOCK_PATCH")
            input_blocks_with_patch = {k: self.input_blocks[k] for k in key_order}
            self.input_blocks = input_blocks_with_patch
            self.flash_bin(get_info=False)
        else:
            self.feedback_text.AppendText(
                "File did not appear to be a valid FRF. Unlocking is possible only with a specific FRF file for your ECU family.\n"
            )

    def flash_bin_file(self, selected_file, patch_cboot=False):
        input_bytes = Path(self.row_obj_dict[selected_file]).read_bytes()
        if str.endswith(self.row_obj_dict[selected_file], ".frf"):
            self.feedback_text.AppendText("Extracting FRF...\n")
            (flash_data, allowed_boxcodes,) = extract_flash.extract_flash_from_frf(
                input_bytes,
                self.flash_info,
                is_dsg=module_selection_is_dq250(self.module_choice.GetSelection()),
            )
            self.input_blocks = {}
            for i in self.flash_info.block_names_frf.keys():
                filename = self.flash_info.block_names_frf[i]
                self.input_blocks[filename] = constants.BlockData(
                    i, flash_data[filename]
                )
            self.flash_bin(get_info=False, should_patch_cboot=patch_cboot)
        elif len(input_bytes) == self.flash_info.binfile_size:
            self.input_blocks = binfile.blocks_from_bin(
                self.row_obj_dict[selected_file], self.flash_info
            )
            self.flash_bin(get_info=False, should_patch_cboot=patch_cboot)
        else:
            self.feedback_text.AppendText(
                "File did not appear to be a valid BIN or FRF\n"
            )

    def flash_flashpack(self, selected_file: str):
        # We're expecting a "FlashPack" ZIP
        with ZipFile(self.row_obj_dict[selected_file], "r") as zip_archive:
            if "file_list.json" not in zip_archive.namelist():
                self.feedback_text.AppendText(
                    "SKIPPING: No file listing found in archive\n"
                )

            else:
                with zip_archive.open("file_list.json") as file_list_json:
                    file_list = json.load(file_list_json)

                self.input_blocks = {}
                for filename in file_list:
                    self.input_blocks[filename] = simos_flash_utils.BlockData(
                        int(file_list[filename]), zip_archive.read(filename)
                    )

                self.flash_bin(get_info=False)

    def flash_cal(self, selected_file: str):
        # Flash a Calibration block only
        self.input_blocks = {}

        if module_selection_is_dq250(self.module_choice.GetSelection()):
            # Populate DSG Driver block from a fixed file name for now.
            dsg_driver_path = path.join(self.options["cal"], "FD_2.DRIVER.bin")
            self.feedback_text.AppendText(
                "Loading DSG Driver from: " + dsg_driver_path + "\n"
            )
            self.input_blocks["FD_2.DRIVER.bin"] = constants.BlockData(
                self.flash_info.block_name_to_number["DRIVER"],
                Path(dsg_driver_path).read_bytes(),
            )
            self.input_blocks[self.row_obj_dict[selected_file]] = constants.BlockData(
                self.flash_info.block_name_to_number["CAL"],
                Path(self.row_obj_dict[selected_file]).read_bytes(),
            )
        else:
            input_bytes = Path(self.row_obj_dict[selected_file]).read_bytes()
            if len(input_bytes) == self.flash_info.binfile_size:
                self.feedback_text.AppendText(
                    "Extracting Calibration from full binary...\n"
                )
                input_blocks = binfile.blocks_from_bin(
                    self.row_obj_dict[selected_file], self.flash_info
                )
                # Filter to only CAL block.
                self.input_blocks = {
                    k: v
                    for k, v in input_blocks.items()
                    if v.block_number == self.flash_info.block_name_to_number["CAL"]
                }
            else:
                self.input_blocks[
                    self.row_obj_dict[selected_file]
                ] = constants.BlockData(
                    self.flash_info.block_name_to_number["CAL"],
                    input_bytes,
                )

        self.flash_bin()

    def on_flash(self, event):
        selected_file = self.list_ctrl.GetFirstSelected()
        logger.critical("Selected: " + str(self.row_obj_dict[selected_file]))

        if selected_file == -1:
            self.feedback_text.AppendText("SKIPPING: Select a file to flash!\n")
        else:
            choice = self.action_choice.GetSelection()
            if choice == 0:
                # "Flash Calibration"
                self.flash_cal(selected_file)

            elif choice == 1:
                # "Flash Flashpack"
                self.flash_flashpack(selected_file)

            elif choice == 2:
                # Flash BIN/FRF (unlocked)
                self.flash_bin_file(selected_file, patch_cboot=True)

            elif choice == 3:
                # "Unlock flash"
                self.flash_unlock(selected_file)

            elif choice == 4:
                # Flash to stock
                self.flash_bin_file(selected_file, patch_cboot=False)

    def update_bin_listing(self, event=None):
        self.list_ctrl.ClearAll()

        self.list_ctrl.InsertColumn(0, "Filename", width=500)
        self.list_ctrl.InsertColumn(1, "Modify Time", width=140)

        if self.action_choice.GetSelection() == 0:
            # Calibration Flash
            bins = glob.glob(self.current_folder_path + "/*.bin")
            self.options["cal"] = self.current_folder_path
        elif self.action_choice.GetSelection() == 1:
            # Flashpack
            bins = glob.glob(self.current_folder_path + "/*.zip")
            self.options["flashpacks"] = self.current_folder_path
        elif self.action_choice.GetSelection() == 2:
            # Full BIN/FRF Unlocked
            bins = glob.glob(self.current_folder_path + "/*.bin")
            bins.extend(glob.glob(self.current_folder_path + "/*.frf"))
            self.options["bins"] = self.current_folder_path
        elif self.action_choice.GetSelection() == 3:
            # Unlock ECU
            bins = glob.glob(
                self.current_folder_path
                + "/*"
                + self.flash_info.patch_info.patch_box_code
                + "*.frf"
            )
            self.options["bins"] = self.current_folder_path
        elif self.action_choice.GetSelection() == 4:
            # Unmodified flash
            bins = glob.glob(self.current_folder_path + "/*.bin")
            bins.extend(glob.glob(self.current_folder_path + "/*.frf"))
            self.options["bins"] = self.current_folder_path

        write_config(self.options)
        bins.sort(key=path.getmtime, reverse=True)

        bin_objects = []
        index = 0
        for bin_file in bins:
            self.list_ctrl.InsertItem(index, path.basename(bin_file))
            self.list_ctrl.SetItem(
                index,
                1,
                str(
                    datetime.fromtimestamp(path.getmtime(bin_file)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                ),
            )

            bin_objects.append(bin_file)
            self.row_obj_dict[index] = bin_file
            index += 1

    def threaded_callback(self, step, status, progress):
        self.GetParent().statusbar.SetStatusText(step)
        self.progress_bar.SetValue(round(float(progress)))
        self.feedback_text.AppendText(
            step + " - " + status + " - " + str(progress) + "\n"
        )

    def update_callback(self, **kwargs):
        if "flasher_step" in kwargs:
            wx.CallAfter(
                self.threaded_callback,
                kwargs["flasher_step"],
                kwargs["flasher_status"],
                kwargs["flasher_progress"],
            )
        else:
            wx.CallAfter(self.threaded_callback, kwargs["logger_status"], "0", 0)

    def flash_bin(self, get_info=True, should_patch_cboot=False):
        (interface, interface_path) = split_interface_name(self.options["interface"])
        if module_selection_is_dq250(self.module_choice.GetSelection()):
            flash_utils = dsg_flash_utils
        elif module_selection_is_dq381(self.module_choice.GetSelection()):
            flash_utils = dq381_flash_utils
        else:
            flash_utils = simos_flash_utils

        self.feedback_text.AppendText(
            "Starting to flash the following software components : \n"
            + binfile.input_block_info(self.input_blocks, self.flash_info)
            + "\n"
        )

        if get_info:
            ecu_info = flash_uds.read_ecu_data(
                self.flash_info,
                interface=interface,
                callback=self.update_callback,
                interface_path=interface_path,
            )

            [
                self.feedback_text.AppendText(did + " : " + ecu_info[did] + "\n")
                for did in ecu_info
            ]

        else:
            ecu_info = None

        for filename in self.input_blocks:
            fileBoxCode = str(
                self.input_blocks[filename]
                .block_bytes[
                    self.flash_info.box_code_location[
                        self.input_blocks[filename].block_number
                    ][0] : self.flash_info.box_code_location[
                        self.input_blocks[filename].block_number
                    ][
                        1
                    ]
                ]
                .decode()
            )

            if (
                ecu_info is not None
                and (
                    module_selection_is_dq250(self.module_choice.GetSelection())
                    or module_selection_is_dq381(self.module_choice.GetSelection())
                )
                is not True
                and ecu_info["VW Spare Part Number"].strip() != fileBoxCode.strip()
            ):
                self.feedback_text.AppendText(
                    "Attempting to flash a file that doesn't match box codes, exiting!: "
                    + ecu_info["VW Spare Part Number"]
                    + " != "
                    + fileBoxCode
                    + "\n"
                )
                return

        flasher_thread = threading.Thread(
            target=flash_utils.flash_bin,
            args=(
                self.flash_info,
                self.input_blocks,
                self.update_callback,
                interface,
                should_patch_cboot,
                interface_path,
            ),
        )
        flasher_thread.daemon = True
        flasher_thread.start()


class VW_Flash_Frame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title="VW_Flash GUI", size=(640, 770))
        self.create_menu()
        self.statusbar = self.CreateStatusBar(1)
        self.statusbar.SetStatusText("Choose a bin file directory")
        self.panel = FlashPanel(self)
        self.hsl_logger = None
        self.Show()

    def create_menu(self):
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        open_folder_menu_item = file_menu.Append(
            wx.ID_ANY, "Open Folder...", "Open a folder with bins"
        )
        extract_frf_menu_item = file_menu.Append(
            wx.ID_ANY, "Extract FRF...", "Extract an FRF file"
        )
        menu_bar.Append(file_menu, "&File")
        self.Bind(
            event=wx.EVT_MENU, handler=self.on_open_folder, source=open_folder_menu_item
        )
        self.Bind(
            event=wx.EVT_MENU,
            handler=self.on_select_extract_frf,
            source=extract_frf_menu_item,
        )

        interface_menu = wx.Menu()

        select_interface_menu_item = interface_menu.Append(
            wx.ID_ANY, "Select Interface...", "Select a CAN or PassThru Interface"
        )
        self.Bind(
            event=wx.EVT_MENU,
            handler=self.on_select_interface,
            source=select_interface_menu_item,
        )

        flash_esp_item = interface_menu.Append(
            wx.ID_ANY, "Reflash Macchina A0", "Flash A0 with latest firmware"
        )
        self.Bind(event=wx.EVT_MENU, handler=self.on_flash_esp, source=flash_esp_item)

        menu_bar.Append(interface_menu, "&Interface")

        logger_menu = wx.Menu()
        logger_path_menu_item = logger_menu.Append(
            wx.ID_ANY,
            "Select logging path...",
            "Select folder for logging configuration and data.",
        )
        self.Bind(
            event=wx.EVT_MENU,
            handler=self.select_logger_path,
            source=logger_path_menu_item,
        )
        logger_menu_item = logger_menu.Append(
            wx.ID_ANY, "Start Logger", "Start Simos High Speed Logger"
        )
        self.Bind(
            event=wx.EVT_MENU, handler=self.on_start_logger, source=logger_menu_item
        )
        logger_stop_menu_item = logger_menu.Append(
            wx.ID_ANY, "Stop Logger", "Stop Simos High Speed Logger"
        )
        self.Bind(
            event=wx.EVT_MENU, handler=self.on_stop_logger, source=logger_stop_menu_item
        )
        menu_bar.Append(logger_menu, "&Logger")

        self.SetMenuBar(menu_bar)

    def on_open_folder(self, event):
        title = "Choose a directory:"
        dlg = wx.DirDialog(self, title, style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.panel.current_folder_path = dlg.GetPath()
            self.panel.update_bin_listing()
        dlg.Destroy()

    def select_logger_path(self, event):
        title = "Choose a directory for logging:"
        dlg = wx.DirDialog(self, title, style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.panel.options["logger"] = dlg.GetPath()
            write_config(self.panel.options)
        dlg.Destroy()

    def on_start_logger(self, event):
        if self.hsl_logger is not None:
            return

        if self.panel.options["logger"] == "":
            return

        (interface, interface_path) = split_interface_name(
            self.panel.options["interface"]
        )
        self.hsl_logger = simos_hsl.hsl_logger(
            runserver=False,
            path=self.panel.options["logger"] + "/",
            callback_function=self.panel.update_callback,
            interface=interface,
            singlecsv=self.panel.options["singlecsv"],
            mode=self.panel.options["logmode"],
            level=self.panel.options["activitylevel"],
            interface_path=interface_path,
        )

        logger_thread = threading.Thread(target=self.hsl_logger.start_logger)
        logger_thread.daemon = True
        logger_thread.start()

        return

    def on_stop_logger(self, event):

        if self.hsl_logger is not None:
            self.hsl_logger.stop()
            self.hsl_logger = None

    def ble_scan_callback(self, interfaces):
        self.panel.interfaces += interfaces
        dialog_interfaces = []
        self.panel.interfaces = list(
            filter(lambda interface: interface[0] is not None, self.panel.interfaces)
        )
        for interface in self.panel.interfaces:
            dialog_interfaces.append(interface[0])
        dlg = wx.SingleChoiceDialog(
            self, "Select an Interface", "Select an interface", dialog_interfaces
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.panel.options["interface"] = self.panel.interfaces[dlg.GetSelection()][
                1
            ]
            write_config(self.panel.options)
            logger.info("User selected: " + self.panel.options["interface"])
        dlg.Destroy()

    def on_select_interface(self, event):
        progress_dialog = wx.ProgressDialog(
            "Scanning for devices...",
            "Checking J2534 and serial...",
            maximum=100,
            parent=self,
            style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE,
        )
        progress_dialog.Show()
        self.panel.interfaces = poll_interfaces()
        progress_dialog.Update(50, "Scanning for BLE devices...")

        def scan_finished(interfaces):
            progress_dialog.Update(100)
            wx.CallAfter(self.ble_scan_callback, interfaces)

        scan_for_ble_devices(scan_finished)

    def try_extract_frf(self, frf_data: bytes):
        flash_infos = [
            simos18.s18_flash_info,
            simos1810.s1810_flash_info,
            dq250mqb.dsg_flash_info,
            dq381.dsg_flash_info,
            simos184.s1841_flash_info,
            simos16.s16_flash_info,
            simos12.s12_flash_info,
            simos122.s122_flash_info,
            simos10.s10_flash_info,
            simos8.s8_flash_info,
        ]
        for flash_info in flash_infos:
            try:
                (flash_data, allowed_boxcodes) = extract_flash.extract_flash_from_frf(
                    frf_data,
                    flash_info,
                    is_dsg=(flash_info is dq250mqb.dsg_flash_info),
                )
                output_blocks = {}
                for i in flash_info.block_names_frf.keys():
                    filename = flash_info.block_names_frf[i]
                    output_blocks[filename] = constants.BlockData(
                        i, flash_data[filename], flash_info.number_to_block_name[i]
                    )
                return [output_blocks, flash_info]
            except:
                pass

    def extract_frf_task(self, frf_path: str, output_path: str, callback):
        frf_name = str.removesuffix(frf_path, ".frf")
        [output_blocks, flash_info] = self.try_extract_frf(Path(frf_path).read_bytes())
        outfile_data = binfile.bin_from_blocks(output_blocks, flash_info)
        callback(50)
        Path(output_path, Path(frf_name).name + ".bin").write_bytes(outfile_data)

        for filename in output_blocks:
            output_block: constants.BlockData = output_blocks[filename]
            binary_data = output_block.block_bytes
            output_filename = (
                filename.rstrip(".bin") + "." + output_block.block_name + ".bin"
            )
            Path(output_path, output_filename).write_bytes(binary_data)
        callback(100)

    def on_select_extract_frf(self, event):
        title = "Choose an FRF file:"
        dlg = wx.FileDialog(self, title, style=wx.FD_DEFAULT_STYLE, wildcard="*.frf")
        if dlg.ShowModal() == wx.ID_OK:
            frf_file = dlg.GetPath()
            dlg.Destroy()
            title = "Choose an output directory:"
            dlg = wx.DirDialog(self, title)
            if dlg.ShowModal() == wx.ID_OK:
                output_dir = dlg.GetPath()
                progress_dialog = wx.ProgressDialog(
                    "Extracting FRF",
                    "Decrypting and unpacking...",
                    maximum=100,
                    parent=self,
                    style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE,
                )
                callback = lambda progress: wx.CallAfter(
                    progress_dialog.Update, progress
                )
                frf_thread = threading.Thread(
                    target=self.extract_frf_task,
                    args=(frf_file, output_dir, callback),
                )
                frf_thread.start()
                progress_dialog.Pulse()
                progress_dialog.Show()

    def on_flash_esp(self, event):
        (interface, port) = split_interface_name(self.panel.options["interface"])
        if interface != "USBISOTP":
            wx.MessageBox(
                "Please select a USB interface using Interface->Select Interface first.",
                "Error",
                wx.OK,
            )
            return

        progress_dialog = wx.ProgressDialog(
            "Reflashing A0 ESP32 processor...",
            "Flashing in progress...",
            maximum=100,
            parent=self,
            style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE,
        )
        callback = lambda progress: wx.CallAfter(progress_dialog.Update, progress)
        bootloader = constants.internal_path("data", "esp32", "bootloader.bin")
        firmware = constants.internal_path("data", "esp32", "isotp_ble_bridge.bin")
        partition_table = constants.internal_path(
            "data", "esp32", "partition-table.bin"
        )

        if not Path.exists(Path(bootloader)):
            wx.MessageBox(
                "Please see data/esp32/README.md for firmware download instructions.",
                "Error",
                wx.OK,
            )
            callback(100)
            return

        flash_thread = threading.Thread(
            target=flash_esp.flash_esp,
            args=(bootloader, firmware, partition_table, port, callback),
        )
        flash_thread.start()
        progress_dialog.Pulse()
        progress_dialog.Show()


if __name__ == "__main__":
    app = wx.App(False)
    frame = VW_Flash_Frame()
    app.MainLoop()
