from django.middleware.csrf import CsrfViewMiddleware


class RelaxedCsrfMiddleware(CsrfViewMiddleware):
    """
    Drop-in replacement for Django's CsrfViewMiddleware that handles
    in-app browsers (WhatsApp, Instagram, etc.) which strip the Referer
    header or send Origin: null on HTTPS form submissions.

    The cookie-vs-token comparison is UNCHANGED — only the HTTPS
    Referer/Origin header check is made permissive for same-host requests.
    """

    def process_view(self, request, callback, callback_args, callback_kwargs):
        # WKWebView (iOS in-app browsers) often sends Origin: null.
        # Removing it lets us fall through to the Referer check below.
        if request.META.get('HTTP_ORIGIN') == 'null':
            request.META.pop('HTTP_ORIGIN', None)
        return super().process_view(request, callback, callback_args, callback_kwargs)

    def _check_referer(self, request):
        # When the Referer header is absent (stripped by privacy-focused
        # browsers or in-app WebViews), synthesise one from the current host
        # so the parent's domain-match logic can still run.
        if not request.META.get('HTTP_REFERER'):
            request.META['HTTP_REFERER'] = f"https://{request.get_host()}/"
        return super()._check_referer(request)
