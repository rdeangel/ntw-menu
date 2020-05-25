import io
import os
import sys
import configparser
import shelve
import re
from pyfiglet import Figlet
from random import randint
from . import ansi

def show_menu(title, options, default=None, height=None, width=None,
    precolored=False):
    """
    Shows an interactive menu in the terminal.

    """

    plugins = [FilterPlugin()]
    if any(isinstance(opt, OptionGroup) for opt in options):
        plugins.append(OptionGroupPlugin())
    if title:
        plugins.append(TitlePlugin(title))
    if precolored:
        plugins.append(PrecoloredPlugin())
    menu = Termenu(options, default=default, height=height,
                   width=width, plugins=plugins)
    return menu.show()

try:
    xrange()
except:
    xrange = range

def pluggable(method):
    """
    Mark a class method as extendable with plugins.
    """
    def wrapped(self, *args, **kwargs):
        if hasattr(self, "_plugins"):
            # call the last plugin, it may call the previous 
            # via self.parent.method
            # creating a call call chain
            return (getattr(self._plugins[-1],
                method.__name__)(*args, **kwargs))
        else:
            return method(self, *args, **kwargs)
    wrapped.original = method
    return wrapped

def register_plugin(host, plugin):
    """
    Register a plugin with a host object. Some @pluggable methods in the host
    will have their behaviour altered by the plugin.
    """
    class OriginalMethods(object):
        def __getattr__(self, name):
            return (lambda *args, **kwargs:
                getattr(host, name).original(host, *args, **kwargs))
    if not hasattr(host, "_plugins"):
        host._plugins = [OriginalMethods()]
    plugin.parent = host._plugins[-1]
    plugin.host = host
    host._plugins.append(plugin)

class Plugin(object):
    def __getattr__(self, name):
        #allow calls to fall through to parent plugins when method not defined
        return getattr(self.parent, name)


class Termenu(object):

    class _Option(object):
        def __init__(self, option, **attrs):
            if isinstance(option, tuple) and len(option) == 2:
                self.text, self.result = option
            else:
                self.text = self.result = option
            if not isinstance(self.text, str):
                self.text = str(self.text)
            self.selected = False
            self.attrs = attrs

    def __init__(self, options, menu_lev, cursor, scroll, filter_text, 
        height, width, memory, shelf, menu_color, user_config_file, 
        default=None, heartbeat=None, plugins=None):
        for plugin in plugins or []:
            register_plugin(self, plugin)
        self.options = self._make_option_objects(options)
        self.menu_lev = menu_lev
        self.height = min((get_terminal_size()[1]-10) or 10, len(self.options))
        self.termwidth_prev = get_terminal_size()[0]
        self.termheight_prev = get_terminal_size()[1]
        self.width = self._compute_width(width, self.options)
        self.cursor = cursor
        self.scroll = scroll
        self.filter_text = filter_text
        self.memory = memory
        self.shelve_file = shelf
        self.menu_color = menu_color
        self.user_config_file = user_config_file
        self.filter_color_bg_prev = ""
        self._heartbeat = heartbeat
        self._aborted = False
        self._lineCache = {}
        self._set_default(default)

    #saves default in-menu color changes at menu start
    def save_user_default_color(self):
        try:
            user_config = configparser.ConfigParser(defaults=None, allow_no_value=False,
                strict=True)
            user_config.optionxform = str
            user_config.read(self.user_config_file)
            user_config.set('MENU_COLORS',
                'Title_Color', str(self.menu_color['title_color']))
            user_config.set('MENU_COLORS',
                'Text_Color', str(self.menu_color['text_color']))
            user_config.set('MENU_COLORS',
                'Text_Active', str(self.menu_color['text_active']))
            user_config.set('MENU_COLORS',
                'Text_Active_Bg', str(self.menu_color['text_active_bg']))
            user_config.set('MENU_COLORS',
                'Filter_Color', str(self.menu_color['filter_color']))
            user_config.set('MENU_COLORS',
                'Filter_Color_Bg', str(self.menu_color['filter_color_bg']))
            user_config.set('MENU_COLORS',
                'Session_Color', str(self.menu_color['session_color']))
            user_config.set('MENU_COLORS',
                'Cursor_Color', str(self.menu_color['cursor_color']))
            user_config.set('MENU_COLORS',
                'Cursor_Exit_Color', str(self.menu_color['cursor_exit_color']))
            user_config.set('MENU_COLORS',
                'Screen_Color', str(self.menu_color['screen_color']))
            user_config.set('MENU_COLORS',
                'Screen_Exit_Color', str(self.menu_color['screen_exit_color']))
            user_config.set('MENU_COLORS',
                'Bright_Text', str(self.menu_color['bright_text']))
            with open(self.user_config_file, 'w') as usr_write_file:
                user_config.write(usr_write_file)
        except:
            print("issue with saving")

    #loads color presets from user config file
    def load_color_presets(self, color_preset_var):
        preset_num = color_preset_var.split("self.color_preset_")[1]
        preset_item = "Color_Preset_" + preset_num

        #loads presets from user config file
        try:
            user_config = configparser.ConfigParser(defaults=None, allow_no_value=False,
                strict=True)
            user_config.optionxform = str
            user_config.read(self.user_config_file)
            exec(color_preset_var + ' = (user_config["MENU_COLORS"]["' + preset_item + '"])')
        except:
            print("Error: it is not possible to load color presets from file: "
                + self.user_config_file)
            sys.exit()

        #estabilishes if presets are defined in user config 
        #file or if main config preset should be used
        try:
            preset_user_config = eval(
                'True if self.color_preset_{0} != "" else False'.format(preset_num))
        except:
            preset_user_config = False
        if preset_user_config:
            color_preset = eval(
                'self.color_preset_{0}.split(",")'.format(preset_num))
        else:
            color_preset = eval(
                'self.menu_color["color_preset_{0}"].split(",")'.format(preset_num))         

        #assigns the preset to the individual color parameters
        self.menu_color['title_color'] = color_preset[0]
        self.menu_color['text_color'] = color_preset[1]
        self.menu_color['text_active'] = color_preset[2]
        self.menu_color['text_active_bg'] = color_preset[3]
        self.menu_color['filter_color'] = color_preset[4]
        self.menu_color['filter_color_bg'] = color_preset[5]
        self.menu_color['session_color'] = color_preset[6]
        self.menu_color['cursor_color'] = color_preset[7]
        self.menu_color['cursor_exit_color'] = color_preset[8]
        self.menu_color['screen_color'] = color_preset[9]
        self.menu_color['screen_exit_color'] = color_preset[10]
        if color_preset[11] == "True":
            self.menu_color['bright_text'] = True
        else:
            self.menu_color['bright_text'] = False
        if self.menu_color['screen_color'] != "":
            ansi.change_screen_color(self.menu_color['screen_color'])
        if self.menu_color['cursor_color'] != "":
            ansi.change_cursor_color(self.menu_color['cursor_color'])

    #randomize all color parameters at once
    def color_func_1(self):
        text_color = str(randint(0, 255))
        text_active = str(randint(0, 255))
        text_active_bg = str(randint(0, 255))
        self.menu_color['title_color'] = text_color
        self.menu_color['text_color'] = text_color
        self.menu_color['text_active'] = text_active
        self.menu_color['text_active_bg'] = text_active_bg
        if self.menu_color['filter_color_bg'] != "":
            self.menu_color['filter_color'] = text_active
            self.menu_color['filter_color_bg'] = text_active_bg
        else:
            self.menu_color['filter_color'] = text_color
        self.menu_color['session_color'] = text_color
        self.menu_color['cursor_color'] = ""
        self.menu_color['cursor_exit_color'] = ""
        self.menu_color['screen_color'] = ""
        self.menu_color['screen_exit_color'] = ""
        self.menu_color['bright_text'] = bool(randint(0, 1))

    #changes menu text and session colors only
    def color_func_2(self):
        text_color = str(randint(0, 255))
        self.menu_color['title_color'] = text_color
        self.menu_color['text_color'] = text_color
        self.menu_color['session_color'] = text_color
        if self.menu_color['filter_color_bg'] == "":
            self.menu_color['filter_color'] = text_color

    #change selection colors and filters simultaneously and randomly
    def color_func_3(self):
        text_active = str(randint(0, 255))
        text_active_bg = str(randint(0, 255))
        self.menu_color['text_active'] = text_active
        self.menu_color['text_active_bg'] = text_active_bg
        self.menu_color['filter_color'] = text_active
        self.menu_color['filter_color_bg'] = text_active_bg

    #change selection colors and filters (text only) simultaneously and randomly
    def color_func_4(self):
        text_active = str(randint(0, 255))
        self.menu_color['text_active'] = text_active
        self.menu_color['filter_color'] = text_active

    #change selection active only both background and text randomly 
    def color_func_5(self):
        text_active = str(randint(0, 255))
        text_active_bg = str(randint(0, 255))
        self.menu_color['text_active'] = text_active
        self.menu_color['text_active_bg'] = text_active_bg

    #change selection active only and text only
    def color_func_6(self):
        text_active = str(randint(0, 255))
        self.menu_color['text_active'] = text_active

    #change filter background and text (if background is set)
    def color_func_7(self):
        filter_color = str(randint(0, 255))
        if self.menu_color['filter_color_bg'] != "":
            filter_color_bg = str(randint(0, 255))
            self.menu_color['filter_color'] = filter_color
            self.menu_color['filter_color_bg'] = filter_color_bg
        else:
            self.menu_color['filter_color'] = filter_color

    #change filter text only
    def color_func_8(self):
        filter_color = str(randint(0, 255))
        self.menu_color['filter_color'] = filter_color

    #switches filter background on and off
    def color_func_9(self):
        try:
            Termenu.filter_color_bg_prev
        except AttributeError:
            Termenu.filter_color_bg_prev = self.menu_color['text_active_bg']
        if self.menu_color['filter_color_bg'] != "":
            Termenu.filter_color_bg_prev = self.menu_color['filter_color_bg']
            self.menu_color['filter_color_bg'] = ""
        else:
            self.menu_color['filter_color_bg'] = Termenu.filter_color_bg_prev

    #changes screen color randomly
    def color_func_10(self):
        screen_color_dec = randint(0,16777215)
        screen_color_hex = str(hex(screen_color_dec))
        self.menu_color['screen_color'] ='#'+ screen_color_hex[2:]
        ansi.change_screen_color(self.menu_color['screen_color'])

    #switches bright text on and off
    def color_func_11(self):
        if self.menu_color['bright_text'] is False:
            self.menu_color['bright_text'] = True
        else:
            self.menu_color['bright_text'] = False

    def color_func_12(self):
        Termenu.save_user_default_color(self)

    #save color presets to user config file
    def save_color_presets(self, color_preset_var):
        preset_num = "Color_Preset_" + color_preset_var.split("self.color_preset_")[1]
        comma_delimited_preset = (
            self.menu_color['title_color'] + "," +
            self.menu_color['text_color'] + "," +
            self.menu_color['text_active'] + "," +
            self.menu_color['text_active_bg'] + "," +
            self.menu_color['filter_color'] + "," +
            self.menu_color['filter_color_bg'] + "," +
            self.menu_color['session_color'] + "," +
            self.menu_color['cursor_color'] + "," +
            self.menu_color['cursor_exit_color'] + "," +
            self.menu_color['screen_color'] + "," +
            self.menu_color['screen_exit_color'] + "," +
            str(self.menu_color['bright_text']))
        try:
            user_config = configparser.ConfigParser(defaults=None, allow_no_value=False,
                strict=True)
            user_config.optionxform = str
            user_config.read(self.user_config_file)
            exec('user_config.set("MENU_COLORS", "' + preset_num + '", comma_delimited_preset)')
            with open(self.user_config_file, 'w') as usr_write_file:
                 user_config.write(usr_write_file)
        except:
            print("Error: it is not possible to load color presets from file: "
                + self.user_config_file)

    #dinamically creates functions for F1-F12 key function combinations
    for i in range(12):
        f_item = str(i+1)
        shift_funcs = ('''
def _on_shift_F{0}(self):
    Termenu.color_func_{0}(self)
    return self.return_to_correct_menu(always=True)

def _on_alt_shift_F{0}(self):
    Termenu.load_color_presets(self, "self.color_preset_{0}")
    return self.return_to_correct_menu(always=True)

def _on_ctrl_alt_shift_F{0}(self):
    Termenu.save_color_presets(self, "self.color_preset_{0}")
    return self.return_to_correct_menu(always=True)
        '''.format(f_item))
        exec(shift_funcs)


    def get_result(self):
        if self._aborted:
            return []
        else:
            selected = [o.result for o in self.options if o.selected]
            if not selected:
                try:
                    selected.append(self._get_active_option().result)
                except:
                    return False, 1, 0, 0, []
            return (selected[0], self.menu_lev, self.cursor,
                self.scroll, self.filter_text)

    def clear_full_menu(clear_screen=False):
        termheight = get_terminal_size()[1]
        if clear_screen:
            ansi.clear_screen()
        else:
            ansi.down(termheight)
            for i in range(termheight):
                ansi.clear_line()
                ansi.up()
            #ansi.clear_line()
            #ansi.up(termheight)

    def refresh(self, menu_lev, always=False):
        Termenu.termwidth_new = get_terminal_size()[0]
        Termenu.termheight_new = get_terminal_size()[1]
        if ((Termenu.termheight_new != self.termheight_prev) or
            (Termenu.termwidth_new != self.termwidth_prev) or 
            (always == True)):
            self.termwidth_prev = Termenu.termwidth_new  
            self.termheight_prev = Termenu.termheight_new  
            if self.menu_lev == 1:
                return 101
            if self.menu_lev == 2:
                return 102

    def return_to_correct_menu(self, always=False):
        #Retun menu level for correct refresh
        new_menu_lev = self.refresh(self.menu_lev, always)
        if (new_menu_lev == 101) or (new_menu_lev == 102):
            self.menu_lev = new_menu_lev
            return True
        else:
            return False

    @pluggable
    def show(self):
        from termenu import keyboard
        termheight = get_terminal_size()[1]
        ansi.hide_cursor()
        if self.filter_text == None:
            self._print_menu()
        elif str(self.filter_text) == ('[]' or ''):
            self.filter_text = None
            self._print_menu()
        else:
            self._on_key('')
            self._print_menu()

        ansi.save_position()
        try:
            for key in keyboard.keyboard_listener(self._heartbeat):
                stop = self._on_key(key)
                if stop:
                    return self.get_result()
                self._goto_top()
                if str(self.filter_text) == ('[]' or ''):
                    self.filter_text = None
                    ansi.up(termheight)
                    self._print_menu()
                else:
                    ansi.up(termheight)
                    self._print_menu()
        finally:
            self._clear_menu()
            ansi.show_cursor()

    @pluggable
    def _goto_top(self):
        ansi.restore_position()
        ansi.up(self.height)

    @pluggable
    def _make_option_objects(self, options):
        return [self._Option(o) for o in options]

    @pluggable
    def _set_default(self, default):
        # handle default selection of multiple options
        if isinstance(default, list) and default:
            for option in self.options:
                if option.text in default:
                    option.selected = True
            default = default[0]

        # handle default active option
        index = self._get_index(default)
        if index is not None:
            if index < self.height:
                self.cursor = index % self.height
                self.scroll = 0
            elif index + self.height < len(self.options) - 1:
                self.cursor = 0
                self.scroll = index
            else:
                self.cursor = index % self.height + 1
                self.scroll = len(self.options) - self.height

    def _compute_width(self, width, options):
        termwidth = get_terminal_size()[0]
        decorations = len(self._decorate(""))
        if width:
            maxwidth = min(width, termwidth)
        else:
            maxwidth = termwidth
        maxwidth -= decorations
        maxoption = max(len(o.text) for o in options)
        return min(maxoption, maxwidth)

    def _get_index(self, s):
        matches = [i for i, o in enumerate(self.options) if o.text == s]
        if matches:
            return matches[0]
        else:
            return None

    def _get_active_option(self):
        return self.options[self.scroll+self.cursor] if self.options else None

    def _get_window(self):
        return self.options[self.scroll:self.scroll+self.height]

    def _get_debug_view(self):
        options = []
        for i, option in enumerate(self._get_window()):
            options.append(
                ("(%s)" if i == self.cursor else "%s") % option.text)
        return " ".join(options)
            
    @pluggable
    def _return_filter_text(self, text, cursor, scroll):
        self.filter_text = list(text)
        self.filter_cursor = cursor
        self.filter_scroll = scroll

    @pluggable
    def _on_key(self, key):
        func = "_on_" + key
        if hasattr(self, func):
            return getattr(self, func)()
        return self.return_to_correct_menu()

    @pluggable
    def _on_heartbeat(self):
        pass

    def _on_down(self):
        height = min(self.height, len(self.options))
        if self.cursor < height - 1:
            self.cursor += 1
        elif self.scroll + height < len(self.options):
            self.scroll += 1
        return self.return_to_correct_menu()

    def _on_up(self):
        if self.cursor > 0:
            self.cursor -= 1
        elif self.scroll > 0:
            self.scroll -= 1
        return self.return_to_correct_menu()

    def _on_pageDown(self):
        height = min(self.height, len(self.options))
        if self.cursor < height - 1:
            self.cursor = height - 1
        elif self.scroll + height * 2 < len(self.options):
            self.scroll += height
        else:
            self.scroll = len(self.options) - height
        return self.return_to_correct_menu()

    def _on_pageUp(self):
        height = min(self.height, len(self.options))
        if self.cursor > 0:
            self.cursor = 0
        elif self.scroll - height >= 0:
            self.scroll -= height
        else:
            self.scroll = 0
        return self.return_to_correct_menu()


    def _on_ctrl_B(self):
        height = min(self.height, len(self.options))
        if self.cursor > 0:
            self.cursor = 0
        elif self.scroll - height >= 0:
            self.scroll -= height
        else:
            self.scroll = 0
        return self.return_to_correct_menu()
            
    def _on_ctrl_F(self):
        height = min(self.height, len(self.options))
        if self.cursor < height - 1:
            self.cursor = height - 1
        elif self.scroll + height * 2 < len(self.options):
            self.scroll += height
        else:
            self.scroll = len(self.options) - height
        return self.return_to_correct_menu()
    
    def _on_ctrl_E(self):
        termheight = get_terminal_size()[1]
        self.menu_lev = 100
        return self.menu_lev

    def _on_ctrl_R(self):
        return self.return_to_correct_menu(always=True)

    def _on_home(self):
        self.cursor = 0
        self.scroll = 0

    def _on_end(self):
        self.scroll = len(self.options) - self.height
        self.cursor = self.height - 1

    @pluggable
    def _on_esc(self):
        if self.menu_lev > 1:
            self.menu_lev = self.menu_lev-1
            return True
        else:
            self.menu_lev = 101
            return True
        
    @pluggable
    def _on_enter(self):
        return True # stop loop

    def _clear_cache(self):
        self._lineCache = {}

    @pluggable
    def _clear_menu(self):
        clear_menu()
        
    @pluggable
    def _print_menu(self):
        termwidth = get_terminal_size()[0]
        termheight = get_terminal_size()[1]
        self.termwidth_prev = termwidth
        self.termheight_prev = termheight

        if self.cursor >= termheight-10:
                self.cursor = 0
        if len(self.options) >= termheight-8:
            if (len(self.options) - (self.cursor+1)) == self.scroll:
                self.scroll = len(self.options) - (termheight-10)
        option_count = 0
        for index, option in enumerate(self._get_window()):
            option = option.text
            option = self._adjust_width(option)
            option = self._decorate(option, **self._decorate_flags(index))
            if self._lineCache.get(index) == option:
                ansi.down()
            else:
                ansi.write(option + "\n")
                self._lineCache[index] = option
            option_count+=1
        if option_count <= termheight - 12:
            self.scroll = 0

        if self.memory and (len(self.options) > 0):
            shelf_store = shelve.open(self.shelve_file)
            if self.menu_lev == 1:
                shelf_store['dev_cursor'] = self.cursor
                shelf_store['dev_scroll'] = self.scroll
                shelf_store['dev_filter'] = self.filter_text
            if self.menu_lev == 2:
                shelf_store['proto_cursor'] = self.cursor
                shelf_store['proto_scroll'] = self.scroll
                shelf_store['proto_filter'] = self.filter_text
            shelf_store.close()
        ansi.clear_eol()

    @pluggable
    def _adjust_width(self, option):
        if len(option) > self.width:
            option = shorten(option, self.width)
        if len(option) < self.width:
            option = option + " " * (self.width - len(option))
        return option

    @pluggable
    def _refilter(self):
        cursor = self.cursor
        scroll = self.scroll        
        
    @pluggable
    def _decorate_flags(self, index):
        return dict(
            active = (self.cursor == index),
            selected = (self.options[self.scroll+index].selected),
            moreAbove = (self.scroll > 0 and index == 0),
            moreBelow = (
                self.scroll + self.height < len(self.options) and 
                index == self.height - 1),
            menu_color = ( self.menu_color ),
        )

    @pluggable
    def _decorate(self, option, **flags):
        active = flags.get("active", False)

        return self._decorate_indicators(option, **flags)

    @pluggable
    def _decorate_indicators(self, option, **flags):
        moreAbove = flags.get("moreAbove", False)
        moreBelow = flags.get("moreBelow", False)

        # add more above/below indicators
        if moreAbove:
            option = option + " " + ansi.colorize("^", self.menu_color['text_color'],
                bright=self.menu_color['bright_text'])
        elif moreBelow:
            option = option + " " + ansi.colorize("v", self.menu_color['text_color'],
                bright=self.menu_color['bright_text'])
        else:
            option = option + "  "

        return option

class FilterPlugin(Plugin):
    def __init__(self, filter_text, filter_cursor, filter_scroll, menu_color):
        self.text = filter_text
        self.cursor = filter_cursor
        self.scroll = filter_scroll
        self.menu_color = menu_color

    def _make_option_objects(self, options):
        objects = self.parent._make_option_objects(options)
        self._allOptions = objects[:]
        return objects

    def _return_filter_text(self, text, cursor, scroll):
        return list(text), cursor, scroll
        
    def _on_key(self, key):
        prevent = False
        if key == "":
            self._refilter()
        if len(key) == 1 and 32 < ord(key) <= 127:
            if not self.text:
                self.text = []
            self.text.append(key)
            self._refilter()
        elif self.text and key == "space":
            self.text.append(' ')
            self._refilter()
        elif self.text and key == "backspace":
            del self.text[-1]
            self._refilter()
        elif self.text is not None and key == "esc":
            self.text = None
            prevent = True
            if self.text != "":
                self._refilter()

        if not prevent:
            return self.parent._on_key(key)

    def _print_menu(self):
        self.parent._print_menu()
        termheight = get_terminal_size()[1]

        if (self.host.height == (termheight-10)) and (len(self.host.options) >= self.host.height):
            #print(termheight, self.host.height, len(self.host.options), self.cursor, self.scroll)
            #sys.exit(0)
            for i in range(0, self.host.height - len(self.host.options)):
                ansi.clear_eol()
                ansi.write("\n")
            if self.text is not None and self.text != []:
                ansi.write(ansi.colorize("/" + "".join(self.text), self.menu_color['filter_color'], 
                    self.menu_color['filter_color_bg'], self.menu_color['bright_text']))
                ansi.write(ansi.colorize("\0", self.menu_color['cursor_color'],
                    self.menu_color['cursor_color'], True))
                ansi.change_cursor_color(self.menu_color['cursor_color'])
                ansi.show_cursor()
        else:
            #print(termheight, self.host.cursor, self.host.scroll, len(self.host.options))
            #sys.exit(0)
            for i in range(0, (termheight - (len(self.host.options)+10))):
                ansi.clear_eol()
                ansi.write("\n")
            if self.text is not None and self.text != []:
                ansi.write(ansi.colorize("/" + "".join(self.text), self.menu_color['filter_color'], 
                    self.menu_color['filter_color_bg'], self.menu_color['bright_text']))
                ansi.write(ansi.colorize("\0", self.menu_color['cursor_color'],
                    self.menu_color['cursor_color'], False))
                ansi.change_cursor_color(self.menu_color['cursor_color'])
                ansi.show_cursor()
            ansi.clear_eol()

    def _refilter(self):
        width_size, height_size = get_terminal_size()
        self.host._clear_cache()
        self.host.options = []
        if str(self.text) != "None":
            text = "".join(self.text)
            search_text = text.lower()
        else:
            search_text = text = ""
        record_counter = 0
        match_counter = 0

        # filter the matching options
        for option in self._allOptions:
            try:
                regex_text = re.match(".*" + search_text + ".*",
                    option.text.lower())
                if regex_text:
                    self.host.options.append(option)
            except:
                break
            record_counter+=1
        if (((len(self.host.options) == 1) and (self.host.cursor == 1)) or
        ((self.host.cursor + self.host.scroll) >= len(self.host.options)) or
        (self.host.cursor > height_size-11)):
            self.host.cursor = 0
            self.host.scroll = 0
            self.cursor = self.host.cursor
            self.scroll = self.host.scroll
        elif height_size-8 <= len(self.host.options):
            self.host.cursor = self.cursor
            self.host.scroll = self.scroll
            self.cursor = self.host.cursor
            self.scroll = self.host.scroll
        #print(self.host.cursor, self.host.scroll)
        ansi.hide_cursor()
        self.parent._return_filter_text(text,self.cursor,self.scroll)

class ColourPlugin(Plugin):
    def _decorate_flags(self, index):
        flags = self.parent._decorate_flags(index)
        flags.update(dict(
            hostname = self.host.options[self.host.scroll+index].text
        ))
        return flags

    def _decorate(self, option, **flags):
        hostname = flags.get("hostname", False)
        active = flags.get("active", False)
        selected = flags.get("selected", False)
        menu_color = flags.get("menu_color", False)
        if active:
            if hostname:
                option = ansi.colorize(option, menu_color['text_active'], 
                    menu_color['text_active_bg'], menu_color['bright_text'])
            else:
                option = ansi.colorize(option, menu_color['text_color'], 
                    menu_color['text_bg'])
        elif hostname:
            option = ansi.colorize(option, menu_color['text_color'], 
                "", menu_color['bright_text'])

        return self.host._decorate_indicators(option, **flags)

class TitlePyfigletPlugin(Plugin):
    def __init__(self, title, subtitle, clearmenu, color):
        self.title = title
        self.subtitle = subtitle
        self.clearmenu = clearmenu
        self.color = color['title_color']
        self.bright = color['bright_text']

    def _goto_top(self):
        self.parent._goto_top()
        if self.clear_menu:
            ansi.up(8)

    def _print_menu(self):
        ansi.hide_cursor()
        width_size, height_size = get_terminal_size()
        if len(self.host.options) == 1:
            counter_text = " (" + str(len(self.host.options)) + " option)"
        else:
            counter_text = " (" + str(len(self.host.options)) + " options)"   
        title_text = Figlet(font='small', width=width_size)
        ansi.write(ansi.colorize("\n", self.color, bright=self.bright))
        ansi.write(ansi.colorize(title_text.renderText(self.title), 
            self.color, bright=self.bright))
        ansi.write(ansi.colorize(
            self.subtitle + counter_text + " "*(width_size-(
                len(self.subtitle)+len(counter_text))
            ) + "\n", self.color, bright=self.bright)
        )
        ansi.clear_eol()
        ansi.down()
        return self.parent._print_menu()

    def _clear_menu(self):
        ansi.hide_cursor()
        self.parent._clear_menu()
        if self.clear_menu:
            ansi.up(8)
        ansi.clear_eol()

def redirect_std():
    """
    Connect stdin/stdout to controlling terminal even if the scripts input and output
    were redirected. This is useful in utilities based on termenu.
    """
    stdin = sys.stdin
    stdout = sys.stdout
    if not sys.stdin.isatty():
        sys.stdin = open_raw("/dev/tty", "r", 0)
    if not sys.stdout.isatty():
        sys.stdout = open_raw("/dev/tty", "w", 0)

    return stdin, stdout

def shorten(s, l=100):
    if len(s) <= l or l < 3:
        return s
    return s[:l//2-2] + "..." + s[-l//2+1:]

def get_terminal_size():
    import fcntl, termios, struct
    try:
        h, w, hp, wp = struct.unpack('HHHH', fcntl.ioctl(sys.stdin,
            termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0)))
        return w, h
    except OSError:
        return 80, 25

def clear_menu():
    ansi.restore_position()
    termwidth = get_terminal_size()[0]
    termheight = get_terminal_size()[1]
    for i in xrange(termheight):
        ansi.clear_line()
        ansi.up()
    ansi.back(termwidth)


if __name__ == "__main__":
    odds = OptionGroup("Odd Numbers", [
        ("%06d" % i, i) for i in xrange(1, 10, 2)
    ])
    evens = OptionGroup("Even Numbers", [
        ("%06d" % i, i) for i in xrange(2, 10, 2)
        ])
    print(show_menu("List Of Numbers", [odds, evens]))
