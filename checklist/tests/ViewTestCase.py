from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase


class ViewTestCase(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.req_factory = RequestFactory()

        # self.user = User.objects.create_user(
        #    username='jacob', email='jacob@…', password='top_secret')

    def create_request_with_session(
        self, path, session_data=None, referer=None, request_data=None
    ):
        # Create a request using the factory
        request = (
            self.req_factory.post(path, data=request_data)
            if request_data
            else self.req_factory.get(path)
        )

        # Add session support to the request
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)

        # Set session data if provided
        if session_data:
            request.session.update(session_data)
            request.session.save()

        # Set the referer if provided
        if referer:
            request.META["HTTP_REFERER"] = referer

        return request
