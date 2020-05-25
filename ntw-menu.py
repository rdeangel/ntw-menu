#!/usr/bin/env python3

import warnings
import configparser
import os
import sys
import subprocess
import shelve
import time
import numpy as np
import csv
import getopt
import colortest
from termenu import ansi
from termenu import keyboard
import termenu

version = "1.4.9.9.9.3_beta"

"""
ntw-menu is a terminal session network menu written in python3.                 

Author: Rocco De Angelis
"""

def is_int(astring):
    #checks if the given string is an integer
    try: int(astring)
    except ValueError: return False
    else: return True

def load_menu(list_values, title_text, menu_lev, cursor, scroll, subtitle,
    filter, filter_text, clear_menu, min_term_width, min_term_height,
    user_mem, shelf, menu_color, user_config_file):
    width_size, height_size = termenu.get_terminal_size()
    height=(height_size - min_term_height)

    if (width_size >= min_term_width) and (height_size >= min_term_height):
        if filter:
            (selected_value, menu_lev, cursor,
                scroll, filter_text) = termenu.Termenu(
                list_values, menu_lev, cursor, scroll, filter_text,
                height, width_size, user_mem,
                shelf, menu_color, user_config_file,
                plugins=[termenu.ColourPlugin(),
                termenu.TitlePyfigletPlugin(
                    title_text, subtitle, clear_menu, menu_color),
                termenu.FilterPlugin(filter_text,cursor,scroll,menu_color)]).show()
        else:
            (selected_value, menu_lev, cursor,
                scroll, filter_text) = termenu.Termenu(
                list_values, menu_lev, cursor, scroll, filter_text,
                height, width_size, user_mem,
                shelf, menu_color, user_config_file,
                plugins=[termenu.TitlePyfigletPlugin(
                    title_text, subtitle, clear_menu, menu_color),
                termenu.ColourPlugin()]).show()
    else:
        print("Error: terminal size is too small to display menu")
        sys.exit(0)
    return selected_value, menu_lev, cursor, scroll, filter_text

def counter(seconds, txt_color, background, bright_text=False):
    countdown = seconds
    ansi.hide_cursor()
    while countdown != 0:
        for key in keyboard.keyboard_listener(0):
            ansi.write(ansi.colorize(str(countdown), txt_color, background, bright_text))
            ansi.back()
            countdown-=1
            time.sleep(1)
            if countdown == 0:
                break
    ansi.back(30)
    ansi.clear_eol()
    ansi.reset_cursor_color()

def protocol_session(conn_cli, txt_color, session_color, text_bg, 
    txt_bright, open_colorize, back_to_menu_msg, timer):
    ansi.write(ansi.colorize("Connecting: " + conn_cli + "\n", txt_color, 
        text_bg, txt_bright, open_colorize))
    ansi.change_cursor_color(session_color)
    ansi.write(ansi.colorize("\0", session_color, text_bg, txt_bright, open_colorize))
    subprocess.call(conn_cli, shell=True)

def open_terminal_session(conn_proto, conn_port, user, host, 
    back_to_menu_timer, connection_timeout, menu_color):
    back_to_menu_msg = "Returning to ntw-menu... "
    enter_user_msg = "Enter username:\n"
    timer = back_to_menu_timer
    timeout = connection_timeout
    txt_color = menu_color['text_color']
    session_color = menu_color['session_color']
    txt_bright = menu_color['bright_text']
    text_bg = ""
    protocolo_session_run = False

    if session_color == "":
        open_colorize = False
        txt_color = ""
        txt_bright = False
    else:
        open_colorize = True
        txt_color = session_color

    ansi.up(1)

    if conn_proto == "ssh":
        ansi.write(ansi.colorize(enter_user_msg, txt_color, text_bg, txt_bright, open_colorize))
        user = input()
        if conn_port == "":
            conn_port = "22"        
        if user != "":
            conn_cli = (conn_proto + " -o ConnectTimeout=" + str(timeout)
                + " -o StrictHostKeyChecking=no -p " + conn_port + " -l "
                + user + " " + host)
            protocolo_session_run = True
    elif conn_proto == "telnet":
        if conn_port == "":
            conn_port = "23"
        conn_cli = conn_proto + " " + host + " " + conn_port
        protocolo_session_run = True
    elif conn_proto == "ftp":
        if conn_port == "":
            conn_port = "21"
        conn_cli = conn_proto + " -nv " + host + " " + conn_port
        protocolo_session_run = True
    elif conn_proto == "sftp":
        ansi.write(ansi.colorize(enter_user_msg, txt_color, text_bg, txt_bright, open_colorize))   
        user = input()
        if conn_port == "":
            conn_port = "22"
        if user != "":
            conn_cli = (conn_proto + " -o StrictHostKeyChecking=no "
                + "-o ConnectTimeout=" + str(timeout) + " -P "
                + conn_port + " " + user + "@" + host)
            protocolo_session_run = True
    if protocolo_session_run:
        protocol_session(conn_cli, txt_color, session_color, text_bg,
            txt_bright, open_colorize, back_to_menu_msg, timer)
        if timer > 0:
            ansi.write(ansi.colorize(back_to_menu_msg, txt_color, text_bg, txt_bright))
            counter(timer, txt_color, text_bg, txt_bright)
        else:
            ansi.write(ansi.colorize(back_to_menu_msg + "\nPress Enter to continue...", txt_color, 
                text_bg, txt_bright))
            for key in keyboard.keyboard_listener(None):
                if key == "enter":
                    break
        for i in range(2):
            ansi.up()
            ansi.back(30)
            ansi.clear_eol()
        termenu.Termenu.clear_full_menu(clear_screen=True)
        return 1
    else:
        user_required_msg = ("A username needs to be supplied for an %s "
            + "connection.") % conn_proto
        if timer > 0:
            ansi.write(ansi.colorize(user_required_msg + "\n" + back_to_menu_msg, txt_color, 
                text_bg, txt_bright))
            counter(timer, txt_color, text_bg, txt_bright)
        else:
            ansi.write(ansi.colorize(user_required_msg + "\nPress Enter to continue...", txt_color, 
                text_bg, txt_bright))
            for key in keyboard.keyboard_listener(None):
                if key == "enter":
                    break
        for i in range(2):
            ansi.up()
            ansi.back(30)
            ansi.clear_eol()
        termenu.Termenu.clear_full_menu(clear_screen=False)
        return 1

def validate_preset(color_preset,preset_num):
    if not ansi.is_color_valid(color_preset[0]): # checks title_color
        print("Error: color_preset_{0} <Title_Color> is incorrecly defined in config file".format(preset_num))
        sys.exit(0)
    if not ansi.is_color_valid(color_preset[1]):
        print("Error: color_preset_{0} <Text_Color> is incorrecly defined in config file".format(preset_num))
        sys.exit(0)
    if not ((ansi.is_color_valid(color_preset[2]) and ansi.is_color_valid(color_preset[3]))
        and (is_int(color_preset[2]) == is_int(color_preset[3]))):
        print("Error: color_preset_{0} <Text_Active> | <Text_Active_Bg> combination is incorrecly defined in config file".format(preset_num))
        sys.exit(0)
    if color_preset[5] is not "":
        if not ((ansi.is_color_valid(color_preset[4]) and ansi.is_color_valid(color_preset[5]))
            and (is_int(str(color_preset[4])) == is_int(str(color_preset[5])))):
            print("Error: color_preset_{0} <Filter_Color> | <Filter_Color_Bg> combination is incorrecly defined in config file".format(preset_num))
            sys.exit(0)
    else:
        if not ansi.is_color_valid(color_preset[4]):
            print("Error: color_preset_{0} <Filter_Color> value is incorrecly defined in config file".format(preset_num))
            sys.exit(0)
    if not ansi.is_color_valid(color_preset[6]):
        print("Error: color_preset_{0} <Session_Color> value is incorrecly defined in config file".format(preset_num))
        sys.exit(0)
    if (color_preset[7] != "") and (color_preset[8] != ""):
        if not ((ansi.is_hex_color_valid(color_preset[7]) and ansi.is_hex_color_valid(color_preset[8]))):
            print("Error: color_preset_{0} <Cursor_Color> | <Cursor_Exit_Color> combination is incorrecly defined in config file".format(preset_num))
            sys.exit(0)
    if (color_preset[9] != "") and (color_preset[10] != ""):
        if not ((ansi.is_hex_color_valid(color_preset[9]) and ansi.is_hex_color_valid(color_preset[10]))):
            print("Error: color_preset_{0} <Screen_Color> | <Screen_Exit_Color> combination is incorrecly defined in config file".format(preset_num))
            sys.exit(0)
    if color_preset[11] != "True" and color_preset[11] != "False":
        print("Error: color_preset_{0} <Bright_Text> value is incorrectly defined in config file".format(preset_num))
        sys.exit(0)

def main(argv):

    global g_cursor_exit_color, g_screen_exit_color

    #initial variable assignment
    display_menu = True
    back_to_menu_timer = 0
    static_dev_list = ""
    static_dev_list_file = ""
    static_list_data = np.array([])
    import_dev_list = ""
    import_dev_list_file = ""
    import_list_data = np.array([])
    user_dev_list = ""
    user_dev_list_file = ""
    user_list_data = np.array([])
    data_mode = 0
    menu_lev = 1
    devicedict = {}
    list_devices = []
    session_selected = False
    device_selected = False
    dev_list_file_presence = 3
    conn_proto_list = ["ssh", "telnet", "sftp", "ftp"]
    connection_timeout = 0
    config_file_opt = ""
    config_file_arg = False
    menu_color_arg = False
    title_text = ""
    title_text_arg = False
    title_text_opt = ""
    screen_color_arg = False
    text_color_opt = ""
    text_active_opt = ""
    text_active_bg_opt = ""
    menu_color = dict()
    usr_menu_color = dict()
    title_color = "231"
    title_color_opt = ""
    title_color_arg = False
    text_color = "231"
    text_active = "21"
    text_active_bg = "231"
    filter_color = "231"
    filter_color_opt = ""
    filter_color_bg_opt = ""
    filter_color_arg = False
    filter_color_bg = ""
    session_color = ""
    session_color_opt = ""
    session_color_arg = False
    cursor_color = ""
    cursor_color_opt = ""
    cursor_exit_color_opt = ""
    cursor_color_arg = False
    cursor_exit_color = ""
    screen_color = ""
    screen_color_opt = ""
    screen_exit_color = ""
    screen_exit_color_opt = ""
    bright_text_arg = False
    bright_text = False
    bright_text_opt = False
    default_preset = "231,231,21,231,231,,,,,,,False"
    min_term_width_opt = ""
    min_term_width_arg = False
    min_term_height_opt = ""
    min_term_height_arg = False
    back_to_menu_timer_opt = ""
    back_to_menu_timer_arg = False
    connection_timeout_opt = ""
    connection_timeout_arg = False
    user_config_file_opt = ""
    user_config_file_arg = False
    data_mode_opt = ""
    data_mode_arg = False
    user_dev_list_opt = ""
    user_dev_list_arg = False
    user_mem_opt = ""
    user_mem_arg = False
    write_opt = ""
    write_arg = False
    reset_arg = False
    write_to_file = False

    user = ""

    #define and read config file
    config_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),"config.ini")
    #user cache directory and config files
    user_directory = os.path.join(str(os.getenv("HOME")),
        ".ntw-menu")
    shelve_file = os.path.join(str(os.getenv("HOME")),
        ".ntw-menu", "default.dat")
    #no_mem file option deprecated
    no_memory_file = os.path.join(str(os.getenv("HOME")),
        ".ntw-menu", "no_mem")
    user_config_file = os.path.join(str(os.getenv("HOME")),
        ".ntw-menu", "user_config.ini")
    init_user_dev_list_file = os.path.join(str(os.getenv("HOME")),
        ".ntw-menu", "user_dev_list.csv")

    main_name = os.path.basename(__file__)

    arg_help = '''ntw-menu version %s 

Usage: %s [OPTION]...

  -c  --config-file         full path and/or filname of ntw-menu config file
  -m  --menu-color          * menu colors defined as <Text_Color>,<Text_Active>,<Text_Active_Bg>
  -s, --session-color       * protocol sessions color sepcified as <Session_Color>
      --title-text          text of menu title to diplay at the top of the menu as <Title_Text>
      --title-color         * title menu color override as <Title_Color>
  -f, --filter-color        * filter text color specified as <Filter_Color>,<Filter_Color_Bg>
      --cursor-color        ** cursor color specified as <Cursor_Color>,<Cursor_Exit_Color>
      --screen-color        ** screen color specified as <Screen_Color>,<Screen_Exit_Color>
                            1. 0011FF
                               example: 000000,FFFFFF
                            2. black,white,red,green,blue,brown,gray,magenta,cyan
                               example: black,white
  -b, --bright-off          ** forces ANSI bright text Off
  -B, --bright-on           ** forces ANSI bright text On
      --min-term-width      minimum terminal width size
      --min-term-height     mininmum terminal height size
      --back-to-menu-timer  back to menu timer in seconds (default 0 no timer)
      --connection-timeout  protocol session timeout in seconds
  -d, --data-mode           data mode (possible value range: 0-2)
                            0: main data files merge only
                            1: merge main data files with user data file
                            2: user data file only
  -u, --user-config-file    full path and/or filename for user config file
      --user-dev-list-file  full path and/or filename of user csv data file (see --data-mode)
      --user-mem-on         enables selection and filter memory across menu sessions
      --user-mem-off        disables selection and filter memory across menu sessions
  -t, --color-table         display/test ansi 256 color table
  -w, --write               saves user specified settings in $HOME/.ntw-menu/user_config.ini
  -r, --reset               reset user_config.ini file back to default
  -k, --key-mapping         display keyboard help to navigate use ntw-menu
  -h, --help                display help

*ANSI Color valid values
----------------------------------------------------------
1. 0-255 
   example: -m 111,22,23
2. default,black,white,red,green,yellow,blue,magenta,cyan
   example: -m green,red,yellow

use: -t|--colortable to lookup available colors and how
     they look in your terminal application
----------------------------------------------------------

**this option does not work with all terminals

''' % (version,main_name)

    try:
        opts, args = getopt.getopt(argv,"c:m:s:f:d:u:bBtwrkh", [
            "config-file",
            "menu-color=",
            "session-color=",
            "title-text=",
            "title-color=",
            "filter-color=",
            "cursor-color=",
            "screen-color=",
            "bright-off",
            "bright-on",
            "min-term-width=",
            "min-term-height=",
            "back-to-menu-timer=",
            "connection-timeout=",
            "data-mode=",
            "user-config-file=",
            "user-dev-list-file=",
            "user-mem-on",
            "user-mem-off",
            "color-table",
            "write",
            "reset",
            "key-mapping",
            "help",])
    except getopt.GetoptError:
        print (arg_help)
        sys.exit(0)


    key_functions = '''
####################################################################################
#                          NTW-MENU - KEYBOARD MAPPING                             #
####################################################################################
# ALPHANUMERIC + SYMBOL KEYS = use to filter device list                           #
# ENTER = select a menu option and move to the next menu or input                  #
# ESC = move to previous menu or reset filter                                      #
# CTRL-B or PAGE-UP = scroll up                                                    #
# CTRL-F or PAGE-DOWN = scroll down                                                #
# CTRL-R = refresh menu                                                            #
# CTRL-E = exit (not while in a device session)                                    #
# CTRL-C = forced exit (not while in a device session)                             #
####################################################################################

####################################################################################
#             FULL XTERM KEY AND ANSI 256 COLOR TERMINAL SUPPORT ONLY              #
####################################################################################
# SHIFT-F1 = randomizes all menu/session color parameters at once                  #
# SHIFT-F2 = changes menu text and session colors only                             #
# SHIFT-F3 = changes selection color and filter simultaneously and randomly        #
# SHIFT-F4 = changes selection text color and filter simultaneously and randomly   #
# SHIFT-F5 = changes selection active only (background and text) randomly          #
# SHIFT-F6 = changes selection active only (text only) randomly                    #
# SHIFT-F7 = changes filter background and text (if background is set)             #
# SHIFT-F8 = changes filter color (text only)                                      #
# SHIFT-F9 = switches filter background color on and off                           #
# SHIFT-F11 = switches bright text on and off                                      #
# SHIFT-F12 = saves current menu color as menu and session defaults                #
# ALT-SHIFT-F1/F12 = loads saved color presets from user config file               #
# CTRL-ALT-SHIFT-F1/F12 = saves color presets to user config file                  #
####################################################################################
'''

    #Extract and set arguments and options
    for opt, arg in opts:
        if opt in ("-c", "--config-file"):
            config_file_opt = arg
            config_file_opt = os.path.abspath(config_file_opt)
            config_file_arg = True
        elif opt in ("-m", "--menu-color"):
            try:
                text_color_opt, text_active_opt, text_active_bg_opt = arg.split(",")
                menu_color_arg = True
            except ValueError:
                print("Argument Error -m --menu-color: "
                    "three valid text or integer values required")
        elif opt in ("-s", "--session-color"):
            session_color_opt = arg
            session_color_arg = True
        elif opt in ("-f", "--filter-color"):
            try:
                filter_color_opt, filter_color_bg_opt = arg.split(",")
                filter_color_arg = True
            except ValueError:
                print("Argument Error -f --filter-color: "
                    "two valid text or integer values required")
                sys.exit(0)
        elif opt in ("-b", "--bright-off"):
            bright_text_opt = False
            bright_text_arg = True
        elif opt in ("-B", "--bright-on"):
            bright_text_opt = True
            bright_text_arg = True
        elif opt in ("-d", "--data-mode"):
            try:
                data_mode_opt = int(arg)
                if 0 <= data_mode_opt  <= 2:
                    data_mode_arg = True
                else:
                    raise ValueError
            except ValueError:
                print("Argument Error -d, --data-mode: " +
                    "a numeric value between 0 and 2 is required")
                sys.exit(0)
        elif opt in ("-u", "--user-config-file"):
            user_config_file_opt = arg
            user_config_file_opt = os.path.abspath(user_config_file_opt)
            user_config_file_arg = True
        elif opt in ("-t", "--color-table"):
            ansi.clear_screen()
            colortest.table()
            sys.exit(0)
        elif opt in ("-w", "--write"):
            write_arg = True
        elif opt in ("-r", "--reset"):
            reset_arg = True
        elif opt in ("-k", "--key-mapping"):
            print (key_functions)
            sys.exit(0)
        elif opt in ("-h", "--help"):
            print (arg_help)
            sys.exit(0)
        elif opt in ("--title-text"):
            title_text_opt = arg
            title_text_arg = True
        elif opt in ("--title-color"):
            title_color_opt = arg
            title_color_arg = True
        elif opt in ("--cursor-color"):
            try:
                cursor_color_opt, cursor_exit_color_opt = arg.split(",")
                if cursor_color_opt[0] != "#" and cursor_color_opt[0].isdigit():
                    cursor_color_opt = "#" + cursor_color_opt
                if cursor_exit_color_opt[0] != "#" and cursor_exit_color_opt[0].isdigit():
                    cursor_exit_color_opt  = "#" + cursor_exit_color_opt 
                cursor_color_arg = True
            except ValueError:
                print("Argument Error --cursor-color: " +
                    "two comma separated values required")
                sys.exit(0)
        elif opt in ("--screen-color"):
            try:
                screen_color_opt, screen_exit_color_opt = arg.split(",")
                if screen_color_opt[0] != "#" and screen_color_opt[0].isdigit():
                    screen_color_opt = "#" + screen_color_opt
                if screen_exit_color_opt[0] != "#" and screen_exit_color_opt[0].isdigit():
                    screen_exit_color_opt  = "#" + screen_exit_color_opt 
                screen_color_arg = True
            except ValueError:
                print("Argument Error --screen-color: " +
                    "two comma separated values required")
                sys.exit(0)
        elif opt in ("--min-term-width"):
            try:
                min_term_width_opt = int(arg)
                if min_term_width_opt >= 50:
                    min_term_width_arg = True
                else:
                    raise ValueError
            except ValueError:
                print("Argument Error --min-term-width: " +
                    "a numeric value higher than or equal to 50 is required")
                sys.exit(0)
        elif opt in ("--min-term-height"):
            try:
                min_term_height_opt = int(arg)
                if min_term_height_opt >= 11:
                    min_term_height_arg = True
                else:
                    raise ValueError
            except ValueError:
                print("Argument Error --min-term-height: " +
                    "a numeric value higher than or equal to 11 is required")
                sys.exit(0)
        elif opt in ("--back-to-menu-timer"):
            try:
                back_to_menu_timer_opt = int(arg)
                if back_to_menu_timer_opt <= 9:
                    back_to_menu_timer_arg = True
                else:
                    raise ValueError
            except ValueError:
                print("Argument Error --back-to-menu-timer: " +
                    "numeric value between 0 and 9 is required")
                sys.exit(0)
        elif opt in ("--connection-timeout"):
            try:
                connection_timeout_opt = int(arg)
                if connection_timeout_opt >= 0:
                    connection_timeout_arg = True
                else:
                    raise ValueError
            except ValueError:
                print("Argument Error --connection-timeout: " +
                    "a positive numeric value is required")
                sys.exit(0)
        elif opt in ("--user-dev-list-file"):
            user_dev_list_opt = arg
            user_dev_list_opt = os.path.abspath(user_dev_list_opt)
            user_dev_list_arg = True
        elif opt in ("--user-mem-on"):
            user_mem_opt = True
            user_mem_arg = True
        elif opt in ("--user-mem-off"):
            user_mem_opt = False
            user_mem_arg = True

    #create user cache directory if it doesn't exist
    if not os.path.exists(user_directory):
        os.makedirs(user_directory)


    #change default user config file if it is pass via argument
    if config_file_arg:
        config_file = config_file_opt
    try:
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(config_file)

        #load config files setting
        title_text = (config['MENU_PARAMETERS']
            ['Title_Text'])
        min_term_width = (config['MENU_PARAMETERS']
            ['Min_Term_Width'])
        if min_term_width:
            if is_int(min_term_width):
                min_term_width = int(min_term_width)
            else:
                print("Error: <Min_Term_Width> has to be an integer value")
                sys.exit(0)
        min_term_height = (config['MENU_PARAMETERS']
            ['Min_Term_Height'])
        if min_term_height:
            if is_int(min_term_height):
                min_term_height = int(min_term_height)
            else:
                print("Error: <Min_Term_Height> has to be an integer value")
                sys.exit(0)
        back_to_menu_timer = (config['MENU_PARAMETERS']
            ['Back_To_Menu_Timer'])
        if back_to_menu_timer:
            if is_int(back_to_menu_timer):
                back_to_menu_timer = int(back_to_menu_timer)
            else:
                print("Error: <Back_To_Menu_Timer> has to be an integer value")
                sys.exit(0)
        connection_timeout = (config['MENU_PARAMETERS']
            ['Connection_Timeout'])
        if connection_timeout:
            if is_int(connection_timeout):
                connection_timeout = int(connection_timeout)
            else:
                print("Error: <Connection_Timeout> has to be an integer value")
                sys.exit(0)
        menu_color['title_color'] = (config['MENU_COLORS']
            ['Title_Color'])
        menu_color['text_color'] = (config['MENU_COLORS']
            ['Text_Color'])
        menu_color['text_active'] = (config['MENU_COLORS']
            ['Text_Active'])
        menu_color['text_active_bg'] = (config['MENU_COLORS']
            ['Text_Active_Bg'])
        menu_color['filter_color'] = (config['MENU_COLORS']
            ['Filter_Color'])
        menu_color['filter_color_bg'] = (config['MENU_COLORS']
            ['Filter_Color_Bg'])
        menu_color['session_color'] = (config['MENU_COLORS']
            ['Session_Color'])
        menu_color['cursor_color'] = (config['MENU_COLORS']
            ['Cursor_Color'])
        menu_color['cursor_exit_color'] = (config['MENU_COLORS']
            ['Cursor_Exit_Color'])
        menu_color['screen_color'] = (config['MENU_COLORS']
            ['Screen_Color'])
        menu_color['screen_exit_color'] = (config['MENU_COLORS']
            ['Screen_Exit_Color'])
        menu_color['bright_text'] = (config['MENU_COLORS']
            ['Bright_Text'])
        menu_color['color_preset_1'] = (config['MENU_COLORS']
            ['Color_Preset_1'])
        menu_color['color_preset_2'] = (config['MENU_COLORS']
            ['Color_Preset_2'])
        menu_color['color_preset_3'] = (config['MENU_COLORS']
            ['Color_Preset_3'])
        menu_color['color_preset_4'] = (config['MENU_COLORS']
            ['Color_Preset_4'])
        menu_color['color_preset_5'] = (config['MENU_COLORS']
            ['Color_Preset_5'])
        menu_color['color_preset_6'] = (config['MENU_COLORS']
            ['Color_Preset_6'])
        menu_color['color_preset_7'] = (config['MENU_COLORS']
            ['Color_Preset_7'])
        menu_color['color_preset_8'] = (config['MENU_COLORS']
            ['Color_Preset_8'])
        menu_color['color_preset_9'] = (config['MENU_COLORS']
            ['Color_Preset_9'])
        menu_color['color_preset_10'] = (config['MENU_COLORS']
            ['Color_Preset_10'])
        menu_color['color_preset_11'] = (config['MENU_COLORS']
            ['Color_Preset_11'])
        menu_color['color_preset_12'] = (config['MENU_COLORS']
            ['Color_Preset_12'])
        static_dev_list = (config['DATA_PARAMETERS']
            ['Static_Dev_List_File'])
        import_dev_list = (config['DATA_PARAMETERS']
            ['Import_Dev_List_File'])
        user_mem = (config['SESSION_MEMORY_PARAMETERS']
            ['User_Mem'])
    except:
        print("Error: it is not possible to read config from file: "
        + config_file)
        sys.exit(0)
    g_cursor_exit_color = menu_color['cursor_exit_color']
    g_screen_exit_color = menu_color['screen_exit_color']

    #change default user config file if it is pass via argument
    if user_config_file_arg:
        user_config_file = user_config_file_opt
        #check if the directory for user_config_file exist if not create it
        if not os.path.exists(os.path.dirname(user_config_file)):
            os.makedirs(os.path.dirname(user_config_file), exist_ok=True)

    if not os.path.exists(user_config_file):
        try:
            if user_config_file_arg:
                '''if a user config file is specified create a user config file and
                and set user data file with similar name'''
                new_user_dev_list_file = (
                    (os.path.splitext(os.path.basename(user_config_file_opt))[0])
                    +(os.path.splitext(os.path.basename(init_user_dev_list_file))[1]))
                init_user_dev_list_file = os.path.join(
                    os.path.dirname(user_config_file_opt),new_user_dev_list_file)
            #else:
            #    new_user_dev_list_file = init_user_dev_list_file
            user_config_exist = False
            user_config = configparser.ConfigParser(allow_no_value=True)
            user_config.optionxform = str
            user_config.add_section('MENU_PARAMETERS')
            user_config['MENU_PARAMETERS']['Title_Text'] = ""
            user_config['MENU_PARAMETERS']['Min_Term_Width'] = ""
            user_config['MENU_PARAMETERS']['Min_Term_Height'] = ""
            user_config['MENU_PARAMETERS']['Back_To_Menu_Timer'] = ""
            user_config['MENU_PARAMETERS']['Connection_Timeout'] = ""
            user_config.add_section('MENU_COLORS')
            user_config['MENU_COLORS']['Title_Color'] = ""
            user_config['MENU_COLORS']['Text_Color'] = ""
            user_config['MENU_COLORS']['Text_Active'] = ""
            user_config['MENU_COLORS']['Text_Active_Bg'] = ""
            user_config['MENU_COLORS']['Filter_Color'] = ""
            user_config['MENU_COLORS']['Filter_Color_Bg'] = ""
            user_config['MENU_COLORS']['Session_Color'] = ""
            user_config['MENU_COLORS']['Cursor_Color'] = ""
            user_config['MENU_COLORS']['Cursor_Exit_Color'] = ""
            user_config['MENU_COLORS']['Screen_Color'] = ""
            user_config['MENU_COLORS']['Screen_Exit_Color'] = ""
            user_config['MENU_COLORS']['Bright_Text'] = ""
            user_config['MENU_COLORS']['Color_Preset_1'] = ""
            user_config['MENU_COLORS']['Color_Preset_2'] = ""
            user_config['MENU_COLORS']['Color_Preset_3'] = ""
            user_config['MENU_COLORS']['Color_Preset_4'] = ""
            user_config['MENU_COLORS']['Color_Preset_5'] = ""
            user_config['MENU_COLORS']['Color_Preset_6'] = ""
            user_config['MENU_COLORS']['Color_Preset_7'] = ""
            user_config['MENU_COLORS']['Color_Preset_8'] = ""
            user_config['MENU_COLORS']['Color_Preset_9'] = ""
            user_config['MENU_COLORS']['Color_Preset_10'] = ""
            user_config['MENU_COLORS']['Color_Preset_11'] = ""
            user_config['MENU_COLORS']['Color_Preset_12'] = ""
            user_config.add_section('DATA_PARAMETERS')
            user_config['DATA_PARAMETERS']['Data_Mode'] = "0"
            user_config['DATA_PARAMETERS']['User_Dev_List_File'] = init_user_dev_list_file
            user_config.add_section('SESSION_MEMORY_PARAMETERS')
            user_config['SESSION_MEMORY_PARAMETERS']['User_Mem'] = ""

            #write user config file in $HOME/.ntw-menu/user_config.ini
            with open(user_config_file, 'w') as usr_write_file:
                user_config.write(usr_write_file)
        
            #when creating a config file check if a user data file doesn't already exist
            if not os.path.isfile(init_user_dev_list_file):
                #if it doesn't create the file in $HOME/.ntw-menu/user_dev_list.csv 
                f_user_dev_list = open(init_user_dev_list_file, "w")
                f_user_dev_list.write("#Edit this file to load user specific device sessions "
                    + "using \"Data_Mode\" = 1 or 2.\n"
                    + "Device 1 Sample in " + init_user_dev_list_file  + ",192.168.1.1,,\n"
                    + "Device 2 Sample in " + init_user_dev_list_file  + ",192.168.1.2,,\n")
                f_user_dev_list.close()
        except:
            print("Error: it is not possible to write config to file: "
            + user_config_file)
            sys.exit(0)

    #check if the user_config.ini file exists
    i=0
    for i in range(2):
        if os.path.exists(user_config_file) and (not reset_arg):
            user_config_exist = True
            try:
                user_config = configparser.ConfigParser(allow_no_value=True)
                user_config.read(user_config_file)
                usr_title_text = (user_config['MENU_PARAMETERS']
                    ['Title_Text'])
                usr_min_term_width = (user_config['MENU_PARAMETERS']
                    ['Min_Term_Width'])
                usr_min_term_height = (user_config['MENU_PARAMETERS']
                    ['Min_Term_Height'])
                usr_back_to_menu_timer = (user_config['MENU_PARAMETERS']
                    ['Back_To_Menu_Timer'])
                usr_connection_timeout = (user_config['MENU_PARAMETERS']
                    ['Connection_Timeout'])
                usr_menu_color['title_color'] = (user_config['MENU_COLORS']
                    ['Title_Color'])
                usr_menu_color['text_color'] = (user_config['MENU_COLORS']
                    ['Text_Color'])
                usr_menu_color['text_active'] = (user_config['MENU_COLORS']
                    ['Text_Active'])
                usr_menu_color['text_active_bg'] = (user_config['MENU_COLORS']
                    ['Text_Active_Bg'])
                usr_menu_color['filter_color'] = (user_config['MENU_COLORS']
                    ['Filter_Color'])
                usr_menu_color['filter_color_bg'] = (user_config['MENU_COLORS']
                    ['Filter_Color_Bg'])
                usr_menu_color['session_color'] = (user_config['MENU_COLORS']
                    ['Session_Color'])
                usr_menu_color['cursor_color'] = (user_config['MENU_COLORS']
                    ['Cursor_Color'])
                usr_menu_color['cursor_exit_color'] = (user_config['MENU_COLORS']
                    ['Cursor_Exit_Color'])
                usr_menu_color['screen_color'] = (user_config['MENU_COLORS']
                    ['Screen_Color'])
                usr_menu_color['screen_exit_color'] = (user_config['MENU_COLORS']
                    ['Screen_Exit_Color'])
                usr_menu_color['bright_text'] = (user_config['MENU_COLORS']
                    ['Bright_Text'])
                usr_data_mode = (user_config['DATA_PARAMETERS']
                    ['Data_Mode'])
                usr_user_dev_list = (user_config['DATA_PARAMETERS']
                    ['User_Dev_List_File'])
                usr_user_mem = (user_config['SESSION_MEMORY_PARAMETERS']
                    ['User_Mem'])
                if usr_title_text:
                    title_text = usr_title_text
                if usr_min_term_width:
                    if is_int(usr_min_term_width):
                        min_term_width = int(usr_min_term_width)
                    else:
                        print("Error: <Min_Term_Width> has to be an integer value")
                        sys.exit(0)
                if usr_min_term_height:
                    if is_int(usr_min_term_height):
                        min_term_height = int(usr_min_term_height)
                    else:
                        print("Error: <Min_Term_Height> has to be an integer value")
                        sys.exit(0)
                if usr_back_to_menu_timer:
                    if is_int(usr_back_to_menu_timer):
                        back_to_menu_timer = int(usr_back_to_menu_timer)
                    else:
                        print("Error: <Back_To_Menu_Timer> has to be an integer value")
                        sys.exit(0)
                if usr_connection_timeout:
                    if is_int(usr_connection_timeout):
                        connection_timeout = int(usr_connection_timeout)
                    else:
                        print("Error: <Connection_Timeout> has to be an integer value")
                        sys.exit(0)
                if usr_menu_color['title_color']:
                    menu_color['title_color'] = usr_menu_color['title_color']
                if usr_menu_color['text_color']:
                    menu_color['text_color'] = usr_menu_color['text_color']
                if usr_menu_color['text_active']:
                    menu_color['text_active'] = usr_menu_color['text_active']
                if usr_menu_color['text_active_bg']:
                    menu_color['text_active_bg'] = usr_menu_color['text_active_bg']
                if usr_menu_color['filter_color']:
                    menu_color['filter_color'] = usr_menu_color['filter_color']
                if usr_menu_color['filter_color_bg']:
                    menu_color['filter_color_bg'] = usr_menu_color['filter_color_bg']
                if usr_menu_color['session_color']:
                    menu_color['session_color'] = usr_menu_color['session_color']
                if usr_menu_color['cursor_color']:
                    menu_color['cursor_color'] = usr_menu_color['cursor_color']
                if usr_menu_color['cursor_exit_color']:
                    menu_color['cursor_exit_color']= usr_menu_color['cursor_exit_color']
                if usr_menu_color['screen_color']:
                    menu_color['screen_color'] = usr_menu_color['screen_color']
                if usr_menu_color['screen_exit_color']:
                    menu_color['screen_exit_color']= usr_menu_color['screen_exit_color']
                if usr_menu_color['bright_text']:
                    menu_color['bright_text'] = usr_menu_color['bright_text']
                if usr_data_mode:
                    if is_int(usr_data_mode):
                        data_mode = int(usr_data_mode)
                    else:
                        print("Error: <Usr_Data_Mode> has to be an integer value")
                        sys.exit(0)
                else:
                    data_mode = 0
                if usr_user_dev_list:
                    user_dev_list = usr_user_dev_list
                else:
                    user_dev_list = False
                if usr_user_mem:
                    user_mem =  usr_user_mem 
            except:
                print("Error: it is not possible to read config from file: "
                + user_config_file)
                sys.exit(0)
        elif os.path.exists(user_config_file) and reset_arg:
            try:
                user_config = configparser.ConfigParser(defaults=None, allow_no_value=False,
                    strict=True)
                user_config.optionxform = str
                user_config.read(user_config_file)
                user_config.set('MENU_PARAMETERS', 'Title_Text', '')
                user_config.set('MENU_PARAMETERS', 'Min_Term_Width', '')
                user_config.set('MENU_PARAMETERS', 'Min_Term_Height', '')
                user_config.set('MENU_PARAMETERS', 'Back_To_Menu_Timer', '')
                user_config.set('MENU_PARAMETERS', 'Connection_Timeout', '')
                user_config.set('MENU_COLORS', 'Title_Color', '')
                user_config.set('MENU_COLORS', 'Text_Color', '')
                user_config.set('MENU_COLORS', 'Text_Active', '')
                user_config.set('MENU_COLORS', 'Text_Active_Bg', '')
                user_config.set('MENU_COLORS', 'Filter_Color', '')
                user_config.set('MENU_COLORS', 'Filter_Color_Bg', '')
                user_config.set('MENU_COLORS', 'Session_Color', '')
                user_config.set('MENU_COLORS', 'Cursor_Color', '')
                user_config.set('MENU_COLORS', 'Cursor_Exit_Color', '')
                user_config.set('MENU_COLORS', 'Screen_Color', '')
                user_config.set('MENU_COLORS', 'Screen_Exit_Color', '')
                user_config.set('MENU_COLORS', 'Bright_Text', '')
                user_config.set('MENU_COLORS', 'Color_Preset_1', '')
                user_config.set('MENU_COLORS', 'Color_Preset_2', '')
                user_config.set('MENU_COLORS', 'Color_Preset_3', '')
                user_config.set('MENU_COLORS', 'Color_Preset_4', '')
                user_config.set('MENU_COLORS', 'Color_Preset_5', '')
                user_config.set('MENU_COLORS', 'Color_Preset_6', '')
                user_config.set('MENU_COLORS', 'Color_Preset_7', '')
                user_config.set('MENU_COLORS', 'Color_Preset_8', '')
                user_config.set('MENU_COLORS', 'Color_Preset_9', '')
                user_config.set('MENU_COLORS', 'Color_Preset_10', '')
                user_config.set('MENU_COLORS', 'Color_Preset_11', '')
                user_config.set('MENU_COLORS', 'Color_Preset_12', '')
                user_config.set('SESSION_MEMORY_PARAMETERS', 'User_Mem', '')
                with open(user_config_file, 'w') as usr_write_file:
                    user_config.write(usr_write_file)
            except:
                print("issue with saving")
            reset_arg = False

    if menu_color['bright_text'] == "True":
        menu_color['bright_text'] = True
    elif menu_color['bright_text'] == "False":
         menu_color['bright_text'] = False
    if user_mem == "True":
        user_mem = True
    elif user_mem == "False":
        user_mem = False

    #validate preset values
    for preset_num in range(1,12):
        color_preset = eval(
            "menu_color['color_preset_{0}'].split(',')".format(preset_num))
        validate_preset(color_preset,preset_num)

    if menu_color_arg:
        menu_color['title_color'] = text_color_opt
        menu_color['text_color'] = text_color_opt
        menu_color['text_active'] = text_active_opt
        menu_color['text_active_bg'] = text_active_bg_opt
        menu_color['filter_color'] = text_color_opt
        menu_color['filter_color_bg'] = ""
        menu_color['session_color'] = ""
        menu_color['cursor_color'] = ""
        menu_color['cursor_exit_color'] = ""
        menu_color['screen_color'] = ""
        menu_color['screen_exit_color'] = ""
        menu_color['bright_text'] = False
    else:
        if menu_color['title_color'] == "":
            menu_color['title_color'] = title_color
        if menu_color['text_color'] == "":
            menu_color['text_color'] = text_color
        if menu_color['text_active'] == "":
            menu_color['text_active'] = text_active
        if menu_color['text_active_bg'] == "":
            menu_color['text_active_bg'] = text_active_bg
        if menu_color['filter_color'] == "":
            menu_color['filter_color'] = filter_color
        if menu_color['filter_color_bg'] == "":
            menu_color['filter_color_bg'] = filter_color_bg
        if menu_color['session_color'] == "":
            menu_color['session_color'] = session_color
        if menu_color['cursor_color'] == "":
            menu_color['cursor_color'] = cursor_color
        if menu_color['cursor_exit_color'] == "":
            menu_color['cursor_exit_color'] = cursor_exit_color
        if menu_color['screen_color'] == "":
            menu_color['screen_color'] = screen_color
        if menu_color['screen_exit_color'] == "":
            menu_color['screen_exit_color'] = screen_exit_color

    #argument option override if set
    if title_text_arg:
        title_text = title_text_opt
    if title_color_arg:
        menu_color['title_color'] = title_color_opt
    if filter_color_arg:
        menu_color['filter_color'] = filter_color_opt
        menu_color['filter_color_bg'] = filter_color_bg_opt
    if cursor_color_arg:
        menu_color['cursor_color'] = cursor_color_opt
        menu_color['cursor_exit_color'] = cursor_exit_color_opt
    if min_term_width_arg:
        min_term_width = min_term_width_opt
    if min_term_height_arg:
        min_term_height = min_term_height_opt
    if back_to_menu_timer_arg:
        back_to_menu_timer = back_to_menu_timer_opt
    if connection_timeout_arg:
        connection_timeout = connection_timeout_opt
    if data_mode_arg:
        data_mode = data_mode_opt
    if user_dev_list_arg:
        user_dev_list = user_dev_list_opt
    if user_mem_arg:
        user_mem = user_mem_opt
    if bright_text_arg:
        menu_color['bright_text'] = bool(bright_text_opt)
    if session_color_arg:
        menu_color['session_color'] = session_color_opt
    if screen_color_arg:
        menu_color['screen_color'] = screen_color_opt
        menu_color['screen_exit_color'] = screen_exit_color_opt
        g_screen_exit_color = screen_exit_color

    #deal with empty settings
    if not title_text:
        title_text = "NTW Menu"
    if not min_term_width:
        min_term_width = 50
    if not min_term_height:
        min_term_height = 10
    if not menu_color['bright_text']:
        menu_color['bright_text'] = False
    if not user_mem:
        user_mem = False
    if not static_dev_list:
        static_dev_list = ""
        dev_list_file_presence-=1
    if not import_dev_list:
        import_dev_list = ""
        dev_list_file_presence-=1
    if not user_dev_list:
        user_dev_list = ""
        dev_list_file_presence-=1

    if dev_list_file_presence == 0:
        print("Error: No data file has been configured to show a device list menu!")
        sys.exit(0)

    #do color selection validation
    if not ansi.is_color_valid(menu_color['title_color']):
        print("Error: <Title_Color> value is incorrecly entered")
        sys.exit(0)
    if not ansi.is_color_valid(menu_color['text_color']):
        print("Error: <Text_Color> value is incorrecly entered")
        sys.exit(0)
    if not ((ansi.is_color_valid(menu_color['text_active']) and ansi.is_color_valid(menu_color['text_active_bg']))
        and (is_int(menu_color['text_active']) == is_int(menu_color['text_active_bg']))):
        print("Error: <Text_Active> | <Text_Active_Bg> value combination is incorrectly entered")
        sys.exit(0)
    if not ansi.is_color_valid(menu_color['session_color']):
        print("Error: <Session_Color> value is incorrecly entered")
        sys.exit(0)
    if menu_color['filter_color_bg'] is not "":
        if not ((ansi.is_color_valid(menu_color['filter_color']) and ansi.is_color_valid(menu_color['filter_color_bg']))
            and (is_int(str(menu_color['filter_color'])) == is_int(str(menu_color['filter_color_bg'])))):
            print("Error: <Filter_Color> | <Filter_Color_Bg> value combination is incorrectly entered")
            sys.exit(0)
    else:
        if not ansi.is_color_valid(menu_color['filter_color']):
            print("Error: <Filter_Color> value is incorrecly entered")
            sys.exit(0)
    if (menu_color['cursor_color'] != "") and (menu_color['cursor_exit_color'] != ""):
        if not ((ansi.is_hex_color_valid(menu_color['cursor_color']) and ansi.is_hex_color_valid(menu_color['cursor_exit_color']))):
            print("Error: <Cursor_Color> | <Cursor_Exit_Color> value/s is/are incorrectly entered")
            sys.exit(0)
    if (menu_color['screen_color'] != "") and (menu_color['screen_exit_color'] != ""):
        if not ((ansi.is_hex_color_valid(menu_color['screen_color']) and ansi.is_hex_color_valid(menu_color['screen_exit_color']))):
            print("Error: <Screen_Color> | <Screen_Exit_Color> value/s is/are incorrectly entered")
            sys.exit(0)

    if min_term_width < 50:
        print("Error: <Min_Term_Width> a positive numeric value higher than or equal to 50 is required")
        sys.exit(0)
    if min_term_height < 11:
        print("Error: <Min_Term_Height> a positive numeric value higher than or equal to 11 is required")
        sys.exit(0)
    if back_to_menu_timer > 9 or back_to_menu_timer < 0:
        print("Error: <Connection_Timeout> a positive numeric value lower than or equal to 9 is required")
        sys.exit(0)
    if connection_timeout < 0:
        print("Error: <Connection_Timeout> a positive numeric value is required")
        sys.exit(0)
    if not isinstance(menu_color['bright_text'], (bool)):
        print("Error: <Bright_Text> a boolean value of either True or False is required")
        sys.exit(0)
    if not isinstance(user_mem, (bool)):
        print("Error: <User_Mem> a boolean value of either True or False is required")
        sys.exit(0)

    #load data from static data file into a numpy array
    static_dev_list_file = os.path.join(
        os.path.dirname(os.path.realpath(config_file)), static_dev_list)
    if os.path.isfile(static_dev_list_file):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                static_list_data = np.loadtxt(static_dev_list_file,
                    dtype=str, delimiter=",", skiprows=int(1))
        except:
            load_error = ("Error: it is not possible to correctly load "
                + "data from file: " + static_dev_list_file + "\n")
            print(load_error)
            static_list_data = np.array([static_list_data])
            sys.exit(0)

    #load data from imported data file into a numpy array
    import_dev_list_file = os.path.join(
        os.path.dirname(os.path.realpath(config_file)), import_dev_list)
    if os.path.isfile(import_dev_list_file):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                import_list_data = np.loadtxt(import_dev_list_file,
                    dtype=str, delimiter=",", skiprows=int(1))
        except:
            load_error = ("Error: it is not possible to correctly load "
                + "data from file: " + import_dev_list_file + "\n")
            print(load_error)
            import_list_data = np.array([import_list_data])
            sys.exit(0)

    #load data from user data file into a numpy array
    user_dev_list_file = os.path.join(
        os.path.dirname(os.path.realpath(config_file)), user_dev_list)
    if os.path.isfile(user_dev_list_file):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                user_list_data = np.loadtxt(user_dev_list_file,
                    dtype=str, delimiter=",", skiprows=int(1))
        except:
            load_error = ("Error: it is not possible to correctly load "
                + "data from file: " + user_dev_list_file + "\n")
            print(load_error)
            user_list_data = np.array([user_list_data])
            sys.exit(0)

    #check if the device list files have a value
    if static_list_data.size != 0:
        if isinstance(static_list_data[0], str):
            static_list_data = np.array([static_list_data])
    if import_list_data.size != 0:
        if isinstance(import_list_data[0], str):
            import_list_data = np.array([import_list_data])
    if user_list_data.size != 0:
        if isinstance(user_list_data[0], str):
            user_list_data = np.array([user_list_data])
    #elif (static_list_data.size != 0) or (import_list_data.size != 0):
    #    data_mode = 0
    
    msg_no_values_present = ("Error: can't load device list, "
        + "one of the data file doesn't have any data to load.\n"
        + "try changing \"data_mode\" to the another value!")
    msg_no_device_list = ("Error: can't load device list, "
        + "one of the data file required is missing.\n"
        + "Try changing \"Data_Mode\" to the another value!")
    msg_device_file_short = ("Error: you need the device list .csv file "
        + "to be at least 4 characters long, excluding file extension.")

    #merge static, imported and user defined device list .csv files
    if data_mode == 0:
        if not (os.path.isfile(static_dev_list_file) or os.path.isfile(import_dev_list_file)):
            print(msg_no_device_list)
            sys.exit(0)
        if static_list_data.size > 0 and import_list_data.size > 0:
            if ((len(os.path.splitext(os.path.basename(static_dev_list_file))[0]) < 4) or 
                (len(os.path.splitext(os.path.basename(import_dev_list_file))[0]) < 4)):
                print(msg_device_file_short)
                sys.exit(0)
            dev_list_data = np.concatenate(
                (static_list_data, import_list_data), axis=0)
            dat_file_name = (os.path.splitext(os.path.basename(static_dev_list_file))[0][:3] + 
                os.path.splitext(os.path.basename(static_dev_list_file))[0][-1:] + "_" +
                os.path.splitext(os.path.basename(import_dev_list_file))[0][:3] +
                os.path.splitext(os.path.basename(import_dev_list_file))[0][-1:])
        elif static_list_data.size > 0:
            if (len(os.path.splitext(os.path.basename(static_dev_list_file))[0]) < 4):
                print(msg_device_file_short)
                sys.exit(0)
            dev_list_data = static_list_data
            dat_file_name = (os.path.splitext(os.path.basename(static_dev_list_file))[0])
        elif import_list_data.size > 0:
            if (len(os.path.splitext(os.path.basename(import_dev_list_file))[0]) < 4):
                print(msg_device_file_short)
                sys.exit(0)
            dev_list_data = import_list_data
            dat_file_name = (os.path.splitext(os.path.basename(import_dev_list_file))[0])
        else:
            print(msg_no_values_present)
            sys.exit(0)
    elif data_mode == 1:
        if not (((os.path.isfile(static_dev_list_file) or (os.path.isfile(import_dev_list_file)))
            and (os.path.isfile(user_dev_list_file)))):
            print(msg_no_device_list)
            sys.exit(0)
        if static_list_data.size > 0 and import_list_data.size > 0 and user_list_data.size > 0:
            if ((len(os.path.splitext(os.path.basename(static_dev_list_file))[0]) < 4) or 
                (len(os.path.splitext(os.path.basename(import_dev_list_file))[0]) < 4) or
                (len(os.path.splitext(os.path.basename(user_dev_list_file))[0]) < 4)):
                print(msg_device_file_short)
                sys.exit(0)
            dev_list_data = np.concatenate(
                (static_list_data, import_list_data, user_list_data), axis=0)
            dat_file_name = (os.path.splitext(os.path.basename(static_dev_list_file))[0][:3] + 
                os.path.splitext(os.path.basename(static_dev_list_file))[0][-1:] + "_" +
                os.path.splitext(os.path.basename(import_dev_list_file))[0][:3] +
                os.path.splitext(os.path.basename(import_dev_list_file))[0][-1:] + "_" +
                os.path.splitext(os.path.basename(user_dev_list_file))[0][:3] +
                os.path.splitext(os.path.basename(user_dev_list_file))[0][-1:])
        elif static_list_data.size > 0 and user_list_data.size > 0 :
            if ((len(os.path.splitext(os.path.basename(static_dev_list_file))[0]) < 4) or
                (len(os.path.splitext(os.path.basename(user_dev_list_file))[0]) < 4)):
                print(msg_device_file_short)
                sys.exit(0)
            dev_list_data = np.concatenate(
                (static_list_data, user_list_data), axis=0)
            dat_file_name = (os.path.splitext(os.path.basename(static_dev_list_file))[0][:3] + 
                os.path.splitext(os.path.basename(static_dev_list_file))[0][-1:] + "_" +
                os.path.splitext(os.path.basename(user_dev_list_file))[0][:3] +
                os.path.splitext(os.path.basename(user_dev_list_file))[0][-1:])
        elif import_list_data.size > 0 and user_list_data.size > 0 :
            if ((len(os.path.splitext(os.path.basename(import_dev_list_file))[0]) < 4) or
                (len(os.path.splitext(os.path.basename(user_dev_list_file))[0]) < 4)):
                print(msg_device_file_short)
                sys.exit(0)
            dev_list_data = np.concatenate(
                (import_list_data, user_list_data), axis=0)
            dat_file_name = (os.path.splitext(os.path.basename(import_dev_list_file))[0][:3] + 
                os.path.splitext(os.path.basename(import_dev_list_file))[0][-1:] + "_" +
                os.path.splitext(os.path.basename(user_dev_list_file))[0][:3] +
                os.path.splitext(os.path.basename(user_dev_list_file))[0][-1:])
        else:
            print(msg_no_values_present)
            sys.exit(0)
    elif data_mode == 2:
        if not (os.path.isfile(user_dev_list_file)):
            print(msg_no_device_list)
            sys.exit(0)
        if user_list_data.size > 0:
            if (len(os.path.splitext(os.path.basename(user_dev_list_file))[0]) < 4):
                print(msg_device_file_short)
                sys.exit(0)
            dev_list_data = user_list_data
            dat_file_name = (os.path.splitext(os.path.basename(user_dev_list_file))[0])
        else:
            print(msg_no_values_present)
            sys.exit(0)

    if os.path.dirname(user_config_file) != os.path.join(str(os.getenv("HOME")),".ntw-menu"):
        #define ntw-menu shelve .dat file to be used in specified user config folder
        shelve_file = os.path.join(str(os.path.dirname(user_config_file)),
            os.path.basename(dat_file_name) + ".dat")
    else:
        #define ntw-menu shelve .dat file to be used in default user config folder
        shelve_file = os.path.join(str(os.getenv("HOME")),
            ".ntw-menu", os.path.basename(dat_file_name) + ".dat")

    #deals with no data, single entry, or multiple entries in device
    #list data files
    if len(dev_list_data) == 0:
        print("Error: Unable to load device list data, no data in data files")
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
        i=0
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
        user_mem = False

    #Check if user_mem is used
    if user_mem:
        #If user memory shelve file or path doesn't exist then create it 
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
        #else read the existing file and parameters
        else:
            try:
                shelf_store = shelve.open(shelve_file)
                dev_cursor = shelf_store['dev_cursor']
                dev_scroll = shelf_store['dev_scroll']
                proto_cursor = shelf_store['proto_cursor']
                proto_scroll = shelf_store['proto_scroll']
                dev_filter = shelf_store['dev_filter']
                proto_filter = shelf_store['proto_filter']
                shelf_store.close()
            except KeyError:
                os.remove(shelve_file)
                print("Error: The user memory data file was corrupted and removed.\n" +
                    "Dat file removed: " + shelve_file)
                sys.exit(0)
    #else do not use user memory function
    else:
        dev_cursor = 0
        dev_scroll = 0
        proto_cursor = 0
        proto_scroll = 0
        dev_filter = None
        proto_filter = None

    try:
        user_config = configparser.ConfigParser(defaults="", allow_no_value=False,
            comment_prefixes=('#'), inline_comment_prefixes="", strict=True)
        user_config.optionxform = str
        user_config.read(user_config_file)
        if write_arg:
            if title_text_arg:
                user_config.set('MENU_PARAMETERS', 'Title_Text', title_text)
                write_to_file = True
            if min_term_width_arg:
                user_config.set('MENU_PARAMETERS', 'Min_Term_Width', str(min_term_width))
                write_to_file = True
            if min_term_height_arg:
                user_config.set('MENU_PARAMETERS', 'Min_Term_Height', str(min_term_height))
                write_to_file = True
            if back_to_menu_timer_arg:
                user_config.set('MENU_PARAMETERS', 'Back_To_Menu_Timer', str(back_to_menu_timer))
                write_to_file = True
            if connection_timeout_arg:
                user_config.set('MENU_PARAMETERS', 'Connection_Timeout', str(connection_timeout))
                write_to_file = True
            if menu_color_arg:
                user_config.set('MENU_COLORS', 'Title_Color', str(menu_color['title_color']))
                user_config.set('MENU_COLORS', 'Text_Color', str(menu_color['text_color']))
                user_config.set('MENU_COLORS', 'Text_Active', str(menu_color['text_active']))
                user_config.set('MENU_COLORS', 'Text_Active_Bg', str(menu_color['text_active_bg']))
                user_config.set('MENU_COLORS', 'Filter_Color', str(menu_color['filter_color']))
                write_to_file = True
            if title_color_arg:
                user_config.set('MENU_COLORS', 'Title_Color', str(menu_color['title_color']))
                write_to_file = True
            if filter_color_arg:
                user_config.set('MENU_COLORS', 'Filter_Color', str(menu_color['filter_color']))
                user_config.set('MENU_COLORS', 'Filter_Color_Bg', str(menu_color['filter_color_bg']))
                write_to_file = True
            if session_color_arg:
                user_config.set('MENU_COLORS', 'Session_Color', str(menu_color['session_color']))
                write_to_file = True
            if cursor_color_arg:
                user_config.set('MENU_COLORS', 'Cursor_Color', str(menu_color['cursor_color']))
                user_config.set('MENU_COLORS', 'Cursor_Exit_Color', str(menu_color['cursor_exit_color']))
                write_to_file = True
            if screen_color_arg:
                user_config.set('MENU_COLORS', 'Screen_Color', str(menu_color['screen_color']))
                user_config.set('MENU_COLORS', 'Screen_Exit_Color', str(menu_color['screen_exit_color']))
                write_to_file = True
            if bright_text_arg:
                user_config.set('MENU_COLORS', 'Bright_Text', str(menu_color['bright_text']))
                write_to_file = True
            if data_mode_arg:
                user_config.set('DATA_PARAMETERS', 'Data_Mode', str(data_mode))
                write_to_file = True
            if user_dev_list_arg:
                user_config.set('DATA_PARAMETERS', 'User_Dev_List_File', user_dev_list)
                write_to_file = True
            if user_mem_arg:
                user_config.set('SESSION_MEMORY_PARAMETERS','User_Mem', str(user_mem))
                write_to_file = True
        if write_to_file:
            with open(user_config_file, 'w') as user_config_file:
                user_config.write(user_config_file)
    except:
        print("issue with saving")

    width_size, height_size = termenu.get_terminal_size()
    termenu.Termenu.clear_full_menu(clear_screen=True)
    ansi.change_screen_color(menu_color['screen_color'])
    while display_menu == True:
        try:
            #Device Session List Menu Level
            if menu_lev == 1:
                termenu.Termenu.clear_full_menu(clear_screen=False)
                if list_devices:
                    (device_selected, menu_lev, dev_cursor,
                    dev_scroll, dev_filter) = load_menu(
                        list_devices, title_text,
                        1, dev_cursor, dev_scroll, "Device Sessions",
                        True, dev_filter, True,
                        min_term_width, min_term_height, user_mem,
                        shelve_file, menu_color, user_config_file
                    )
                    if menu_lev == (100):
                        ansi.change_cursor_color(menu_color['cursor_exit_color'])
                        ansi.change_screen_color(menu_color['screen_exit_color'])
                        break
                    if menu_lev == 101:
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
                #If a session with no defined protocols is selected load the protocol menu
                if session_selected:
                    (conn_proto_selected, menu_lev, proto_cursor,
                    proto_scroll, proto_filter) = load_menu(
                        conn_proto_list, title_text,
                        2, proto_cursor, proto_scroll,
                        "Session Protocols for "
                        + host_selected,
                        False, proto_filter, False,
                        min_term_width, min_term_height, user_mem,
                        shelve_file, menu_color, user_config_file
                    )
                    #Reset pre-set default cursor and screen color when exiting
                    if menu_lev == 100:
                        for i in range(0, height_size):
                            ansi.clear_eol()
                            ansi.up()
                        ansi.change_cursor_color(menu_color['cursor_exit_color'])
                        ansi.change_screen_color(menu_color['screen_exit_color'])
                        break
                    #Refresh protocol menu on ctrl_r
                    if menu_lev == 102:
                        menu_lev = 2
                        continue
                    #Open terminal session selected
                    if menu_lev > 1:
                        menu_lev = open_terminal_session(
                            conn_proto_selected,
                            conn_port, user,
                            host_selected,
                            back_to_menu_timer,
                            connection_timeout,
                            menu_color
                        )
                #else if no session is selected reset filter and redisplay the main menu
                else:   
                    menu_lev = 1
            #Open terminal session selected when protocol menu is skipped
            if menu_lev == 0:
                menu_lev = open_terminal_session(
                    conn_proto_preselected,
                    conn_port, user,
                    host_selected,
                    back_to_menu_timer,
                    connection_timeout,
                    menu_color
                )
            #When no session is selected
            session_selected = False
            #Exit session menu _on_ctrl_E
            if menu_lev == 100:
                break
            #Refresh session menu
            if menu_lev == 101:
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
        main(sys.argv[1:])
    #Reset terminal and exit on Ctrl-C
    except KeyboardInterrupt:
        ansi.back(10)
        termenu.Termenu.clear_full_menu(clear_screen=True)
        termenu.clear_menu()
        ansi.change_cursor_color(g_cursor_exit_color)
        ansi.change_screen_color(g_screen_exit_color)
        ansi.show_cursor()
        os.system("stty sane")
        ansi.write(ansi.colorize("ntw-menu - Exited with CTRL-C\n",color="default"))
        sys.exit(0)