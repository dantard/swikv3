import base64

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QColor
from PyQt5.QtWidgets import QMenu, QDialog, QMessageBox

from dialogs import PasswordDialog
from renderer import convert_box_to_upside_down
from resizeable import ResizableRectItem
from signer import P12Signer
from tools.tool import Tool


class SignerRectItem(ResizableRectItem):
    ACTION_SIGN = 0
    ACTION_EDIT = 1

    def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
        menu = QMenu()
        menu.addAction("Sign", lambda: self.signals.action.emit(SignerRectItem.ACTION_SIGN, self))
        menu.addAction("Edit", lambda: self.signals.action.emit(SignerRectItem.ACTION_EDIT, self))
        menu.addSeparator()
        menu.exec(event.screenPos())


class ToolSign(Tool):
    (configured, cfg_p12, cfg_password, cfg_signed_suffix,
     cfg_signature_border, cfg_text_font_size, cfg_text,
     cfg_text_stretch, cfg_text_timestamp, cfg_image_file,
     cfg_image_stretch) = (False, None, None, None,
                           None, None, None, None, None, None, None)

    def __init__(self, view, renderer, config):
        super().__init__(view, renderer, config)
        self.rubberband = None

    @staticmethod
    def configure(config):
        if not ToolSign.configured:
            signature = config.root().addSubSection("Digital Signature")
            ToolSign.cfg_p12 = signature.addFile("p12", pretty="Signature File", extension=["p12", "pfx"], extension_name="PKCS#12")
            ToolSign.cfg_password = signature.addPassword("password", pretty='Password')
            ToolSign.cfg_signed_suffix = signature.addString("signed_suffix", pretty="Signed File Suffix", default="-signed")
            appearance = signature.addSubSection("Appearance")

            ToolSign.cfg_signature_border = appearance.addInt("signature_border", pretty="Border width", default=0)
            text = appearance.addSubSection("Text")
            ToolSign.cfg_text_font_size = text.addInt("text_font_size", pretty="Font Size", default=11, max=85)
            ToolSign.cfg_text = text.addEditBox("text_signature", pretty="Text",
                                                default='Signed by&&%(signer)s&&Time: %(ts)s'.replace('\n', '\\n'))
            ToolSign.cfg_text_stretch = text.addCheckbox("text_stretch", pretty="Stretch")
            ToolSign.cfg_text_timestamp = text.addString("text_timestamp", default="%d/%m/%Y")

            image = appearance.addSubSection("Image")
            ToolSign.cfg_image_file = image.addFile("image_file", pretty="File", extension="png")
            ToolSign.cfg_image_stretch = image.addCheckbox("image_stretch", pretty="Stretch")
            ToolSign.configured = True

    def mouse_pressed(self, event):
        page = self.view.get_page_at_pos(event.pos())
        if page is None:
            return

        if self.rubberband is None:
            text = self.cfg_text.get_value().replace('&&', '\n')
            image = QImage(self.cfg_image_file.get_value())
            max_font_size = self.cfg_text_font_size.get_value()

            text_mode = SignerRectItem.TEXT_MODE_STRETCH if self.cfg_text_stretch.get_value() else SignerRectItem.TEXT_MODE_KEEP
            image_mode = SignerRectItem.IMAGE_MODE_STRETCH if self.cfg_image_stretch.get_value() else SignerRectItem.IMAGE_MODE_MAINTAIN_RATIO
            self.rubberband = SignerRectItem(page, text=text, image=image, max_font_size=max_font_size, text_mode=text_mode,
                                             image_mode=image_mode, pen=Qt.transparent, brush=QColor(255, 0, 0, 80))

            self.view.setCursor(Qt.CrossCursor)
            self.rubberband.signals.action.connect(self.actions)
            self.view.scene().addItem(self.rubberband)
            self.rubberband.view_mouse_press_event(self.view, event)

    def mouse_released(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_release_event(self.view, event)
            self.rubberband = None
            self.finished.emit()

    def mouse_moved(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_move_event(self.view, event)

    def finish(self):
        self.view.setCursor(Qt.ArrowCursor)

    def sign(self, index, rect):
        filename = self.renderer.get_filename()

        password_to_save = None
        if (password := self.config.get('password')) is None:
            dialog = PasswordDialog(parent=self.view)
            if dialog.exec() == QDialog.Accepted:
                password = dialog.getText()
                if dialog.getCheckBox():
                    password_to_save = base64.encodebytes(password.encode()).decode().replace('\n', '')
            else:
                return
        else:
            password = base64.decodebytes(password.encode()).decode()

        suffix = self.config.get('signed_suffix')
        output_filename = filename.replace(".pdf", suffix + ".pdf")

        res = self.apply_signature(filename, index, rect,
                                   password, output_filename,
                                   font_size=self.cfg_text_font_size.get_value(),
                                   border=self.cfg_signature_border.get_value(),
                                   text=self.cfg_text.get_value().replace('&&', '\n'),
                                   image=self.cfg_image_file.get_value(),
                                   timestamp=self.cfg_text_timestamp.get_value(),
                                   text_stretch=1 if self.cfg_text_stretch.get_value() else 0,
                                   image_stretch=0 if self.cfg_image_stretch.get_value() else 1)

        if res == P12Signer.OK:
            QMessageBox.information(self.view, "Signature", "Document signed Successfully", QMessageBox.Ok)
            # Save Password only if the signature was successful
            if password_to_save is not None:
                self.cfg_password.set_value(password_to_save)
            self.renderer.open_pdf(output_filename)
        else:
            QMessageBox.warning(self.view, "Signature", "Error signing the document", QMessageBox.Ok)

    def apply_signature(self, filename, index, rect, password, output_filename, **kwargs):

        if (p12_file := self.config.get('p12')) is None:
            self.config.edit()
            return

        signer = P12Signer(filename,
                           output_filename,
                           p12_file, password, **kwargs)

        box = convert_box_to_upside_down(filename, index, rect)

        # Actually Sign the file
        return signer.sign(index, box)

    def actions(self, action, rubberband):
        if action == SignerRectItem.ACTION_SIGN:
            self.sign(rubberband.get_parent().index,
                      rubberband.get_rect_on_parent())
        elif action == SignerRectItem.ACTION_EDIT:
            if self.config.edit():
                text = self.cfg_text.get_value().replace('&&', '\n')
                image = QImage(self.cfg_image_file.get_value())
                max_font_size = self.cfg_text_font_size.get_value()

                text_mode = SignerRectItem.TEXT_MODE_STRETCH if self.cfg_text_stretch.get_value() else SignerRectItem.TEXT_MODE_KEEP
                image_mode = SignerRectItem.IMAGE_MODE_STRETCH if self.cfg_image_stretch.get_value() else SignerRectItem.IMAGE_MODE_MAINTAIN_RATIO

                rubberband.apply_kwargs(text=text, image=image, max_font_size=max_font_size, text_mode=text_mode,
                                        image_mode=image_mode)
                rubberband.update()


