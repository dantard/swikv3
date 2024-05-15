#!/usr/bin/env python3
import fitz
from pymupdf import Widget, Rect
from pymupdf.mupdf import PDF_WIDGET_TYPE_RADIOBUTTON, PDF_WIDGET_TYPE_CHECKBOX

doc = fitz.open()
page = doc.new_page()

widget = Widget()
widget.field_name = "radio"
widget.rect = Rect(100, 100, 120, 120)
widget.field_type = PDF_WIDGET_TYPE_RADIOBUTTON
widget.field_label = "radio1"
widget.field_value = False
page.add_widget(widget)
widget.

widget = Widget()
widget.field_name = "radio"
widget.rect = Rect(200, 200, 220, 220)
widget.field_type = PDF_WIDGET_TYPE_RADIOBUTTON
widget.field_value = False
widget.field_label = "radio2"
page.add_widget(widget)
widget.update()

print("xref", widget.xref)


#page = doc[0]
widgets = page.widgets()

for w in widgets:
    if w.field_label == "radio2":
        w.field_value = True
        w.update()


doc.save("radio_button_pdf.pdf")
doc.close()

