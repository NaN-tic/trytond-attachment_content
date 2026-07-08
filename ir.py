# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import logging
import mimetypes
import tempfile

from magic import Magic
from markitdown import (FileConversionException, MarkItDown,
                        UnsupportedFormatException)
from trytond.model import ModelView, fields
from trytond.pool import PoolMeta

logger = logging.getLogger(__name__)


class Attachment(ModelView, metaclass=PoolMeta):
    "Attachment"
    __name__ = 'ir.attachment'

    mimetype = fields.Char('Mimetype', readonly=True)
    content = fields.Text('Content', readonly=True)
    data_updated = fields.Boolean('Data Updated', readonly=True)

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for values in vlist:
            cls.calculate_fields(values)

        records = super().create(vlist)
        cls.__queue__.extract_content(records)
        return records

    @classmethod
    def write(cls, *args):
        actions = iter(args)
        new_args = []
        for records, values in zip(actions, actions):
            values = values.copy()
            new_args += [records, values]
            cls.calculate_fields(values)
            if values.get('data_updated'):
                cls.__queue__.extract_content(records)

        super().write(*new_args)

    @staticmethod
    def calculate_fields(dictionary):
        if 'data' not in dictionary:
            return
        dictionary.setdefault('data_updated', True)

        data = dictionary['data']
        if not data:
            dictionary.setdefault('content', None)
            dictionary.setdefault('mimetype', None)
        else:
            try:
                mimetype = Magic(mime=True).from_buffer(data)
            except TypeError:
                mimetype = None
            dictionary.setdefault('mimetype', mimetype)

    @classmethod
    def extract_content(cls, records):
        converter = MarkItDown()

        for record in records:
            if not record.data_updated:
                continue
            record.data_updated = False
            if not record.data:
                record.content = None
                continue

            if not record.mimetype:
                if '.' not in record.name:
                    continue
                extension = record.name.rsplit('.', 1)[-1]
            else:
                extension = mimetypes.guess_extension(record.mimetype)
            if not extension:
                continue
            extension = extension.lower()
            try:
                # MarkItDown convert_stream does not handle these payloads
                # reliably, so use a temporary file path instead.
                with tempfile.NamedTemporaryFile(
                        mode='wb', suffix=extension) as temp_file:
                    temp_file.write(record.data)
                    temp_file.flush()
                    result = converter.convert(temp_file.name)
                    record.content = result.text_content.replace('\x00', '')
            except (FileConversionException, UnsupportedFormatException) as e:
                logger.warning(
                    'Could not extract content using MarkItDown: %s', e)
                record.content = None
        cls.save(records)
