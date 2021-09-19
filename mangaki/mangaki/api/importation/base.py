from rest_framework.exceptions import APIException


class ImportMechanismUnavailable(APIException):
    status_code = 503
    default_detail = 'This import mechanism is temporarily unavailable, try again later.'
    default_code = 'import_unavailable'
