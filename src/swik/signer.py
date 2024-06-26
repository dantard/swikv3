import contextlib
from random import randint

from pyhanko import stamp
from pyhanko.pdf_utils import text, images
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.layout import InnerScaling, SimpleBoxLayoutRule, AxisAlignment
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign import signers, fields
from pyhanko.sign.fields import VisibleSigSettings
from pyhanko.sign.validation import SignatureCoverageLevel
from pyhanko.sign.validation import validate_pdf_signature


class P12Signer:
    OK = 0
    ERROR_SIGNER_IS_NONE = 1
    ERROR_PDF_DOESNT_EXIST = 2
    ERROR_UNABLE_TO_OPEN_OUTPUT_FILE = 3
    ERROR_SIGNING_FAILED = 4

    def __init__(self, filename, output_filename, p12, password, **kwargs):
        self.p12_file = p12
        self.pwd = password
        self.filename = filename
        self.outf = output_filename
        self.kwargs = kwargs

    def sign(self, page, box):
        signer = signers.SimpleSigner.load_pkcs12(
            self.p12_file, passphrase=str.encode(self.pwd),
        )

        if signer is None:
            return self.ERROR_SIGNER_IS_NONE

        try:
            f = open(self.filename, 'rb')
        except:
            return self.ERROR_PDF_DOESNT_EXIST

        ifw = IncrementalPdfFileWriter(f, strict=False)
        num = randint(10000, 99999)
        fields.append_signature_field(
            ifw, sig_field_spec=fields.SigFieldSpec(
                'Signature_' + str(num),
                box=box,
                on_page=page,
                visible_sig_settings=VisibleSigSettings(
                    rotate_with_page=False,
                    scale_with_page_zoom=True,
                    print_signature=True)
            )
        )

        meta = signers.PdfSignatureMetadata(field_name='Signature_' + str(num))
        sign_text = self.kwargs.get('text', "Digitally Signed")
        bg_image = self.kwargs.get("image", None)
        border = self.kwargs.get("border", 0)
        fontsize = self.kwargs.get('font_size', 11)

        timestamp = self.kwargs.get('timestamp', '%d/%m/%Y')
        text_mode = InnerScaling.SHRINK_TO_FIT if self.kwargs.get('text_stretch') == 1 else InnerScaling.NO_SCALING
        image_mode = InnerScaling.STRETCH_TO_FIT if self.kwargs.get(
            'image_stretch') == 1 else InnerScaling.NO_SCALING

        pdf_signer = signers.PdfSigner(
            meta, signer=signer, stamp_style=stamp.TextStampStyle(
                # the 'signer' and 'ts' parameters will be interpolated by pyHanko, if present
                stamp_text=sign_text,
                text_box_style=text.TextBoxStyle(
                    # font=opentype.GlyphAccumulatorFactory(font) if font is not None else None
                    font_size=fontsize,
                    box_layout_rule=SimpleBoxLayoutRule(
                        x_align=AxisAlignment.ALIGN_MIN,
                        y_align=AxisAlignment.ALIGN_MIN
                    ),
                ),
                background_layout=SimpleBoxLayoutRule(
                    x_align=AxisAlignment.ALIGN_MIN,
                    y_align=AxisAlignment.ALIGN_MAX,
                    inner_content_scaling=image_mode
                ),
                border_width=border,
                background=images.PdfImage(bg_image) if bg_image is not None else None,
                timestamp_format=timestamp,
                inner_content_layout=SimpleBoxLayoutRule(
                    x_align=AxisAlignment.ALIGN_MIN,
                    y_align=AxisAlignment.ALIGN_MAX,
                    inner_content_scaling=text_mode  # InnerScaling.STRETCH_TO_FIT#NO_SCALING
                ),
            ),
        )

        try:
            out_file = open(self.outf, 'wb')
        except:
            return self.ERROR_UNABLE_TO_OPEN_OUTPUT_FILE

        if pdf_signer.sign_pdf(ifw, output=out_file):
            return self.OK

        return self.ERROR_SIGNING_FAILED


def get_signature_info(pdf_path, cert_path):
    with contextlib.redirect_stderr(None):
        # root_cert = load_cert_from_pemder(cert_path)
        # vc = ValidationContext(trust_roots=[root_cert])
        result = []
        with open(pdf_path, 'rb') as doc:
            r = PdfFileReader(doc, False)
            for sig in r.embedded_signatures:
                status = validate_pdf_signature(sig)  # , vc)
                data = status.signing_cert.subject.human_friendly.split(', ')
                info = {}
                all_fields = []
                for field in data:
                    if ";" in field:
                        other_fields = field.split('; ')
                        print("other_fields", other_fields)
                        all_fields.extend(other_fields)
                    else:
                        all_fields.append(field)

                for data in all_fields:
                    data = data.split(': ')
                    if len(data) == 2:
                        k, v = data
                        info[k] = v

                info.update({'Valid': 'Yes' if status.valid else 'No',
                             'Intact': 'Yes' if status.intact else 'No',
                             'Coverage': 'Whole file' if status.coverage == SignatureCoverageLevel.ENTIRE_FILE else 'Partial ' + status.coverage.name,
                             'Date': status.signer_reported_dt.isoformat(),
                             })
                result.append(info)

    return result
