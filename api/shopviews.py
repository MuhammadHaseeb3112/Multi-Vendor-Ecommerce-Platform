from django.db.models import Q
from django.shortcuts import render

from .models import Product, categories_with_products


def _category_id(value):
    """The ?category= value as an int, or None when missing or not a number."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def shop_view(request):
    products = Product.objects.filter(is_available=True).select_related('category')
    categories = categories_with_products()
    selected_category = _category_id(request.GET.get('category'))
    search_query = (request.GET.get('q') or '').strip()
    sort_by = request.GET.get('sort')

    # Filter by category
    if selected_category:
        products = products.filter(category_id=selected_category)

    # Search: product name, brand, short description or category name
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(brand__icontains=search_query)
            | Q(short_details__icontains=search_query)
            | Q(category__name__icontains=search_query)
        )

    # Sorting
    if sort_by == 'price_low':
        products = products.order_by('base_price')
    elif sort_by == 'price_high':
        products = products.order_by('-base_price')

    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'search_query': search_query,
    }
    return render(request, 'shop.html', context)
