import base64
import glob
import os
import shutil

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QColor
from PyQt5.QtWidgets import QMenu, QDialog, QMessageBox, QVBoxLayout, QWidget, QPushButton, QTreeWidget, \
    QTreeWidgetItem, QHeaderView, QComboBox, QHBoxLayout, QLabel, QFileDialog

from swik import signer
from swik.dialogs import PasswordDialog, ImportDialog, ImportP12
from swik.interfaces import Shell
from swik.manager import Manager
from swik.renderer import convert_box_to_upside_down
from swik.resizeable import ResizableRectItem
from swik.signer import P12Signer
from swik.tools.tool import Tool


class SignerRectItem(ResizableRectItem):
    ACTION_SIGN = 0
    ACTION_EDIT = 1
    ACTION_DELETED = 2

    def contextMenuEvent(self, event: 'QGraphicsSceneContextMenuEvent') -> None:
        menu = QMenu()
        menu.addAction("Sign", lambda: self.signals.action.emit(SignerRectItem.ACTION_SIGN, self))
        menu.addAction("Edit", lambda: self.signals.action.emit(SignerRectItem.ACTION_EDIT, self))
        menu.addAction("Delete", self.delete_item)
        menu.addSeparator()
        menu.exec(event.screenPos())

    def delete_item(self):
        self.scene().removeItem(self)
        self.deleted()

    def deleted(self):
        self.signals.action.emit(SignerRectItem.ACTION_DELETED, self)


class SignatureConf:
    def __init__(self, config, section_name, p12_file=None):
        header = config.root().getSubSection("signatures", pretty="Digital Signatures")
        self.signature = signature = header.getSubSection(section_name)
        self.p12_file = signature.getFile("p12_file", pretty="File", extension="p12", default=p12_file)
        self.password = signature.getPassword("password", pretty='Password')
        self.signed_suffix = signature.getString("signed_suffix", pretty="Signed File Suffix", default="-signed")
        appearance = signature.getSubSection("Appearance")
        self.border = appearance.getInt("signature_border", pretty="Border width", default=0)
        text = appearance.getSubSection("Text")
        self.text_font_size = text.getInt("text_font_size", pretty="Font Size", default=11, max=85)
        self.text_signature = text.getEditBox("text_signature", pretty="Text", default='Signed by&&%(signer)s&&Time: %(ts)s'.replace('\n', '\\n'))
        self.text_stretch = text.getCheckbox("text_stretch", pretty="Stretch")
        self.text_timestamp = text.getString("text_timestamp", default="%d/%m/%Y")
        image = appearance.getSubSection("Image")
        self.image_file = image.getFile("image_file", pretty="File", extension="png")
        self.image_stretch = image.getCheckbox("image_stretch", pretty="Stretch")


class ToolSign(Tool):

    def __init__(self, widget: Shell, **kwargs):
        super().__init__(widget, **kwargs)
        self.rubberband = None
        self.helper = None
        self.sign_btn = None
        self.draw_btn = None
        self.tree = None
        self.signature_cb = None
        self.selected = 0
        self.signatures: dict = {}
        self.cfg_p12 = []

        self.nicknames = self.config.root().getList("signature_list", default=[], hidden=True)
        self.config.read()

        self.configure()

    def configure(self):
        self.signatures.clear()

        for nickname in self.nicknames.get_value():
            sc = SignatureConf(self.config, nickname)
            self.signatures[nickname] = sc

        self.config.read()

    def update_cb(self):
        self.signature_cb.clear()
        self.signature_cb.addItems(self.nicknames.get_value())
        self.check_interaction()

    def init(self):
        v_layout = QVBoxLayout()
        self.helper = QWidget()
        self.signature_cb = QComboBox()
        self.signature_cb.setMinimumWidth(100)

        h_layout = QHBoxLayout()

        add_btn = QPushButton("+")
        add_btn.clicked.connect(self.import_signature)
        add_btn.setFixedSize(25, 25)
        add_btn.setToolTip("Add Signature")

        self.remove_btn = QPushButton("-")
        self.remove_btn.clicked.connect(self.remove_signature)
        self.remove_btn.setFixedSize(25, 25)
        self.remove_btn.setToolTip("Remove")

        self.config_btn = QPushButton("⚙")
        self.config_btn.clicked.connect(self.show_config)
        self.config_btn.setFixedSize(25, 25)
        self.config_btn.setToolTip("Configure")

        self.make_default_btn = QPushButton("☑")
        self.make_default_btn.clicked.connect(self.make_default)
        self.make_default_btn.setFixedSize(25, 25)
        self.make_default_btn.setToolTip("Make default")

        h_layout.addWidget(self.signature_cb)
        h_layout.addWidget(self.make_default_btn)
        h_layout.addWidget(self.config_btn)
        h_layout.addWidget(self.remove_btn)
        h_layout.addWidget(add_btn)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.header().setVisible(False)
        v_layout.addWidget(QLabel("Info"))
        v_layout.addWidget(self.tree)

        try:
            valid = signer.get_signature_info(self.renderer.get_filename(),
                                              '/home/danilo/Desktop/AC_FNMT_Usuarios.cer')
            print(valid)
            for i, value in enumerate(valid):
                item = QTreeWidgetItem(["Signer " + str(i + 1)])
                self.tree.addTopLevelItem(item)
                print(i, value)
                for k, v in value.items():
                    item.addChild(QTreeWidgetItem([k, v]))
            self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        except Exception as e:
            print(e)

        # = '/home/danilo/Downloads/20240510_Resolucion_240510_Expresion_de_Interes_bolsa_viajes_general_2024-signed.pdf'
        # root_cert = load_cert_from_pemder('/home/danilo/Desktop/AC_FNMT_Usuarios.cer')

        self.draw_btn = QPushButton("Draw")
        self.draw_btn.setCheckable(True)

        self.sign_btn = QPushButton("Sign")
        self.sign_btn.setEnabled(False)

        v_layout.setAlignment(Qt.AlignTop)
        v_layout.addWidget(QLabel("Sign with"))
        v_layout.addLayout(h_layout)
        v_layout.addWidget(self.draw_btn)
        v_layout.addWidget(self.sign_btn)
        self.helper.setLayout(v_layout)
        self.widget.set_app_widget(self.helper, title="Sign")

        self.draw_btn.clicked.connect(self.draw_signature)
        self.sign_btn.clicked.connect(self.sign_document)
        self.signature_cb.currentIndexChanged.connect(self.on_signature_changed)

        for h in [self.draw_btn, self.sign_btn, self.signature_cb, self.tree, self.helper, add_btn,
                  self.make_default_btn, self.config_btn, self.remove_btn, h_layout, v_layout]:
            h.setContentsMargins(0, 0, 0, 0)

        self.update_cb()
        self.check_interaction()

    def import_signature(self):
        import_dialog = ImportP12("Select signature file", "PKCS#12 (*.p12)")
        if import_dialog.exec_():
            nickname = import_dialog.get_nickname()
            self.signatures[nickname] = SignatureConf(self.config, import_dialog.get_nickname(), import_dialog.get_file())
            self.nicknames.get_value().append(nickname)
            self.update_cb()

    def make_default(self):
        selected = self.signature_cb.currentText()
        self.nicknames.get_value().remove(selected)
        self.nicknames.get_value().insert(0, selected)
        self.update_cb()
        self.check_interaction()

    def remove_signature(self):
        if self.signature_cb.currentIndex() >= 0:
            index = self.signature_cb.currentText()
            ask = QMessageBox.question(self.helper, "Remove signature", "Are you sure you want to remove this signature?", QMessageBox.Yes | QMessageBox.No)
            if ask == QMessageBox.Yes:
                self.signatures.pop(index)
                self.nicknames.get_value().remove(index)
                self.update_cb()

    def show_config(self):
        self.config.exec(self.get_selected().signature)

    def check_interaction(self):
        self.draw_btn.setEnabled(self.signature_cb.count() > 0)
        self.config_btn.setEnabled(self.signature_cb.count() > 0)
        self.remove_btn.setEnabled(self.signature_cb.count() > 0)
        self.make_default_btn.setEnabled(self.signature_cb.count() > 0 and self.signature_cb.currentIndex() > 0)

    def on_signature_changed(self, index):
        self.check_interaction()

    def mouse_pressed(self, event):
        page = self.view.get_page_at_pos(event.pos())
        if page is None:
            return

        if self.rubberband is not None:
            if self.rubberband.parentItem() is None:
                self.rubberband.setParentItem(page)
                self.rubberband.view_mouse_press_event(self.view, event)

    def mouse_released(self, event):
        if self.rubberband is not None:
            if self.rubberband.view_mouse_release_event(self.view, event):
                self.sign_btn.setEnabled(True)
                self.draw_btn.setChecked(False)
                self.draw_btn.setEnabled(False)
                self.view.setCursor(Qt.ArrowCursor)
            else:
                self.rubberband = None
            # self.finished.emit()

    def mouse_moved(self, event):
        if self.rubberband is not None:
            self.rubberband.view_mouse_move_event(self.view, event)

    def sign(self, index, rect):
        signature = self.get_selected()

        filename = self.renderer.get_filename()

        password_to_save = None

        if (password := signature.password.get_value()) is None:
            dialog = PasswordDialog(parent=self.view)
            if dialog.exec() == QDialog.Accepted:
                password = dialog.getText()
                if dialog.getCheckBox():
                    password_to_save = base64.encodebytes(password.encode()).decode().replace('\n', '')
            else:
                return
        else:
            password = base64.decodebytes(password.encode()).decode()

        suffix = signature.signed_suffix.get_value()
        output_filename = filename.replace(".pdf", suffix + ".pdf")

        res = self.apply_signature(filename, index, rect,
                                   password, output_filename,
                                   font_size=signature.text_font_size.get_value(),
                                   border=signature.border.get_value(),
                                   text=signature.text_signature.get_value().replace('&&', '\n'),
                                   image=signature.image_file.get_value(),
                                   timestamp=signature.text_timestamp.get_value(),
                                   text_stretch=1 if signature.text_stretch.get_value() else 0,
                                   image_stretch=0 if signature.image_stretch.get_value() else 1)

        if res == P12Signer.OK:
            QMessageBox.information(self.view, "Signature", "Document signed Successfully", QMessageBox.Ok)
            # Save Password only if the signature was successful
            if password_to_save is not None:
                signature.signature.set_value(password_to_save)
                # self.renderer.open_pdf(output_filename)
            return output_filename
        else:
            QMessageBox.warning(self.view, "Signature", "Error signing the document", QMessageBox.Ok)
        return None

    def get_selected(self):
        index = self.signature_cb.currentText()
        return self.signatures[index]

    def apply_signature(self, filename, index, rect, password, output_filename, **kwargs):

        signature = self.get_selected()

        p12_file = signature.p12_file.get_value()

        signer = P12Signer(filename,
                           output_filename,
                           p12_file, password, **kwargs)

        box = convert_box_to_upside_down(filename, index, rect)

        # Actually Sign the file
        return signer.sign(index, box)

    def sign_document(self):
        filename = self.sign(self.rubberband.get_parent().index,
                             self.rubberband.get_rect_on_parent())
        if filename:
            self.rubberband = None
            self.emit_finished(Manager.OPEN_REQUESTED, filename)

    def draw_signature(self):
        signature = self.get_selected()

        text = signature.text_signature.get_value().replace('&&', '\n')
        image_filename = signature.image_file.get_value()
        max_font_size = signature.text_font_size.get_value()

        text_mode = SignerRectItem.TEXT_MODE_STRETCH if signature.text_stretch.get_value() else SignerRectItem.TEXT_MODE_KEEP
        image_mode = SignerRectItem.IMAGE_MODE_STRETCH if signature.image_stretch.get_value() else SignerRectItem.IMAGE_MODE_MAINTAIN_RATIO
        self.rubberband = SignerRectItem(None, text=text, image_filename=image_filename, max_font_size=max_font_size,
                                         text_mode=text_mode,
                                         image_mode=image_mode, pen=Qt.transparent, brush=QColor(255, 0, 0, 80))

        self.view.setCursor(Qt.CrossCursor)
        self.rubberband.signals.action.connect(self.actions)
        # self.view.scene().addItem(self.rubberband)

    def actions(self, action, rubberband):

        signature = self.get_selected()

        if action == SignerRectItem.ACTION_SIGN:
            self.sign(rubberband.get_parent().index,
                      rubberband.get_rect_on_parent())
        elif action == SignerRectItem.ACTION_EDIT:
            if self.config.edit():
                text = signature.text_signature.get_value().replace('&&', '\n')
                image = QImage(signature.image_file)
                max_font_size = signature.text_font_size

                text_mode = SignerRectItem.TEXT_MODE_STRETCH if signature.text_stretch.get_value() else SignerRectItem.TEXT_MODE_KEEP
                image_mode = SignerRectItem.IMAGE_MODE_STRETCH if self.signatures[
                    self.selected].image_stretch.get_value() else SignerRectItem.IMAGE_MODE_MAINTAIN_RATIO

                rubberband.apply_kwargs(text=text, image=image, max_font_size=max_font_size, text_mode=text_mode,
                                        image_mode=image_mode)
                rubberband.update()
        elif action == SignerRectItem.ACTION_DELETED:
            self.rubberband = None
            self.sign_btn.setEnabled(False)
            self.draw_btn.setEnabled(True)

    def finish(self):
        if self.rubberband is not None:
            self.view.scene().removeItem(self.rubberband)
            self.view.setCursor(Qt.ArrowCursor)
            self.rubberband = None
        self.view.setCursor(Qt.ArrowCursor)
        self.widget.remove_app_widget()
        self.helper.deleteLater()
