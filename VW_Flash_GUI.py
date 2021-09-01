import glob
import wx
import os.path as path
import logging
import json
import threading
import pprint
import sys

try:
    import winreg
except:
    print("module winreg not found")

from zipfile import ZipFile
from datetime import datetime

from lib import flash_uds
from lib import simos_flash_utils
from lib import constants
from lib import simos_hsl

# Get an instance of logger, which we'll pull from the config file
logger = logging.getLogger("VWFlash")

try:
    currentPath = path.dirname(path.abspath(__file__))
except NameError:  # We are the main py2exe script, not a module
    currentPath = path.dirname(path.abspath(sys.argv[0]))

logging.config.fileConfig(path.join(currentPath, "logging.conf"))

logger.info("Starting VW_Flash.py")


def read_from_file(infile=None):
    f = open(infile, "rb")
    return f.read()


def write_config(paths):
    with open("gui_config.json", "w") as config_file:
        json.dump(paths, config_file)


class FlashPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        self.flash_info = constants.s18_flash_info

        self.hsl_logger = None

        try:
            with open("gui_config.json", "r") as config_file:
                self.options = json.load(config_file)
        except:
            logger.critical("No config file present, creating one")
            self.options = {
                "cal": "",
                "flashpack": "",
                "logger": "",
                "interface": "",
                "singlecsv": False,
                "logmode": "3E",
                "activitylevel": "INFO",
            }
            with open("gui_config.json", "w") as config_file:
                write_config(self.options)

        if sys.platform == "win32":
            self.interfaces = self.get_dlls_from_registry()
            if len(self.interfaces) == 0:
                logger.critical("No J2534 devices found")
            elif len(self.interfaces) == 1:
                logger.info("1 J2534 device found, using: " + self.interfaces[0][1])
                self.options["interface"] = self.interfaces[0][1]
            else:
                logger.info("Need to select J2534 interface, defaulting to the first")
                self.options["interface"] = self.interfaces[0][1]

            write_config(self.options)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        middle_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Create a drop down menu
        available_actions = ["Calibration flash", "Full flash", "JoeLogger"]
        self.action_choice = wx.Choice(self, choices=available_actions)
        self.action_choice.SetSelection(0)

        # Create a button for choosing the folder
        self.folder_button = wx.Button(self, label="Open Folder")
        self.folder_button.Bind(wx.EVT_BUTTON, self.GetParent().on_open_folder)

        middle_sizer.Add(self.action_choice, 0, wx.EXPAND | wx.ALL, 5)
        middle_sizer.Add(self.folder_button, 0, wx.ALL | wx.RIGHT, 5)

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

        get_info_button = wx.Button(self, label="Get Ecu Info")
        get_info_button.Bind(wx.EVT_BUTTON, self.on_get_info)

        launch_logger_button = wx.Button(self, label="Start Logger")
        launch_logger_button.Bind(wx.EVT_BUTTON, self.on_start_logger)

        stop_logger_button = wx.Button(self, label="Stop Logger")
        stop_logger_button.Bind(wx.EVT_BUTTON, self.on_stop_logger)

        bottom_sizer.Add(get_info_button, 0, wx.ALL | wx.CENTER, 5)
        bottom_sizer.Add(flash_button, 0, wx.ALL | wx.CENTER, 5)
        bottom_sizer.Add(launch_logger_button, 0, wx.ALL | wx.CENTER, 5)
        bottom_sizer.Add(stop_logger_button, 0, wx.ALL | wx.CENTER, 5)

        main_sizer.Add(self.feedback_text, 0, wx.ALL | wx.EXPAND, 5)
        main_sizer.Add(middle_sizer)
        main_sizer.Add(self.list_ctrl, 0, wx.ALL | wx.EXPAND, 5)
        main_sizer.Add(self.progress_bar, 0, wx.EXPAND, 5)
        main_sizer.Add(bottom_sizer)
        self.SetSizer(main_sizer)

        if self.options["cal"] != "":
            self.update_bin_listing(self.options["cal"])

    def get_dlls_from_registry(self):

        interfaces = []

        BaseKey = winreg.OpenKeyEx(
            winreg.HKEY_LOCAL_MACHINE, r"Software\\PassThruSupport.04.04\\"
        )

        for i in range(winreg.QueryInfoKey(BaseKey)[0]):
            DeviceKey = winreg.OpenKeyEx(BaseKey, winreg.EnumKey(BaseKey, i))
            Name = winreg.QueryValueEx(DeviceKey, "Name")[0]
            FunctionLibrary = winreg.QueryValueEx(DeviceKey, "FunctionLibrary")[0]
            interfaces.append((Name, FunctionLibrary))
        return interfaces

    def on_get_info(self, event):
        ecu_info = flash_uds.read_ecu_data(
            self.flash_info,
            interface="J2534",
            callback=self.update_callback,
            interface_path=self.options["interface"],
        )

        [
            self.feedback_text.AppendText(did + " : " + ecu_info[did] + "\n")
            for did in ecu_info
        ]

    def on_flash(self, event):
        selected_file = self.list_ctrl.GetFirstSelected()
        logger.critical("Selected: " + str(self.row_obj_dict[selected_file]))

        if selected_file == -1:
            print("Select a file to flash")
        else:
            if self.action_choice.GetSelection() == 0:
                # We're expecting a bin file as input

                self.input_blocks = {}
                self.input_blocks[
                    self.row_obj_dict[selected_file]
                ] = constants.BlockData(
                    5, read_from_file(self.row_obj_dict[selected_file])
                )

                self.flash_bin()

            elif self.action_choice.GetSelection() == 1:
                # We're expecting a zip file as input
                with ZipFile(self.row_obj_dict[selected_file], "r") as zip_archive:
                    if "file_list.json" not in zip_archive.namelist():
                        self.feedback_text.AppendText(
                            "No file listing found in archive\n"
                        )

                    else:
                        with zip_archive.open("file_list.json") as file_list_json:
                            file_list = json.load(file_list_json)

                        self.input_blocks = {}
                        for filename in file_list:
                            self.feedback_text.AppendText(
                                str(filename)
                                + " will be flashed to block "
                                + str(file_list[filename])
                                + "\n"
                            )

                            self.input_blocks[filename] = simos_flash_utils.BlockData(
                                int(file_list[filename]), zip_archive.read(filename)
                            )

                        self.flash_bin(get_info=False)

    def on_start_logger(self, event):

        if self.hsl_logger is not None:
            return

        if self.options["logger"] == "":
            return

        self.hsl_logger = simos_hsl.hsl_logger(
            runserver=False,
            path=self.options["logger"] + "/",
            callback_function=self.update_callback,
            interface="J2534",
            singlecsv=self.options["singlecsv"],
            mode=self.options["logmode"],
            level=self.options["activitylevel"],
            interface_path=self.options["interface"],
        )

        logger_thread = threading.Thread(target=self.hsl_logger.start_logger)
        logger_thread.daemon = True
        logger_thread.start()

        return

    def on_stop_logger(self, event):

        if self.hsl_logger is not None:
            self.hsl_logger.stop()
            self.hsl_logger = None

    def update_bin_listing(self, folder_path):
        self.current_folder_path = folder_path
        self.list_ctrl.ClearAll()

        self.list_ctrl.InsertColumn(0, "Filename", width=500)
        self.list_ctrl.InsertColumn(1, "Modify Time", width=140)

        if self.action_choice.GetSelection() == 0:
            bins = glob.glob(folder_path + "/*.bin")
            self.options["cal"] = folder_path
        elif self.action_choice.GetSelection() == 1:
            bins = glob.glob(folder_path + "/*.zip")
            self.options["flashpacks"] = folder_path
        elif self.action_choice.GetSelection() == 2:
            bins = glob.glob(folder_path + "/*")
            self.options["logger"] = folder_path

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

    def flash_bin(self, get_info=True):

        if get_info:
            ecu_info = flash_uds.read_ecu_data(
                self.flash_info, interface="J2534", callback=self.update_callback
            )

            [
                self.feedback_text.AppendText(did + " : " + ecu_info[did] + "\n")
                for did in ecu_info
            ]

        else:
            ecu_info = None

        for filename in self.input_blocks:
            logger.info(
                "Executing flash_bin with the following blocks:\n"
                + "\n".join(
                    [
                        " : ".join(
                            [
                                filename,
                                str(self.input_blocks[filename].block_number),
                                constants.int_to_block_name[
                                    self.input_blocks[filename].block_number
                                ],
                                str(
                                    self.input_blocks[filename]
                                    .block_bytes[
                                        self.flash_info.software_version_location[
                                            self.input_blocks[filename].block_number
                                        ][
                                            0
                                        ] : self.flash_info.software_version_location[
                                            self.input_blocks[filename].block_number
                                        ][
                                            1
                                        ]
                                    ]
                                    .decode()
                                ),
                                str(
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
                                ),
                            ]
                        )
                        for filename in self.input_blocks
                    ]
                )
            )

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
            target=simos_flash_utils.flash_bin,
            args=(self.flash_info, self.input_blocks, self.update_callback, "J2534"),
        )
        flasher_thread.daemon = True
        flasher_thread.start()


class VW_Flash_Frame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title="VW_Flash GUI", size=(640, 750))
        self.create_menu()
        self.statusbar = self.CreateStatusBar(1)
        self.statusbar.SetStatusText("Choose a bin file directory")
        self.panel = FlashPanel(self)
        self.Show()

    def create_menu(self):
        menu_bar = wx.MenuBar()
        file_menu = wx.Menu()
        open_folder_menu_item = file_menu.Append(
            wx.ID_ANY, "Open Folder", "Open a folder with bins"
        )
        select_interface_menu_item = file_menu.Append(
            wx.ID_ANY, "Select Interface", "Select a CAN or PassThru Interface"
        )
        menu_bar.Append(file_menu, "&File")
        self.Bind(
            event=wx.EVT_MENU, handler=self.on_open_folder, source=open_folder_menu_item
        )
        self.Bind(
            event=wx.EVT_MENU,
            handler=self.on_select_interface,
            source=select_interface_menu_item,
        )
        self.SetMenuBar(menu_bar)

    def on_open_folder(self, event):
        title = "Choose a directory:"
        dlg = wx.DirDialog(self, title, style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.panel.update_bin_listing(dlg.GetPath())
        dlg.Destroy()

    def on_select_interface(self, event):
        interfaces = []
        for i in range(len(self.panel.interfaces)):
            interfaces.append(self.panel.interfaces[i][0])
        dlg = wx.SingleChoiceDialog(
            self, "Select an Interface", "Select an interface", interfaces
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.panel.paths["interface"] = self.panel.interfaces[dlg.GetSelection()][1]
            logger.info("User selected: " + self.panel.paths["interface"])
        dlg.Destroy()


if __name__ == "__main__":
    app = wx.App(False)
    frame = VW_Flash_Frame()
    app.MainLoop()
