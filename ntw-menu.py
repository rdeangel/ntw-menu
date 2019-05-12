#!/usr/bin/env python3

import configparser
import os
import sys
import subprocess
import shelve
import time
import numpy as np
import csv
from termenu import ansi
import termenu

"""
ntw-menu - version 1.4

This is a small terminal network session menu.                 

Written by Rocco De Angelis
"""

def load_menu(list_values, banner, menu_lev, cursor, scroll, subtitle,
    filter, filter_text, clear_menu, min_term_width, min_term_height,
    user_memory, user_selection_memory, shelf):
    width_size, height_size = termenu.get_terminal_size()
    height=(height_size - min_term_height)
    
    if (width_size > min_term_width) and (height_size > min_term_height):
        if filter:
            (selected_value, menu_lev, cursor,
            scroll, filter_text) = termenu.Termenu(
                list_values, menu_lev, cursor, scroll, filter_text,
                height, width_size, user_memory,
                user_selection_memory, shelf,
                plugins=[termenu.TitlePyfigletPlugin(
                    banner, subtitle, clear_menu),
                termenu.ColourPlugin(),
                termenu.FilterPlugin(filter_text,cursor,scroll)]).show()
        else:
            (selected_value, menu_lev, cursor,
            scroll, filter_text) = termenu.Termenu(
                list_values, menu_lev, cursor, scroll, filter_text,
                height, width_size, user_memory,
                user_selection_memory, shelf,
                plugins=[termenu.TitlePyfigletPlugin(
                    banner, subtitle, clear_menu),
                termenu.ColourPlugin()]).show()
    else:
        raise Exception("Error: terminal size is too small to display menu")
    return selected_value, menu_lev, cursor, scroll, filter_text

def counter(seconds):
    countdown = seconds
    ansi.hide_cursor()
    while countdown != 0:
        ansi.write(str(countdown))
        ansi.back()
        countdown-=1
        time.sleep(1)

def open_terminal_session(conn_proto, conn_port, user, host, 
    back_to_menu_timer, connection_timeout):
    user_required_msg = ("A username needs to be supplied for an ssh "
        + "connection.")
    back_to_menu_msg = "Returning to ntw-menu..... "
    enter_user_msg = "Enter username:\n"
    timer = back_to_menu_timer
    timeout = connection_timeout
    
    ansi.up(1)
    if conn_proto == "ssh":
        ansi.write(enter_user_msg)
        user = input()

        if conn_port == "":
            conn_port = "22"        
        if user == "":
            ansi.write(user_required_msg + "\n" + back_to_menu_msg)
            counter(timer)
            return 2
        else:
            conn_cli = (conn_proto + " -o ConnectTimeout=" + str(timeout)
                + " -o StrictHostKeyChecking=no -p " + conn_port + " -l "
                + user + " " + host)
            ansi.write("Connecting: " + conn_cli + "\n")
            subprocess.call(conn_cli, shell=True)
            ansi.write(back_to_menu_msg)
            counter(timer)
            return 1
    elif conn_proto == "telnet":
        if conn_port == "":
            conn_port = "23"
        conn_cli = conn_proto + " " + host + " " + conn_port
        ansi.write("Connecting: " + conn_cli + "\n")
        subprocess.call(conn_cli, shell=True)
        ansi.write(back_to_menu_msg)
        counter(timer)
        return 1
    elif conn_proto == "ftp":
        if conn_port == "":
            conn_port = "21"
        conn_cli = conn_proto + " -nv " + host + " " + conn_port
        ansi.write("Connecting: " + conn_cli + "\n")
        subprocess.call(conn_cli, shell=True)
        ansi.write(back_to_menu_msg)
        counter(timer)
        return 1
    elif conn_proto == "sftp":
        ansi.write(enter_user_msg)
        user = input()
        if conn_port == "":
            conn_port = "22"
        if user == "":
            ansi.write(user_required_msg + "\n" + back_to_menu_msg)
            counter(timer)
            return 2
        else:
            conn_cli = (conn_proto + " -o StrictHostKeyChecking=no "
                + "-o ConnectTimeout=" + str(timeout) + " -P "
                + conn_port + " " + user + "@" + host)
            ansi.write("Connecting: " + conn_cli + "\n")
            subprocess.call(conn_cli, shell=True)
            ansi.write(back_to_menu_msg)
            counter(timer)
            return 1
    else:
        return 2
    ansi.clear_screen()

def main():
    #fix variable assignment
    display_menu = True
    back_to_menu_timer = 0
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
    conn_proto_list = ["ssh", "telnet", "sftp", "ftp"]
    connection_timeout = 0
    user = ""
    #user cache directory and files
    user_cache_directory = os.path.join(str(os.getenv("HOME")),
    ".ntw-menu")
    shelve_file = os.path.join(str(os.getenv("HOME")),
    ".ntw-menu", "shelf")
    no_memory_file = os.path.join(str(os.getenv("HOME")),
    ".ntw-menu", "no_mem")
    
    #create user cache directory if it doesn't exist
    if not os.path.exists(user_cache_directory):
        os.makedirs(user_cache_directory)

    #define and read config file
    config_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),"config.ini")
    try:
        config = configparser.ConfigParser()
        config.read(config_file)

        #load config files setting
        banner = (config["MENU_PARAMETERS"]
            ["Banner"])
        min_term_width = int(config["MENU_PARAMETERS"]
            ["Min_Term_Width"])
        min_term_height = int(config["MENU_PARAMETERS"]
            ["Min_Term_Height"])
        back_to_menu_timer = int(config["MENU_PARAMETERS"]
            ["Back_To_Menu_Timer"])
        connection_timeout = int(config["MENU_PARAMETERS"]
            ["Connection_Timeout"])
        static_dev_list = (config["DATA_PARAMETERS"]
            ["Static_Device_List_File"])
        import_dev_list = (config["DATA_PARAMETERS"]
            ["Import_Device_List_File"])
        user_memory = (config["SESSION_MEMORY_PARAMETERS"]
            ["User_Memory"])
        if user_memory == "True":
            user_memory = True
        else:
            user_memory = False
        user_selection_memory = (config["SESSION_MEMORY_PARAMETERS"]
            ["user_selection_memory"])
        if user_selection_memory == "True":
            user_selection_memory = True
        else:
            user_selection_memory = False
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
        print("No data file has been configured to show a device list menu!")
        sys.exit(0)

    #load data from static data file into a numpy array
    static_dev_list_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), static_dev_list)
    if os.path.isfile(static_dev_list_file):
        try:
            static_list_data = np.loadtxt(static_dev_list_file, 
                dtype=str, delimiter=",", skiprows=int(1))       
        except:
            load_error = ("Error: it is not possible to correctly load "
                + "data from file: " + static_dev_list_file + "\n")
            print(load_error)
            static_list_data = np.array([static_list_data])

    #load data from imported data file into a numpy array
    import_dev_list_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), import_dev_list)
    if os.path.isfile(import_dev_list_file):
        try:
            import_list_data = np.loadtxt(import_dev_list_file, 
                dtype=str, delimiter=",", skiprows=int(1))
        except:
            load_error = ("Error: it is not possible to correctly load "
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
        dev_list_data = np.concatenate(
            (import_list_data, static_list_data), axis=0)
    elif static_list_data.size != 0:
        dev_list_data = static_list_data
    elif import_list_data.size != 0:
        dev_list_data = import_list_data

    #deals with no data, single entry, or multiple entries in device
    #list data files
    if len(dev_list_data) == 0:
        print("Error Loading device list data, no data in data files")
    elif dev_list_data.ndim == 1:
        if dev_list_data[2] != "":
            if dev_list_data[3] != "":
                dev_list_dic_name = (dev_list_data[0] + " - " 
                    + dev_list_data[1] + " [" + dev_list_data[2]
                    + ":" + dev_list_data[3] + "]")
                devicedict[dev_list_dic_name] = [dev_list_data[1]]
            else:
                dev_list_dic_name = (dev_list_data[0] + " - " 
                    + dev_list_data[1] + " - " 
                    + dev_list_data[2])
                devicedict[dev_list_dic_name] = [dev_list_data[1]]
        elif dev_list_data[2] == "":
            dev_list_dic_name = (dev_list_data[0] + " - " 
                + dev_list_data[1])
            devicedict[dev_list_dic_name] = [dev_list_data[1]]
        list_devices = sorted(list(devicedict))
    else:
        for i in range(len(dev_list_data)):
            if dev_list_data[i][2] != "":
                if dev_list_data[i][3] != "":
                    if dev_list_data[i][0] not in devicedict:
                        dev_list_dic_name = (dev_list_data[i][0] + " - " 
                            + dev_list_data[i][1] + " ["
                            + dev_list_data[i][2] 
                            + ":" + dev_list_data[i][3] + "]")
                        devicedict[dev_list_dic_name] = []
                    dev_list_dic_name = (dev_list_data[i][0] + " - " 
                        + dev_list_data[i][1] + " ["
                        + dev_list_data[i][2] 
                        + ":" + dev_list_data[i][3] + "]")
                    devicedict[dev_list_dic_name].append(
                            [dev_list_data[i][1],
                                dev_list_data[i][2],dev_list_data[i][3]])
                else:
                    if dev_list_data[i][0] not in devicedict:
                        dev_list_dic_name = (dev_list_data[i][0] + " - " 
                            + dev_list_data[i][1] + " ["
                            + dev_list_data[i][2] + "]")
                        devicedict[dev_list_dic_name]= []
                    dev_list_dic_name = (dev_list_data[i][0] + " - " 
                        + dev_list_data[i][1] + " ["
                        + dev_list_data[i][2] + "]")
                    devicedict[dev_list_dic_name].append(
                            [dev_list_data[i][1],
                                dev_list_data[i][2],dev_list_data[i][3]])
            elif dev_list_data[i][2] == "":
                if dev_list_data[i][0] not in devicedict:
                    dev_list_dic_name = (dev_list_data[i][0] + " - " 
                        + dev_list_data[i][1])
                    devicedict[dev_list_dic_name]= []
                dev_list_dic_name = (dev_list_data[i][0] + ' - ' 
                    + dev_list_data[i][1])
                devicedict[dev_list_dic_name].append(
                        [dev_list_data[i][1],
                        dev_list_data[i][2],dev_list_data[i][3]])
        list_devices = sorted(list(devicedict))

    if os.path.exists(no_memory_file):
        user_memory = False
        
    #Check if user_memory is used
    if user_memory:
        if not (os.path.exists(shelve_file) or
            os.path.exists(shelve_file + ".db")):
            dev_cursor = 0
            dev_scroll = 0
            proto_cursor = 0
            proto_scroll = 0
            dev_filter = None
            proto_filter = None
            shelf_store = shelve.open(shelve_file)
            shelf_store['dev_cursor'] = dev_cursor
            shelf_store['dev_scroll'] = dev_scroll
            shelf_store['proto_cursor'] = proto_cursor
            shelf_store['proto_scroll'] = proto_scroll
            shelf_store['dev_filter'] = dev_filter
            shelf_store['proto_filter'] = proto_filter
            shelf_store.close()
        else:
            shelf_store = shelve.open(shelve_file)
            dev_cursor = shelf_store['dev_cursor']
            dev_scroll = shelf_store['dev_scroll']
            proto_cursor = shelf_store['proto_cursor']
            proto_scroll = shelf_store['proto_scroll']
            dev_filter = shelf_store['dev_filter']
            proto_filter = shelf_store['proto_filter']
            shelf_store.close()
    else:
        dev_cursor = 0
        dev_scroll = 0
        proto_cursor = 0
        proto_scroll = 0
        dev_filter = None
        proto_filter = None

    ansi.clear_screen()
    while display_menu == True:
        try:
            #Device Session List Menu Level
            if menu_lev == 1:
                termenu.Termenu.clear_full_menu()
                if list_devices:
                    (device_selected, menu_lev, dev_cursor,
                    dev_scroll, dev_filter) = load_menu(
                        list_devices, banner,
                        1, dev_cursor, dev_scroll, "Device Sessions",
                        True, dev_filter, True,
                        min_term_width, min_term_height, user_memory,
                        user_selection_memory, shelve_file
                    )
                    if menu_lev == 0:
                        pass
                    if menu_lev == (100 or 101):
                        break
                    if menu_lev == 102:
                        menu_lev = 1
                        continue
                    else:
                        menu_lev+=1
                        
                    if device_selected:
                        session_selected = [
                            devicedict[device_selected][0][0],
                            devicedict[device_selected][0][1],
                            devicedict[device_selected][0][2]
                        ]
                        host_selected = str(session_selected[0])
                        conn_proto_preselected = str(session_selected[1])
                        conn_port = str(session_selected[2])                  
                        if (conn_proto_preselected in conn_proto_list
                            and host_selected != ""):
                            menu_lev = 0
                        if (conn_proto_preselected == "" 
                            and host_selected != "" and menu_lev == 0):
                            menu_lev = 2
                        elif host_selected == "" and menu_lev == 1:
                            menu_lev = 100
            #Device Connection Protocol Level
            if menu_lev == 2:
                termenu.Termenu.clear_full_menu()
                if session_selected:
                    (conn_proto_selected, menu_lev, proto_cursor,
                    proto_scroll, proto_filter) = load_menu(
                        conn_proto_list, banner,
                        2, proto_cursor, proto_scroll,
                        "Session Protocols for "
                        + host_selected,
                        False, proto_filter, False,
                        min_term_width, min_term_height, user_memory,
                        user_selection_memory, shelve_file
                    )
                    if menu_lev == 100:
                        break
                    if menu_lev > 1:
                        menu_lev = open_terminal_session(
                            conn_proto_selected,
                            conn_port, user,
                            host_selected,
                            back_to_menu_timer,
                            connection_timeout
                        )
                else:
                    menu_lev = 1
            if menu_lev == 0:
                menu_lev = open_terminal_session(
                    conn_proto_preselected,
                    conn_port, user,
                    host_selected,
                    back_to_menu_timer,
                    connection_timeout
                )
            session_selected = False
            if menu_lev == 101:
                break
            if menu_lev == 102:
                menu_lev = 1
                continue
        except ValueError as e:
            termenu.Termenu.clear_full_menu() 
            print("ValueError exception: " + str(e))
            sys.exit(0)
        except TypeError as e:
            termenu.Termenu.clear_full_menu()  
            print("TypeError exception: " + str(e))
            sys.exit(0)
        except AttributeError as e:
            termenu.Termenu.clear_full_menu()  
            print("AttributeError exception: " + str(e))
            sys.exit(0)
        except Exception as e:
            termenu.Termenu.clear_full_menu()  
            print("Exception: " + str(e))
            sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    #reset terminal and exit on Ctrl-C
    except KeyboardInterrupt:
        ansi.back(10)
        ansi.clear_screen()
        ansi.write("ntw-menu - Exited with CTRL-C\n")
        os.system("reset")
        ansi.show_cursor()
        sys.exit(0)
