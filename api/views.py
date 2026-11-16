import random

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CustomerForm
from .models import Category, CustomUser, Product, ProductQuestion, Vendor
from .tracking import find_trackable_order


def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def home(request):
    top_vendors = Vendor.objects.annotate(
        product_count=Count('products')
    ).order_by('-product_count')[:4]
    # Works on a fresh database too: missing categories just give empty sections.
    available = Product.objects.filter(is_available=True).select_related('category', 'vendor')
    featured_category = Category.objects.filter(slug='electronics').first()
    electronics_category = featured_category
    electronics_products = available.filter(category__slug="electronics")[:3]
    deals_category = Category.objects.filter(slug="deals").first()
    deals_products = available.filter(category__slug="deals")[:3]
    mens_category = Category.objects.filter(slug="mens-fashion").first()
    mens_products = available.filter(category__slug="mens-fashion")[:3]
    women_category = Category.objects.filter(slug="women-fashion").first()
    women_products = available.filter(category__slug="women-fashion")[:3]
    products = available.filter(category__slug="electronics")
    
    selected_category_id = request.GET.get('category')
    categories = Category.objects.all()
    for vendor in top_vendors:
        vendor.rating_float = float(vendor.average_rating)
    badge_options = {
        'New': 'bg-primary',
        'Popular': 'bg-success',
        'Hot': 'bg-danger',
        'Trending': 'bg-warning text-dark',
        'Top': 'bg-dark'
    }

    for category in categories:
        badge = random.choice(list(badge_options.keys()))
        category.badge = badge
        category.badge_color = badge_options[badge]

    if selected_category_id:
        try:
            selected_category_id = int(selected_category_id)
            products = Product.objects.filter(category__id=selected_category_id, is_available=True)
        except ValueError:
            products = Product.objects.filter(is_available=True)
            selected_category_id = None
    else:
        products = Product.objects.filter(is_available=True)
        selected_category_id = None

    for product in products:
        badge_label = random.choice(list(badge_options.keys()))
        product.badge = badge_label
        product.badge_color = badge_options[badge_label]

    category_chunks = list(chunk_list(list(categories), 5))

    return render(request, 'home.html', {
        'products': products,
        'categories': categories,
        'category_chunks': category_chunks,
        'selected_category_id': selected_category_id,
        'category': featured_category,
        'category_products': products,
        'electronics_category': electronics_category,
        'electronics_products': electronics_products,
        'deals_category': deals_category,
        'deals_products': deals_products,
        'mens_category': mens_category,
        'mens_products': mens_products,
        'women_category': women_category,
        'women_products': women_products,
        'top_vendors': top_vendors,

    })
    
def about_us(request):
    return render(request, 'about_us.html')



def ask_question(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        question_text = request.POST.get('question')
        email = request.POST.get('email')

        product = get_object_or_404(Product, id=product_id)

        # Save question to database
        ProductQuestion.objects.create(
            product=product,
            question=question_text,
            email=email
        )

        # Optional: send an email to site admin
        send_mail(
            subject=f"New Question about {product.name}",
            message=f"From: {email}\n\nQuestion:\n{question_text}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],
            fail_silently=True
        )

        messages.success(request, "Your question has been submitted successfully.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    messages.error(request, "Invalid request.")
    return redirect('/')
def track_order_view(request):
    order = None
    searched = False

    if request.method == 'POST':
        searched = True
        order = find_trackable_order(request)

    return render(request, 'track_order.html', {'order': order, 'searched': searched})
@login_required
def vendor_track_order_view(request):
    order = None
    searched = False

    if request.method == 'POST':
        searched = True
        order = find_trackable_order(request)

    return render(request, 'vendor/track_order.html', {'order': order, 'searched': searched})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def customer_list(request):
    query = request.GET.get('q')
    customers = CustomUser.objects.filter(is_customer=True).exclude(username__startswith="visitor_").order_by("-date_joined")
    if query:
        customers = customers.filter(Q(username__icontains=query) | Q(email__icontains=query))
    paginator = Paginator(customers, 10)
    page = request.GET.get('page')
    customers = paginator.get_page(page)
    return render(request, 'admin/customers_list.html', {'customers': customers})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer created successfully.")
            return redirect('customer_list')
    else:
        form = CustomerForm()
    return render(request, 'admin/customers_form.html', {'form': form, 'title': 'Add Customer'})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def customer_edit(request, pk):
    customer = get_object_or_404(CustomUser, pk=pk)
    form = CustomerForm(request.POST or None, request.FILES or None, instance=customer)
    if form.is_valid():
        form.save()
        messages.success(request, "Customer updated successfully.")
        return redirect('customer_list')
    return render(request, 'admin/customers_form.html', {'form': form, 'title': 'Edit Customer'})

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def customer_delete(request, pk):
    customer = get_object_or_404(CustomUser, pk=pk)
    customer.delete()
    messages.success(request, "Customer deleted successfully.")
    return redirect('customer_list')

def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, is_available=True)
    return render(request, 'products/category_products.html', {
        'category': category,
        'products': products
    })
def vendor_detail(request, vendor_slug):
    vendor = get_object_or_404(Vendor, vendor_slug=vendor_slug)
    products = Product.objects.filter(vendor=vendor, is_available=True)

    # --- Filters ---
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    category_id = request.GET.get('category')
    sort = request.GET.get('sort')

    if min_price:
        products = products.filter(base_price__gte=min_price)
    if max_price:
        products = products.filter(base_price__lte=max_price)
    if category_id:
        products = products.filter(category__id=category_id)

    # --- Sorting ---
    if sort == 'price_low':
        products = products.order_by('base_price')
    elif sort == 'price_high':
        products = products.order_by('-base_price')
    elif sort == 'latest':
        products = products.order_by('-created_at')
    else:
        products = products.order_by('name')  # Default sort

    # --- Social Links ---
    raw_links = [link.strip() for link in vendor.social_links.split(',')] if vendor.social_links else []
    social_links = []
    for link in raw_links:
        if 'facebook.com' in link:
            icon = 'fab fa-facebook'
        elif 'instagram.com' in link:
            icon = 'fab fa-instagram'
        elif 'twitter.com' in link:
            icon = 'fab fa-twitter'
        elif 'linkedin.com' in link:
            icon = 'fab fa-linkedin'
        elif 'youtube.com' in link:
            icon = 'fab fa-youtube'
        else:
            icon = 'fas fa-link'
        social_links.append({'url': link, 'icon': icon})

    # --- Category List for Filter Sidebar ---
    categories = Category.objects.all()

    return render(request, 'vendor/vendor_details.html', {
        'vendor': vendor,
        'social_links': social_links,
        'products': products,
        'categories': categories,
    })
