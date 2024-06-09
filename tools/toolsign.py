import base64
import glob
import os
import shutil

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QColor
from PyQt5.QtWidgets import QMenu, QDialog, QMessageBox, QVBoxLayout, QWidget, QPushButton, QTreeWidget, \
    QTreeWidgetItem, QHeaderView, QComboBox, QGroupBox, QHBoxLayout, QLabel, QFileDialog

import signer
from dialogs import PasswordDialog
from interfaces import Shell
from manager import Manager
from renderer import convert_box_to_upside_down
from resizeable import ResizableRectItem
from signer import P12Signer
from tools.tool import Tool
import contextlib


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
    def __init__(self, header, section_name, file):
        self.signature = signature = header.getSubSection(section_name)
        self.nickname = signature.getString("nickname", pretty="Nickname", default=section_name)
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
        self.p12_file = file


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
        self.signatures: list[SignatureConf] = []
        self.cfg_p12 = []
        self.configure()

    def configure(self):
        self.signatures.clear()

        header = self.config.root().getSubSection("digital_signature", pretty="Digital Signatures")

        for file_path in glob.glob(os.path.join(self.config.base_dir + "signatures", '*.p12')):
            if os.path.isfile(file_path):
                section_name = os.path.basename(file_path).replace(".p12", "")
                sc = SignatureConf(header, section_name, file_path)
                self.signatures.append(sc)

        self.config.read()

    def update_cb(self):
        self.signature_cb.clear()
        self.signature_cb.addItems([x.nickname.get_value() for x in self.signatures])

    def init(self):
        v_layout = QVBoxLayout()
        self.helper = QWidget()

        self.signature_cb = QComboBox()
        self.signature_cb.currentIndexChanged.connect(self.on_signature_changed)
        self.update_cb()
        h_layout = QHBoxLayout()

        add_btn = QPushButton("+")
        add_btn.clicked.connect(self.import_signature)
        add_btn.setFixedSize(25, 25)

        remove_btn = QPushButton("-")
        remove_btn.clicked.connect(self.remove_signature)
        remove_btn.setFixedSize(25, 25)

        config_btn = QPushButton("⚙")
        config_btn.clicked.connect(self.show_config)
        config_btn.setFixedSize(25, 25)

        h_layout.addWidget(self.signature_cb)
        h_layout.addWidget(config_btn)
        h_layout.addWidget(remove_btn)
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
        self.draw_btn.clicked.connect(self.draw_signature)
        self.draw_btn.setCheckable(True)

        self.sign_btn = QPushButton("Sign")
        self.sign_btn.clicked.connect(self.sign_document)

        self.sign_btn.setEnabled(False)
        v_layout.setAlignment(Qt.AlignTop)
        v_layout.addWidget(QLabel("Sign with"))
        v_layout.addLayout(h_layout)
        v_layout.addWidget(self.draw_btn)
        v_layout.addWidget(self.sign_btn)
        self.helper.setLayout(v_layout)
        self.widget.set_app_widget(self.helper, title="Sign")
        self.check_interaction()

    def import_signature(self):
        if not self.config.been_warned("signature_import"):
            if QMessageBox.warning(self.helper, "Import signature",
                                   "The file will be copied to the signatures folder in the configuration directory.",
                                   QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                return

        file_path = QFileDialog.getOpenFileName(self.helper, "Select signature file", self.config.base_dir + "signatures", "PKCS#12 (*.p12)")[0]
        if file_path:
            self.config.set_warned("signature_import", True)
            shutil.copy2(file_path, self.config.base_dir + "signatures")
            self.configure()
            self.signature_cb.clear()
            self.signature_cb.addItems([os.path.basename(p12).rstrip(".p12") for p12 in self.cfg_p12])
            self.check_interaction()

    def remove_signature(self):
        index = self.signature_cb.currentIndex()
        if index >= 0:
            ask = QMessageBox.question(self.helper, "Remove signature", "Are you sure you want to remove this signature?", QMessageBox.Yes | QMessageBox.No)
            if ask == QMessageBox.Yes:
                os.remove(self.cfg_p12[index])
                self.configure()
                self.signature_cb.clear()
                self.signature_cb.addItems([os.path.basename(p12).rstrip(".p12") for p12 in self.cfg_p12])
                self.check_interaction()

    def show_config(self):
        self.config.exec(self.signatures[self.selected].signature)
        index = self.signature_cb.currentIndex()
        self.update_cb()
        self.signature_cb.setCurrentIndex(index)

    def check_interaction(self):
        self.draw_btn.setEnabled(self.signature_cb.count() > 0)

    def on_signature_changed(self, index):
        self.selected = index

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
        filename = self.renderer.get_filename()

        password_to_save = None
        if (password := self.signatures[self.selected].password.get_value()) is None:
            dialog = PasswordDialog(parent=self.view)
            if dialog.exec() == QDialog.Accepted:
                password = dialog.getText()
                if dialog.getCheckBox():
                    password_to_save = base64.encodebytes(password.encode()).decode().replace('\n', '')
            else:
                return
        else:
            password = base64.decodebytes(password.encode()).decode()

        suffix = self.signatures[self.selected].signed_suffix.get_value()
        output_filename = filename.replace(".pdf", suffix + ".pdf")

        print("hhhhhhhhhhhhhhhhhhhhh", filename)

        res = self.apply_signature(filename, index, rect,
                                   password, output_filename,
                                   font_size=self.signatures[self.selected].text_font_size.get_value(),
                                   border=self.signatures[self.selected].border.get_value(),
                                   text=self.signatures[self.selected].text_signature.get_value().replace('&&', '\n'),
                                   image=self.signatures[self.selected].image_file.get_value(),
                                   timestamp=self.signatures[self.selected].text_timestamp.get_value(),
                                   text_stretch=1 if self.signatures[self.selected].text_stretch.get_value() else 0,
                                   image_stretch=0 if self.signatures[self.selected].image_stretch.get_value() else 1)

        if res == P12Signer.OK:
            QMessageBox.information(self.view, "Signature", "Document signed Successfully", QMessageBox.Ok)
            # Save Password only if the signature was successful
            if password_to_save is not None:
                self.signatures[self.selected].signature.set_value(password_to_save)
                # self.renderer.open_pdf(output_filename)
            return output_filename
        else:
            QMessageBox.warning(self.view, "Signature", "Error signing the document", QMessageBox.Ok)
        return None

    def apply_signature(self, filename, index, rect, password, output_filename, **kwargs):
        p12_file = self.signatures[self.selected].p12_file

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
        text = self.signatures[self.selected].text_signature.get_value().replace('&&', '\n')
        image_filename = self.signatures[self.selected].image_file.get_value()
        max_font_size = self.signatures[self.selected].text_font_size.get_value()

        text_mode = SignerRectItem.TEXT_MODE_STRETCH if self.signatures[self.selected].text_stretch.get_value() else SignerRectItem.TEXT_MODE_KEEP
        image_mode = SignerRectItem.IMAGE_MODE_STRETCH if self.signatures[self.selected].image_stretch.get_value() else SignerRectItem.IMAGE_MODE_MAINTAIN_RATIO
        self.rubberband = SignerRectItem(None, text=text, image_filename=image_filename, max_font_size=max_font_size,
                                         text_mode=text_mode,
                                         image_mode=image_mode, pen=Qt.transparent, brush=QColor(255, 0, 0, 80))

        self.view.setCursor(Qt.CrossCursor)
        self.rubberband.signals.action.connect(self.actions)
        # self.view.scene().addItem(self.rubberband)

    def actions(self, action, rubberband):
        if action == SignerRectItem.ACTION_SIGN:
            self.sign(rubberband.get_parent().index,
                      rubberband.get_rect_on_parent())
        elif action == SignerRectItem.ACTION_EDIT:
            if self.config.edit():
                text = self.signatures[self.selected].text_signature.get_value().replace('&&', '\n')
                image = QImage(self.signatures[self.selected].image_file)
                max_font_size = self.signatures[self.selected].text_font_size

                text_mode = SignerRectItem.TEXT_MODE_STRETCH if self.signatures[self.selected].text_stretch.get_value() else SignerRectItem.TEXT_MODE_KEEP
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
