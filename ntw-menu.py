#!/usr/bin/env python3

import configparser
import os
import sys
import subprocess
import time
import numpy as np
import csv
from termenu import ansi
import termenu

"""
ntw-menu - version 1.0

This is a terminal network menu.

Written by Rocco De Angelis
"""

def load_menu(list_values,banner,menu_lev,subtitle,filter,clear_menu,
    min_term_width,min_term_height):
    width_size, height_size = termenu.get_terminal_size()
    if (width_size > min_term_width) and (height_size > min_term_height):
        if filter:
            selected_value, menu_lev = termenu.Termenu(list_values, menu_lev,
                height=(height_size - min_term_height), width=width_size, 
                multiselect=False,
                plugins=[termenu.TitlePyfigletPlugin(
                    banner,subtitle,clear_menu),
                termenu.ColourPlugin(),termenu.FilterPlugin()]).show()
        else:
            selected_value, menu_lev = termenu.Termenu(list_values, menu_lev,
                height=(height_size - min_term_height), width=width_size, 
                multiselect=False,
                plugins=[termenu.TitlePyfigletPlugin(
                    banner,subtitle,clear_menu),
                termenu.ColourPlugin()]).show()
    else:
        raise Exception("Error: terminal size is too small to display menu")
    return selected_value, menu_lev

def counter(seconds):
    countdown = seconds
    ansi.hide_cursor()
    while countdown != 0:
        ansi.write(str(countdown))
        ansi.back()
        countdown-=1
        time.sleep(1)

def open_terminal_session(conn_proto, user, host):
    user_required_msg = ("A username needs to be supplied for an ssh "
        + "connection.")
    back_to_menu_msg = "Returning to ntw-menu..... "
    enter_user_msg = "Enter username:\n"
    
    ansi.up(1)
    if conn_proto == "ssh":
        ansi.write(enter_user_msg)
        user = input()
        if user == "":
            ansi.write(user_required_msg + "\n" + back_to_menu_msg)
            counter(3)
            return 2
        else:
            conn_cli = (conn_proto + " -o ConnectTimeout=5 "
                + "-o StrictHostKeyChecking=no -l " + user + " " + host)
            ansi.write("Connecting: " + conn_cli + "\n")
            subprocess.call(conn_cli, shell=True)
            ansi.write(back_to_menu_msg)
            counter(3)
            return 1
    elif conn_proto == "telnet":
        conn_cli = conn_proto + " " + host
        ansi.write("Connecting: " + conn_cli + "\n")
        subprocess.call(conn_cli, shell=True)
        ansi.write(back_to_menu_msg)
        counter(3)
        return 1
    elif conn_proto == "ftp":
        conn_cli = conn_proto + " -nv " + host
        ansi.write("Connecting: " + conn_cli + "\n")
        subprocess.call(conn_cli, shell=True)
        ansi.write(back_to_menu_msg)
        counter(3)
        return 1
    elif conn_proto == "sftp":
        ansi.write(enter_user_msg)
        user = input()
        if user == "":
            ansi.write(user_required_msg + "\n" + back_to_menu_msg)
            counter(3)
            return 2
        else:
            conn_cli = (conn_proto + " -o StrictHostKeyChecking=no "
                + "-o ConnectTimeout=5 " + user + "@" + host)
            ansi.write("Connecting: " + conn_cli + "\n")
            subprocess.call(conn_cli, shell=True)
            ansi.write(back_to_menu_msg)
            counter(3)
            return 1
    else:
        return 2
    ansi.clear_screen()

def main():
    #fix variable assignment
    display_menu = True
    static_dev_list_file = ""
    static_list_data = np.array([])
    import_dev_list_file = ""
    import_list_data = np.array([])
    menu_lev = 1
    devicedict = {}
    list_devices = []
    session_selected = False
    device_selected = False
    dev_list_file_presence = 2
    conn_proto = ["ssh", "telnet", "sftp", "ftp"]
    user = ""

    #define and read config file
    config_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),"config.ini")
    try:
        config = configparser.ConfigParser()
        config.read(config_file)

        #load config files setting
        banner = config["MENU_PARAMETERS"]["Banner"]
        min_term_width = int(config["MENU_PARAMETERS"]["Min_Term_Width"])
        min_term_height = int(config["MENU_PARAMETERS"]["Min_Term_Height"])
        static_dev_list = (config["DATA_PARAMETERS"]
            ["Static_Device_List_File"])
        import_dev_list = (config["DATA_PARAMETERS"]
            ["Import_Device_List_File"])
    except:
        print("Error: it is not possible to read config from file: "
        + config_file)
        sys.exit(0)

    #deal with empty settings
    if not banner:
        banner = "NTW Menu"
    if not min_term_width:
        min_term_width = 50
    if not min_term_height:
        min_term_height = 10
    if not static_dev_list:
        static_dev_list = ""
        dev_list_file_presence-=1
    if not import_dev_list:
        import_dev_list = ""
        dev_list_file_presence-=1

    if dev_list_file_presence == 0:
        print("No data file has been configured to show a menu!")
        sys.exit(0)

    #load data from static data file into a numpy array
    static_dev_list_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),static_dev_list)
    if os.path.isfile(static_dev_list_file):
        try:
            static_list_data = np.loadtxt(static_dev_list_file, 
                dtype=str, delimiter=",", skiprows=int(1))       
        except:
            load_error = ("Error: it is not possible to correctly load job "
                + "data from file: " + static_dev_list_file + "\n")
            print(load_error)
            static_list_data = np.array([static_list_data])

    #load data from imported data file into a numpy array
    import_dev_list_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),import_dev_list)
    if os.path.isfile(import_dev_list_file):
        try:
            import_list_data = np.loadtxt(import_dev_list_file, 
                dtype=str, delimiter=",", skiprows=int(1))
        except:
            load_error = ("Error: it is not possible to correctly load job "
                + "data from file: " + import_dev_list_file + "\n")
            print(load_error)
            import_list_data = np.array([import_list_data])
    
    if not (os.path.isfile(static_dev_list_file)
        or os.path.isfile(import_dev_list_file)):
        print("No device list file exist, ntw-menu won't be able to load.")
        sys.exit(0)

    #check if the device list files have a value
    if static_list_data.size != 0:
        if isinstance(static_list_data[0], str):
            static_list_data = np.array([static_list_data])
    if import_list_data.size != 0:
        if isinstance(import_list_data[0], str):
            import_list_data = np.array([import_list_data])

    #merge imported file and static device list file
    if static_list_data.size >= 1 and import_list_data.size >= 1:
        dev_list_data = np.concatenate((import_list_data,static_list_data),
            axis=0)
    elif static_list_data.size != 0:
        dev_list_data = static_list_data
    elif import_list_data.size != 0:
        dev_list_data = import_list_data

    #deal with no data, single entry, or multiple entries in device
    #list data files
    if len(dev_list_data) == 0:
        print("Error Loading device list data, no data in data files")
    elif dev_list_data.ndim == 1:
        devicedict[(dev_list_data[0] + " - " 
        + dev_list_data[1])] = [dev_list_data[1]]
        list_devices = sorted(list(devicedict))
    else:
        for i in range(len(dev_list_data)):
            if dev_list_data[i][0] not in devicedict:
                devicedict[(dev_list_data[i][0] + " - " 
                    + dev_list_data[i][1])] = []
            devicedict[(dev_list_data[i][0] + " - " 
                + dev_list_data[i][1])].append(dev_list_data[i][1])
        list_devices = sorted(list(devicedict))

    ansi.clear_screen()
    while display_menu == True:
        try:
            #Device Session List Menu Level
            if menu_lev == 1:
                termenu.Termenu.clear_full_menu()
                if list_devices:
                    device_selected, menu_lev = load_menu(
                        list_devices,banner,
                        1, "List of Device Sessions",
                        True,True,
                        min_term_width,min_term_height
                    )
                    menu_lev+=1
                    if device_selected:
                            list_addresses = []
                            if (len(devicedict[device_selected])) > 1:
                                for i in range(
                                    len(devicedict[device_selected])
                                ):
                                    list_addresses.append(
                                        devicedict[device_selected][i])
                            else:
                                list_addresses = [
                                    devicedict[device_selected][0]
                                ]
                            session_selected = list_addresses[0]
            #Device Connection Protocol Level
            if menu_lev == 2:
                termenu.Termenu.clear_full_menu()
                if session_selected:
                        conn_proto_selected, menu_lev = load_menu(
                            conn_proto,banner,
                            2,
                            "List connection protocols for address "
                            + session_selected,
                            False,False,
                            min_term_width,min_term_height
                        )
                        if menu_lev == 100:
                            break
                        if menu_lev != 1:
                            menu_lev = open_terminal_session(
                                conn_proto_selected,
                                user,
                                session_selected
                            )
                else:
                    menu_lev = 1
            session_selected = False
            if menu_lev == 101:
                break
        except ValueError as e:
            termenu.Termenu.clear_full_menu() 
            #print("ValueError exception: " + str(e))
            #sys.exit(0)
        except TypeError as e:
            termenu.Termenu.clear_full_menu()  
            #print("TypeError exception: " + str(e))
            #sys.exit(0)
        except AttributeError as e:
            termenu.Termenu.clear_full_menu()  
            #print("AttributeError exception: " + str(e))
            #sys.exit(0)
        except Exception as e:
            termenu.Termenu.clear_full_menu()  
            print("Exception: " + str(e))
            sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    #reset terminal and exit on Ctrl-C
    except KeyboardInterrupt:
        ansi.clear_screen()
        ansi.write("ntw-menu - Exited with CTRL-C\n")
        os.system("reset")
        sys.exit(0)
