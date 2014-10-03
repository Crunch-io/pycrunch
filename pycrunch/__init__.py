from pycrunch import cubes
from pycrunch import elements
from pycrunch import shoji
from pycrunch import importing
from pycrunch.lemonpy import ClientError, ServerError, urljoin

Session = elements.ElementSession

__all__ = [
    'cubes',
    'elements',
    'shoji',
    'importing',
    'ClientError', 'ServerError', 'CrunchError'
    'Session',
    'urljoin'
]


class CrunchError(elements.Element):

    element = "crunch:error"


class CrunchTable(elements.Document):

    element = "crunch:table"
