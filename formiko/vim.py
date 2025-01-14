from logging import error
from os.path import splitext
from subprocess import PIPE, Popen, check_output
from time import sleep
from uuid import uuid4

from gi.repository.GObject import SIGNAL_RUN_FIRST, SIGNAL_RUN_LAST
from gi.repository.Gtk import Socket

VIM_PATH = "/usr/bin"


class VimEditor(Socket):
    __gsignals__ = {
        "file-type": (SIGNAL_RUN_FIRST, None, (str,)),
        "scroll-changed": (SIGNAL_RUN_LAST, None, (float,)),   # not implemented
    }

    def __init__(self, app_window, file_name=""):
        super().__init__()
        self.__file_name = file_name
        self.__server_name = str(uuid4())
        self.connect("plug-removed", app_window.destroy_from_vim)
        self.connect("realize", self.print_state)

    def print_state(self, *args):
        self.vim_start_server()

    def vim_start_server(self):
        if self.__file_name:
            name, ext = splitext(self.__file_name)
            self.emit("file-type", ext)
            file_type = ""
        else:
            file_type = " filetype=rst"
        args = [
            VIM_PATH+"/gvim",
            "--socketid", str(self.get_id()),
            "--servername", self.__server_name,
            "--echo-wid",
            # no menu (m) a no toolbar (T)
            "-c", "set go-=m go-=T" + file_type]
        if self.__file_name:
            args.append(self.__file_name)
        server = Popen(args, stdout=PIPE)
        server.stdout.readline()    # read wid, so server was started
        sleep(0.1)                  # some time for vim server

    def vim_remote_expr(self, command):
        out = check_output([
            VIM_PATH+"/vim",
            "--servername", self.__server_name,
            "--remote-expr", command,
            ])
        return out.decode("utf-8").strip()

    def vim_remote_send(self, command):
        check_output([
            VIM_PATH+"/vim",
            "--servername", self.__server_name,
            "--remote-send", command,
            ])

    def get_vim_changes(self):
        return int(self.vim_remote_expr("b:changedtick") or "0")

    def get_vim_lines(self):
        return int(self.vim_remote_expr("line('$')") or "0")

    def get_vim_get_buffer(self, count):
        return self.vim_remote_expr("getline(0, %d)" % count)

    def get_vim_pos(self):
        pos = self.vim_remote_expr("getpos('.')") or ",0,0,"
        buff, row, col, off = pos.split("\n")
        return int(row), int(col)

    def get_vim_file_path(self):
        return self.vim_remote_expr("expand('%:p')")

    def get_vim_encoding(self):
        return self.vim_remote_expr("&l:encoding")

    def get_vim_filetype(self):
        return self.vim_remote_expr("&l:filetype")

    def vim_quit(self):
        self.vim_remote_send("<ESC>:q! <CR>")

    def vim_open_file(self, file_name):
        self.vim_remote_send("<ESC>:e %s<CR>" % file_name)

    @property
    def is_modified(self):
        return bool(int(self.vim_remote_expr("&l:modified") or "0"))

    @property
    def file_name(self):
        __file_name = self.vim_remote_expr("@%")
        if __file_name != self.__file_name:
            name, ext = splitext(__file_name)
            self.emit("file-type", ext)
        self.__file_name = __file_name
        return self.__file_name

    @property
    def file_path(self):
        return self.get_vim_file_path()

    def do_file_type(self, ext):
        pass

    def read_from_file(self, file_name):
        error("Not supported call read_from_file in VimEditor")

    def save(self, *args):
        error("Not supported call save in VimEditor")

    def save_as(self, *args):
        error("Not supported call save_as in VimEditor")
