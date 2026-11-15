from .models import Cart

class CartMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Media/static files don't need a cart (and parallel image requests
        # used to create duplicate carts).
        if request.path.startswith(('/media/', '/static/')):
            return self.get_response(request)

        # Ensure session exists for anonymous users
        if not request.session.session_key:
            request.session.create()

        if request.user.is_authenticated:
            # Get or create cart for logged-in user
            cart = Cart.for_user(request.user)
        else:
            # Get or create cart for anonymous user by session key
            session_key = request.session.session_key
            cart, _ = Cart.objects.get_or_create(session_key=session_key)

        # Attach the cart instance to the request object
        request.cart = cart

        # Continue processing request
        response = self.get_response(request)
        return response
