import base64
from io import BytesIO

import barcode
import qrcode
from barcode.writer import ImageWriter
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import Order


def receipt_input_view(request):
    return render(request, 'receipt_input.html')

@login_required
def generate_receipt(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    user = request.user
    is_vendor_of_order = hasattr(user, "vendor") and order.items.filter(product__vendor=user.vendor).exists()
    if not (user.is_staff or order.user_id == user.id or is_vendor_of_order):
        raise Http404("Order not found")

    # QR Code generation
    qr = qrcode.make(request.build_absolute_uri(reverse('track_order')))
    qr_io = BytesIO()
    qr.save(qr_io, format='PNG')
    qr_base64 = base64.b64encode(qr_io.getvalue()).decode()
    qr_url = f'data:image/png;base64,{qr_base64}'

    # Barcode generation
    code128 = barcode.get('code128', str(order.id), writer=ImageWriter())
    bar_io = BytesIO()
    code128.write(bar_io)
    bar_base64 = base64.b64encode(bar_io.getvalue()).decode()
    bar_url = f'data:image/png;base64,{bar_base64}'

    return render(request, 'order_receipt.html', {
        'order': order,
        'qr_code_url': qr_url,
        'barcode_url': bar_url,
        'width': 58,  # or 58 for thermal printer
    })
