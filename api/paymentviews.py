from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Payment


@login_required
def payment_history(request):
    payments = Payment.objects.filter(order__user=request.user).select_related('order').order_by('-order__created_at')
    latest_payment = payments.first()
    return render(request, 'customers/payment_history.html', {
        'payments': payments,
        'latest_payment': latest_payment
    })


@require_POST
@login_required
def update_payment_method(request):
    try:
        payment = Payment.objects.filter(order__user=request.user).latest('id')

        card_number = request.POST.get('card_number')
        expiry = request.POST.get('expiry')
        cvv = request.POST.get('cvv')

        # Basic validation
        if not (card_number and expiry and cvv):
            return JsonResponse({'success': False, 'message': 'All fields are required.'})

        # Validate expiry format
        try:
            datetime.strptime(expiry, "%m/%y")
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Invalid expiry date format. Use MM/YY.'})

        # Update card details
        digits = card_number.replace(' ', '')
        if not digits.isdigit() or not 12 <= len(digits) <= 19:
            return JsonResponse({'success': False, 'message': 'Invalid card number.'})
        # Never store full card numbers or CVV (PCI-DSS): keep only the last 4 digits.
        payment.card_number = digits[-4:].rjust(16, '*')
        payment.expiry = expiry
        payment.cvv = ''
        payment.save()

        return JsonResponse({'success': True})
    except Payment.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'No payment method found.'})


@require_POST
@login_required
def delete_payment_method(request):
    payment_id = request.POST.get('payment_id')

    payment = get_object_or_404(Payment, id=payment_id)

    if payment.order.user != request.user:
        return HttpResponseForbidden("You are not allowed to delete this payment method.")

    payment.card_number = ''
    payment.expiry = ''
    payment.cvv = ''
    payment.save()

    return redirect('payment_history')
