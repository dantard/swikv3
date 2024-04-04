import os
import shutil
import sys
import tempfile
import threading
import time
import traceback

from PyQt5.QtCore import QObject, QStandardPaths
from PyQt5.QtGui import QFont, QFontDatabase
from fontTools import ttLib


class FontManager(QObject):
    weight_class_mapping = {
        100: QFont.Thin,
        200: QFont.ExtraLight,
        300: QFont.Light,
        400: QFont.Normal,
        500: QFont.Medium,
        600: QFont.DemiBold,
        700: QFont.Bold,
        800: QFont.ExtraBold,
        900: QFont.Black
    }

    base14_fonts = [
        {'full_name': 'Helvetica', 'path': None, 'family': 'Helvetica', 'weight': 400, 'nickname': 'Helvetica', },
        {'full_name': 'Helvetica-Bold', 'path': None, 'family': 'Helvetica', 'weight': 700, 'nickname': 'Helvetica-Bold', },
        {'full_name': 'Helvetica-Oblique', 'path': None, 'family': 'Helvetica', 'weight': 400, 'nickname': 'Helvetica-Oblique', },
        {'full_name': 'Helvetica-BoldOblique', 'path': None, 'family': 'Helvetica', 'weight': 700, 'nickname': 'Helvetica-BoldOblique', },
        {'full_name': 'Courier', 'path': None, 'family': 'Courier', 'weight': 400, 'nickname': 'Courier', },
        {'full_name': 'Courier-Bold', 'path': None, 'family': 'Courier', 'weight': 700, 'nickname': 'Courier-Bold', },
        {'full_name': 'Courier-Oblique', 'path': None, 'family': 'Courier', 'weight': 400, 'nickname': 'Courier-Oblique', },
        {'full_name': 'Courier-BoldOblique', 'path': None, 'family': 'Courier', 'weight': 700, 'nickname': 'Courier-BoldOblique', },
        {'full_name': 'Times-Roman', 'path': None, 'family': 'Times', 'weight': 400, 'nickname': 'Times-Roman', },
        {'full_name': 'Times-Bold', 'path': None, 'family': 'Times', 'weight': 700, 'nickname': 'Times-Bold', },
        {'full_name': 'Times-Italic', 'path': None, 'family': 'Times', 'weight': 400, 'nickname': 'Times-Italic', },
        {'full_name': 'Times-BoldItalic', 'path': None, 'family': 'Times', 'weight': 700, 'nickname': 'Times-BoldItalic', },
        {'full_name': 'Symbol', 'path': None, 'family': 'Symbol', 'weight': 400, 'nickname': 'Symbol', },
        {'full_name': 'ZapfDingbats', 'path': None, 'family': 'ZapfDingbats', 'weight': 400, 'nickname': 'ZapfDingbats', }
    ]

    system_fonts = []
    swik_fonts = []

    def __init__(self, renderer):
        super().__init__()
        self.renderer = renderer
        self.document_fonts = []
        self.font_dir = None
        for base14 in FontManager.base14_fonts:
            base14['subset'] = False
            base14['path'] = '@base14/' + base14['nickname']
            base14['italic'] = base14['nickname'].endswith('Oblique') or base14['nickname'].endswith('Italic')

    def update_document_fonts(self):
        self.document_fonts.clear()
        if self.font_dir is not None:
            shutil.rmtree(self.font_dir, ignore_errors=True)

        self.font_dir = tempfile.mkdtemp()
        print("-----------font dir: ", self.font_dir)
        self.renderer.save_fonts(self.font_dir)
        fonts = self.get_fonts([self.font_dir])

        print("-----------Fonts: ", fonts)
        for f in fonts:
            self.document_fonts.append(f)

    @staticmethod
    def get_system_fonts():
        return FontManager.system_fonts

    def get_document_fonts(self):
        fonts = self.document_fonts
        return fonts

    def get_fully_embedded_fonts(self):
        return [f for f in self.document_fonts if not f['subset']]

    def get_subset_fonts(self):
        return [f for f in self.document_fonts if f['subset']]

    def get_all_available_fonts(self):
        return FontManager.base14_fonts + FontManager.swik_fonts + FontManager.system_fonts

    def get_font_info_from_name(self, name):
        for f in self.document_fonts:
            if f['nickname'] == name:
                return f

        for f in FontManager.base14_fonts:
            if f['nickname'] == name:
                return f

        for f in FontManager.swik_fonts:
            if f['nickname'] == name:
                return f

        for f in FontManager.system_fonts:
            # print("System font: ", f['nickname'])
            if f['nickname'] == name:
                return f

        return None

    @staticmethod
    def update_swik_fonts():
        FontManager.swik_fonts = FontManager.get_fonts("fonts")

    @staticmethod
    def get_swik_fonts():
        return FontManager.swik_fonts

    @staticmethod
    def get_base14_fonts():
        return FontManager.base14_fonts

    @staticmethod
    def update_system_fonts():
        print("Starting thread")
        threading.Thread(target=FontManager.update_system_fonts_thread).start()

    @staticmethod
    def update_system_fonts_thread():
        time.sleep(1)
        FontManager.system_fonts = FontManager.get_system_font_list()
        print("System fonts updated")

    @staticmethod
    def map_weigth_to_qfont(weight):
        return FontManager.weight_class_mapping[weight]

    @staticmethod
    def get_font_info(path):
        if path.startswith('@base14'):
            nickname = path[8:]
            for f in FontManager.base14_fonts:
                if f['nickname'] == nickname:
                    return f
            return None

        font = ttLib.TTFont(path)
        if font.has_key('name'):
            family_name = font['name'].getDebugName(1)
            full_name = font['name'].getDebugName(4)
            nickname = font['name'].getDebugName(6)
            modifiers = str(font['name'].getDebugName(2))
            modifiers = modifiers.lower()
            if font.has_key('OS/2'):
                os2_table = font['OS/2']
                weight_class = os2_table.usWeightClass
            else:
                weight_class = 400

            return {'full_name': full_name, 'path': path, 'family': family_name, 'weight': weight_class, 'nickname': nickname,
                    'italic': 'italic' in modifiers or 'oblique' in modifiers, 'subset': '+' in path}
        else:
            # May be encrypted
            return None

    @staticmethod
    def get_qfont_from_ttf(filename, size=11):
        if filename.startswith('@base14'):
            nickname = filename[8:]
            font_info = next((f for f in FontManager.base14_fonts if f['nickname'] == nickname), FontManager.base14_fonts[0])
            family = font_info['family']
        else:
            idx = QFontDatabase.addApplicationFont(filename)
            families = QFontDatabase.applicationFontFamilies(idx)
            if len(families) > 0:
                family = families[0]
                font_info = FontManager.get_font_info(filename)
            else:
                font_info = FontManager.base14_fonts[0]
                family = font_info['family']

        weight = FontManager.weight_class_mapping.get(font_info['weight'], QFont.Normal)
        font = QFont(family)
        font.setWeight(weight)
        font.setItalic(font_info['italic'])
        font.setPointSizeF(size)
        return font

    @staticmethod
    def get_fonts(font_paths):
        print("get fonts, ", font_paths)
        fonts = {}
        if type(font_paths) is not list:
            font_paths = [font_paths]
        for fpath in font_paths:  # go through all font paths
            if os.path.isdir(fpath):
                walk = os.walk(fpath)
                for root, dirs, files in walk:
                    for filename in files:
                        path = os.path.join(root, filename)
                        try:
                            # print("Font path: ", path)
                            info = FontManager.get_font_info(path)
                            if info is not None:
                                fonts.update({info.get('nickname', None): info})
                        except:
                            pass
                            # traceback.print_exc()
                            # print("Error reading font: ", path)
        fonts = list(fonts.values())
        fonts.sort(key=lambda x: x['full_name'])
        return fonts

    @staticmethod
    def get_system_font_list():
        font_paths = QStandardPaths.standardLocations(QStandardPaths.FontsLocation)
        return FontManager.get_fonts(font_paths)
