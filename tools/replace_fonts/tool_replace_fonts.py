from PyQt5.QtCore import QMimeData, QUrl, Qt, pyqtSignal
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QDialog

from dialogs import ReplaceFontsDialog
from dict_editor import DictTreeWidget
from progressing import Progressing
from tools.replace_fonts.repl_font import repl_font
from tools.replace_fonts.repl_fontnames import repl_fontnames
from tools.tool import BasicTool, Tool



class ToolReplaceFonts(Tool):

    file_generate = pyqtSignal(str, int, float)
    def __init__(self, view, icon, parent, **kwargs):
        super(ToolReplaceFonts, self).__init__(view, icon, parent, **kwargs)
        self.placeholder = None
        self.font_manager = kwargs.get('font_manager')

    def init(self):
        data = repl_fontnames(self.renderer.get_filename())
        editor = ReplaceFontsDialog(self.font_manager, data)
        res = editor.exec()
        if res == QDialog.Accepted:
            in_name = self.renderer.get_filename()
            out_name = in_name.replace(".pdf", "_replaced.pdf")
            self.placeholder = Progressing(self.view)
            def do():
                repl_font(in_name, editor.get_data(), out_name)
                self.finished.emit()
                self.file_generate.emit(out_name, self.view.get_page(), self.view.get_ratio())

            self.placeholder.start(do)
        else:
            self.finished.emit()




    def mouse_pressed(self, event):
        print("jajajajsssssssssssssss")



