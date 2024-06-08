import tempfile

from PyQt5.QtCore import Qt, QPointF, QRectF, QUrl, QMimeData
from PyQt5.QtGui import QFont, QFontDatabase, QColor, QClipboard, QGuiApplication, QDesktopServices, QDrag
from PyQt5.QtWidgets import QMenu, QGraphicsRectItem, QGraphicsScene, QDialog, QMessageBox

import utils
from annotations.highlight_annotation import HighlightAnnotation
from annotations.redactannotation import RedactAnnotation
from dialogs import FontAndColorDialog
from font_manager import Font
from interfaces import Shell
from selector import SelectorRectItem
from simplepage import SimplePage
from swiktext import SwikText, SwikTextReplace
from tools.tool import Tool
from word import Word


class ToolTextSelection(Tool):
    SELECTION_MODE_NATURAL = 0
    SELECTION_MODE_RECT = 1

    def __init__(self, widget: Shell, **kwargs):
        super(ToolTextSelection, self).__init__(widget, **kwargs)
        self.rubberband = None
        self.font_manager = widget.get_font_manager()
        self.selection_mode = ToolTextSelection.SELECTION_MODE_RECT
        self.selected = []
        self.multiple_selection = []

    def iterate_selection_mode(self):
        self.selection_mode = (self.selection_mode + 1) % 2

    def clear_selection(self):
        zombies = []
        for word in self.selected:
            if word not in self.multiple_selection:
                word.set_selected(False)
                zombies.append(word)
        # self.selected.clear()
        for word in zombies:
            self.selected.remove(word)
        self.selected.clear()
        self.multiple_selection.clear()

    def selecting(self, selector: SelectorRectItem):
        p1 = selector.get_rect_on_scene().topLeft()
        p2 = selector.get_rect_on_scene().bottomRight()

        p1_on_view = self.view.mapFromScene(p1)
        p2_on_view = self.view.mapFromScene(p2)

        page1 = self.view.get_page_at_pos(p1_on_view)
        page2 = self.view.get_page_at_pos(p2_on_view)

        # print(page1.index, page2.index)

        self.clear_selection()

        if page1 is not None and page2 is not None:

            words = []

            for i in range(page1.index, page2.index + 1):
                page = self.view.get_page_item(i)

                for word in page.gather_words():
                    words.append(word)

            for i, word in enumerate(words):
                word.seq = i
                if word.get_rect_on_scene().intersects(selector.get_rect_on_scene()):
                    self.selected.append(word)

            if len(self.selected) > 0:
                if self.selection_mode == ToolTextSelection.SELECTION_MODE_NATURAL:
                    # Clear the selection to restore order
                    begin, end = self.selected[0].seq, self.selected[-1].seq
                    self.selected.clear()
                    for i in range(begin, end + 1):
                        words[i].set_selected(True)
                        self.selected.append(words[i])
                else:
                    for word in self.selected:
                        word.set_selected(True)

    def selecting_done(self, selector: SelectorRectItem):
        self.selecting(selector)
        self.view.scene().removeItem(selector)
        self.rubberband = None
        self.view.setCursor(Qt.ArrowCursor)
        self.multiple_selection.extend(self.selected)

    def mouse_pressed(self, event):
        if event.button() == Qt.RightButton:
            return

        if event.modifiers() & Qt.ShiftModifier:
            event.accept()
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setUrls([QUrl.fromLocalFile(self.renderer.get_filename())])
            drag.setMimeData(mime_data)
            drag.exec_(Qt.CopyAction)
            return

        if self.view.there_is_any_other_than(event.pos(), (SimplePage, Word)):
            return

        if self.rubberband is None:

            if event.modifiers() & Qt.ControlModifier:
                pass
            else:
                self.multiple_selection.clear()

            if self.selection_mode == ToolTextSelection.SELECTION_MODE_NATURAL:
                self.rubberband = SelectorRectItem(pen=Qt.transparent)
                self.view.setCursor(Qt.IBeamCursor)
            else:
                self.rubberband = SelectorRectItem()
                self.view.setCursor(Qt.CrossCursor)

            self.rubberband.signals.creating.connect(self.selecting)
            self.view.scene().addItem(self.rubberband)
            self.rubberband.view_mouse_press_event(self.view, event)

    def mouse_released(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_release_event(self.view, event)
            self.selecting_done(self.rubberband)

    def mouse_moved(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_move_event(self.view, event)

    def context_menu(self, event):
        page = self.view.get_page_at_pos(event.pos())
        if page is None:
            return

        # if not self.view.top_is(event.pos(), [SimplePage, SimplePage.MyImage, Word]):
        #    return

        if self.view.there_is_any_other_than(event.pos(), (SimplePage, Word)):
            return

        menu = QMenu()
        add_text = menu.addAction("Add Text")
        if len(self.selected) > 0:
            copy = menu.addAction("Copy")
            anon = menu.addAction("Anonymyze")
            highlight = menu.addAction("Highlight Annotation")
            replace = menu.addAction("Replace")
            menu.addSeparator()
            web_search = menu.addAction("Web Search")
        else:
            anon, highlight, copy, replace, web_search = None, None, None, None, None

        if QGuiApplication.clipboard().text() != "":
            paste = menu.addAction("Paste")
        else:
            paste = None

        res = menu.exec(event.globalPos())
        if res is None:
            pass
        elif res == paste:
            text = QGuiApplication.clipboard().text()
            for i, word in enumerate(text.replace("\n", " ").split(" ")):
                st = SwikText(word, page, self.font_manager, Font("fonts/Arial.ttf"), 11)
                on_scene = self.view.mapToScene(event.pos())
                st.setPos(st.mapFromScene(on_scene) + QPointF(15 * i, 15 * i))

        elif res == web_search:
            text = str()
            for word in self.selected:
                text += word.get_text() + " "
            text.rstrip(" ")
            if (query := self.config.general.get("web_search")) is not None:
                QDesktopServices.openUrl(QUrl(query + text))

        elif res == anon:
            for word in self.selected:  # type: Word
                r = RedactAnnotation(word.parentItem(), brush=Qt.black)
                r.setRect(word.get_rect_on_parent())
            self.clear_selection()

        elif res == highlight:
            annot = HighlightAnnotation(QColor(255, 0, 0, 80), self.selected[0].parentItem())
            for word in self.selected:  # type: Word
                r = word.get_rect_on_parent()
                annot.add_quad(r)
            self.clear_selection()

        elif res == add_text:
            st = SwikText("New Text", page, self.font_manager, Font("fonts/Arial.ttf"), 11)
            on_scene = self.view.mapToScene(event.pos())
            st.setPos(st.mapFromScene(on_scene))

        elif res == copy:
            self.copy_selected_to_clipboard()

        elif res == replace:
            first_font, first_size, first_color = self.renderer.get_word_font_info(self.selected[0])
            for word in self.selected[1:]:
                font, size, color = self.renderer.get_word_font_info(word)
                if font != first_font or size != first_size or color != first_color:
                    QMessageBox.warning(self.view, "Warning", "Selected words have different font, size or color.")
                    break

            print("WWWWW Font: ", first_font)

            dialog = FontAndColorDialog(self.font_manager, first_font, first_size, first_color)
            if dialog.exec() == QDialog.Accepted:
                for word in self.selected:
                    print("AAAAAAAAAAAAAPPPPPPPPPPPPPPP", dialog.get_font())

                    SwikTextReplace(word, self.font_manager, dialog.get_font(), dialog.get_font_size() / 1.34,
                                    dialog.get_text_color())
                    self.clear_selection()

    def mouse_double_clicked(self, event):
        scene_pos = self.view.mapToScene(event.pos())
        items = self.view.scene().items(scene_pos)
        if len(items) > 0 and type(items[0]) == Word:
            word = items[0]
            word.set_selected(True)
            if not word in self.selected:
                self.selected.append(word)

    def finish(self):
        for word in self.selected + self.multiple_selection:
            word.set_selected(False)
        self.selected.clear()
        self.multiple_selection.clear()
        self.view.setCursor(Qt.ArrowCursor)

    def copy_selected_to_clipboard(self):
        text = ""
        for word in self.selected:
            text += word.get_text() + " "
        text.rstrip(" ")
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)

    def keyboard(self, combination):
        if combination == "Ctrl+C":
            self.copy_selected_to_clipboard()
        elif combination == "Ctrl+A":
            self.select_all()

    def select_all(self):
        self.clear_selection()
        page = self.view.get_current_page()
        page.gather_words()
        for word in page.get_words():
            word.set_selected(True)
            self.selected.append(word)
