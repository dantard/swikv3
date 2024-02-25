import base64

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QMenu, QDialog, QMessageBox

from dialogs import PasswordDialog
from renderer import convert_box_to_upside_down
from resizeable import ResizableRectItem
from signer import P12Signer
from tool import Tool


class SignerRectItem(ResizableRectItem):
    ACTION_SIGN = 0

    def populate_menu(self, menu: QMenu):
        menu.addAction("Sign", lambda: self.signals.action.emit(SignerRectItem.ACTION_SIGN, self))
        menu.addSeparator()
        super(SignerRectItem, self).populate_menu(menu)


class ToolSign(Tool):
    def __init__(self, view, renderer, config):
        super().__init__(view, renderer, config)
        self.rubberband = None
        self.cfg_p12 = None
        self.cfg_password = None
        self.cfg_signed_suffix = None
        self.cfg_signature_border = None
        self.cfg_text_font_size = None
        self.cfg_text = None
        self.cfg_text_stretch = None
        self.cfg_text_timestamp = None
        self.cfg_image_file = None
        self.cfg_image_stretch = None

    def configure(self):
        signature = self.config.root().addSubSection("Digital Signature")
        self.cfg_p12 = signature.addFile("p12", pretty="Signature File", extension=["p12", "pfx"], extension_name="PKCS#12")
        self.cfg_password = signature.addPassword("password", pretty='Password')
        self.cfg_signed_suffix = signature.addString("signed_suffix", pretty="Signed File Suffix", default="-signed")
        appearance = signature.addSubSection("Appearance")
        self.cfg_signature_border = appearance.addInt("signature_border", pretty="Border width", default=0)
        text = appearance.addSubSection("Text")
        self.cfg_text_font_size = text.addInt("text_font_size", pretty="Font Size", default=11, max=85)
        self.cfg_text = text.addEditBox("text_signature", pretty="Text",
                                        default='Signed by&&%(signer)s&&Time: %(ts)s'.replace('\n', '\\n'))
        self.cfg_text_stretch = text.addCheckbox("text_stretch", pretty="Stretch")
        self.cfg_text_timestamp = text.addString("text_timestamp", default="%d/%m/%Y")

        image = appearance.addSubSection("Image")
        self.cfg_image_file = image.addFile("image_file", pretty="File", extension="png")
        self.cfg_image_stretch = image.addCheckbox("image_stretch", pretty="Stretch")

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
                                             image_mode=image_mode)

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
                                   font_size=self.config.get('text_font_size'),
                                   border=self.config.get('signature_border'),
                                   text=self.config.get('text_signature').replace('&&', '\n'),
                                   image=self.config.get('image_file'),
                                   timestamp=self.config.get('text_timestamp'),
                                   text_stretch=1 if self.config.get('text_stretch') else 0,
                                   image_stretch=0 if self.config.get('image_stretch') else 1)

        if res == P12Signer.OK:
            QMessageBox.information(self.view, "Signature", "Document signed Successfully", QMessageBox.Ok)
            # Save Password only if the signature was successful
            if password_to_save is not None:
                self.config.set('Password', password_to_save)
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
            self.sign(rubberband.get_limits().index,
                      rubberband.get_rect_on_limits())
