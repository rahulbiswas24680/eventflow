from rest_framework.views import exception_handler


def custom_exception_handler(exc, context=None):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Update the structure of the response data.
    if response is not None:
        customized_response = {}
        customized_response['errors'] = []

        for key, value in response.data.items():
            error = {'field': key.capitalize().replace("_", " "), 'message': value}
            customized_response['errors'].append(error)

        response.data = customized_response

    return response