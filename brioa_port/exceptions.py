class BRIOAException(Exception):
    pass


class InvalidWebcamImageException(BRIOAException):
    pass


class FileHasInvalidLastModifiedDateException(BRIOAException):
    pass
