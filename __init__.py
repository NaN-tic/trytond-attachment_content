# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import ir


def register():
    Pool.register(
        ir.Attachment,
        module='attachment_content', type_='model')
