import io
import sys
import re
from pyfiglet import Figlet
from . import ansi

def show_menu(title, options, default=None, height=None, width=None,
    multiselect=False, precolored=False):
    """
    Shows an interactive menu in the terminal.

    Arguments:
        options: list of menu options
        default: initial option to highlight
        height: maximum height of the menu
        width: maximum width of the menu
        multiselect: allow multiple items to be selected?
        precolored: allow strings with embedded ANSI commands

    Returns:
        * If multiselect is True, returns a list of selected options.
        * If mutliselect is False, returns the selected option.
        * If an option is a 2-tuple, the first item will be displayed and the
          second item will be returned.
        * If menu is cancelled (Esc pressed), returns None.
        *
    Notes:
        * You can pass OptionGroup objects to `options` to create sub-headers
          in the menu.
    """

    plugins = [FilterPlugin()]
    if any(isinstance(opt, OptionGroup) for opt in options):
        plugins.append(OptionGroupPlugin())
    if title:
        plugins.append(TitlePlugin(title))
    if precolored:
        plugins.append(PrecoloredPlugin())
    menu = Termenu(options, default=default, height=height,
                   width=width, multiselect=multiselect, plugins=plugins)
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

    def __init__(self, options, menu_lev, default=None, height=None,
        width=None, multiselect=True, heartbeat=None, plugins=None):
        for plugin in plugins or []:
            register_plugin(self, plugin)
        self.options = self._make_option_objects(options)
        self.menu_lev = menu_lev
        self.height = min(height or 10, len(self.options))
        self.width = self._compute_width(width, self.options)
        self.multiselect = multiselect
        self.cursor = 0
        self.scroll = 0
        self._heartbeat = heartbeat
        self._aborted = False
        self._lineCache = {}
        self._set_default(default)

    def get_result(self):
        if self._aborted:
            return []
        else:
            selected = [o.result for o in self.options if o.selected]
            if not selected:
                try:
                    selected.append(self._get_active_option().result)
                except:
                    return False, 1
            return selected[0], self.menu_lev

    @pluggable
    def show(self):
        from termenu import keyboard
        self._print_menu()
        ansi.save_position()
        ansi.hide_cursor()
        try:
            for key in keyboard.keyboard_listener(self._heartbeat):
                stop = self._on_key(key)
                if stop:
                    return self.get_result()
                self._goto_top()
                self._print_menu()
        finally:
            self._clear_menu()
            ansi.show_cursor()
            
    def clear_full_menu():
        ansi.clear_screen()
        termheight = get_terminal_size()[1]
        for i in range(termheight):
            ansi.down(1)
            ansi.clear_line()
        ansi.up(termheight-1)

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
            if not self.multiselect:
                raise ValueError("multiple defaults passed, "
                + "but multiselect is False")
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
    def _on_key(self, key):
        func = "_on_" + key
        if hasattr(self, func):
            return getattr(self, func)()

    @pluggable
    def _on_heartbeat(self):
        pass

    def _on_down(self):
        height = min(self.height, len(self.options))
        if self.cursor < height - 1:
            self.cursor += 1
        elif self.scroll + height < len(self.options):
            self.scroll += 1

    def _on_up(self):
        if self.cursor > 0:
            self.cursor -= 1
        elif self.scroll > 0:
            self.scroll -= 1

    def _on_pageDown(self):
        height = min(self.height, len(self.options))
        if self.cursor < height - 1:
            self.cursor = height - 1
        elif self.scroll + height * 2 < len(self.options):
            self.scroll += height
        else:
            self.scroll = len(self.options) - height

    def _on_pageUp(self):
        height = min(self.height, len(self.options))
        if self.cursor > 0:
            self.cursor = 0
        elif self.scroll - height >= 0:
            self.scroll -= height
        else:
            self.scroll = 0

    def _on_ctrl_B(self):
        height = min(self.height, len(self.options))
        if self.cursor > 0:
            self.cursor = 0
        elif self.scroll - height >= 0:
            self.scroll -= height
        else:
            self.scroll = 0
            
    def _on_ctrl_F(self):
        height = min(self.height, len(self.options))
        if self.cursor < height - 1:
            self.cursor = height - 1
        elif self.scroll + height * 2 < len(self.options):
            self.scroll += height
        else:
            self.scroll = len(self.options) - height

    def _on_ctrl_R(self):
        self._aborted = True
        return True #stop loop

    def _on_home(self):
        self.cursor = 0
        self.scroll = 0

    def _on_end(self):
        self.scroll = len(self.options) - self.height
        self.cursor = self.height - 1

    def _on_esc(self):
        self.menu_lev = 100
        return self.menu_lev
        
    @pluggable
    def _on_enter(self):
        return True # stop loop
    
    @pluggable
    def _on_ctrl_backspace(self):
        self.menu_lev = self.menu_lev-1
        return True

    def _clear_cache(self):
        self._lineCache = {}

    @pluggable
    def _clear_menu(self):
        ansi.restore_position()
        termheight = get_terminal_size()[1]
        for i in xrange(termheight):
            ansi.clear_eol()
            ansi.up()
        ansi.clear_eol()

    @pluggable
    def _print_menu(self):
        ansi.write("\r")
        for index, option in enumerate(self._get_window()):
            option = option.text
            option = self._adjust_width(option)
            option = self._decorate(option, **self._decorate_flags(index))
            if self._lineCache.get(index) == option:
                ansi.down()
            else:
                ansi.write(option + "\n")
                self._lineCache[index] = option

    @pluggable
    def _adjust_width(self, option):
        if len(option) > self.width:
            option = shorten(option, self.width)
        if len(option) < self.width:
            option = option + " " * (self.width - len(option))
        return option

    @pluggable
    def _decorate_flags(self, index):
        return dict(
            active = (self.cursor == index),
            selected = (self.options[self.scroll+index].selected),
            moreAbove = (self.scroll > 0 and index == 0),
            moreBelow = (
                self.scroll + self.height < len(self.options) and 
                index == self.height - 1),
        )

    @pluggable
    def _decorate(self, option, **flags):
        active = flags.get("active", False)
        selected = flags.get("selected", False)

        # add selection / cursor decorations
        if active and selected:
            option = "*" + ansi.colorize(option, "red", "white")
        elif active:
            option = " " + ansi.colorize(option, "black", "white")
        elif selected:
            option = "*" + ansi.colorize(option, "red")
        else:
            option = " " + option

        return self._decorate_indicators(option, **flags)

    @pluggable
    def _decorate_indicators(self, option, **flags):
        moreAbove = flags.get("moreAbove", False)
        moreBelow = flags.get("moreBelow", False)

        # add more above/below indicators
        if moreAbove:
            option = option + " " + ansi.colorize("^", "white", bright=True)
        elif moreBelow:
            option = option + " " + ansi.colorize("v", "white", bright=True)
        else:
            option = option + "  "

        return option

class FilterPlugin(Plugin):
    def __init__(self):
        self.text = None

    def _make_option_objects(self, options):
        objects = self.parent._make_option_objects(options)
        self._allOptions = objects[:]
        return objects

    def _on_key(self, key):
        prevent = False
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
            self._refilter()

        if not prevent:
            return self.parent._on_key(key)

    def _print_menu(self):
        self.parent._print_menu()

        for i in xrange(0, self.host.height - len(self.host.options)):
            ansi.clear_eol()
            ansi.write("\n")
        if self.text is not None:
            ansi.write("/" + "".join(self.text))
            ansi.show_cursor()
        ansi.clear_eol()

    def _refilter(self):
        self.host._clear_cache()
        self.host.options = []
        text = "".join(self.text or []).lower()
        # filter the matching options
        for option in self._allOptions:
            try:
                regex_text = re.match(".*" + text + ".*",
                    option.text.lower())
                if regex_text:
                    if (regex_text.group(0) in option.text.lower() or
                        option.attrs.get("showAlways")):
                        self.host.options.append(option)
            except:
                break
        # select the first matching element (showAlways no match required)
        self.host.scroll = 0
        self.host.cursor = 0
        for i, option in enumerate(self.host.options):
            try:
                regex_text = re.match(text, option.text.lower())
                if regex_text:
                    if (not option.attrs.get("showAlways") and
                        regex_text.group(0) in option.text.lower()):
                        self.host.cursor = i
                        break
            except:
                break
        ansi.hide_cursor()

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
        if active:
            if hostname:
                option = ansi.colorize(option, "blue", "white", bright=True)
            else:
                option = ansi.colorize(option, "black", "white")
        elif hostname:
            option = ansi.colorize(option, "white", bright=True)
        if selected:
            option = ansi.colorize("* ", "red") + option
        else:
            option = "  " + option

        return self.host._decorate_indicators(option, **flags)

class TitlePyfigletPlugin(Plugin):
    def __init__(self, title, subtitle, clearmenu):
        self.title = title
        self.subtitle = subtitle
        self.clearmenu = clearmenu

    def _goto_top(self):
        self.parent._goto_top()
        if self.clear_menu:
            ansi.up(8)

    def _print_menu(self):
        width_size, height_size = get_terminal_size()
        if len(self.host.options) == 1:
            counter_text = " (" + str(len(self.host.options)) + " option)"
        else:
            counter_text = " (" + str(len(self.host.options)) + " options)"        
        title_text = Figlet(font='small')
        ansi.write(ansi.colorize("\n", "white", bright=True))
        ansi.write(ansi.colorize(title_text.renderText(self.title), 
            "white", bright=True))
        ansi.write(ansi.colorize(
            self.subtitle + counter_text + " "*(width_size-(
                len(self.subtitle)+len(counter_text))
            ) + "\n\n", "white", bright=True)
        )
        return self.parent._print_menu()

    def _clear_menu(self):
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

if __name__ == "__main__":
    odds = OptionGroup("Odd Numbers", [
        ("%06d" % i, i) for i in xrange(1, 10, 2)
    ])
    evens = OptionGroup("Even Numbers", [
        ("%06d" % i, i) for i in xrange(2, 10, 2)
        ])
    print(show_menu("List Of Numbers", [odds, evens], multiselect=True))
