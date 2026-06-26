from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import *

import datetime
import re


@login_required(login_url="login")
def checkout_view(request):

    cart = Cart.get_or_create_cart(request)

    if not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("cart_view")

    if request.method == "POST":

        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        zip_code = request.POST.get("zip_code", "").strip()

        card_number = request.POST.get("card_number", "").strip()
        expiry = request.POST.get("expiry", "").strip()
        cvv = request.POST.get("cvv", "").strip()

        form_data = {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "address": address,
            "city": city,
            "zip_code": zip_code,
            "card_number": card_number,
            "expiry": expiry,
            "cvv": cvv,
        }

        errors = {}

        # ---------------------------
        # Customer Validation
        # ---------------------------

        if not full_name:
            errors["full_name"] = "Full name is required."

        if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors["email"] = "Valid email is required."

        if not phone or not re.match(r"^[0-9+\-\s]{10,15}$", phone):
            errors["phone"] = "Valid phone number is required."

        if not address:
            errors["address"] = "Address is required."

        if not city:
            errors["city"] = "City is required."

        if not zip_code.isdigit():
            errors["zip_code"] = "Valid zip code is required."

        # ---------------------------
        # Card Validation
        # ---------------------------

        if not card_number.isdigit() or len(card_number) != 16:
            errors["card_number"] = "Card number must be 16 digits."

        elif not card_number.startswith(("4", "5")):
            errors["card_number"] = (
                "Only Visa and MasterCard are accepted."
            )

        if not cvv.isdigit() or len(cvv) not in [3, 4]:
            errors["cvv"] = "CVV must be 3 or 4 digits."

        # ---------------------------
        # Expiry Validation
        # ---------------------------

        if not expiry or not re.match(
            r"^(0[1-9]|1[0-2])\/\d{2}$",
            expiry,
        ):
            errors["expiry"] = "Expiry must be MM/YY."

        else:
            try:

                exp_month, exp_year = map(
                    int,
                    expiry.split("/")
                )

                exp_year += 2000

                exp_date = datetime.datetime(
                    exp_year,
                    exp_month,
                    1
                )

                now = datetime.datetime.now()

                if exp_date < now.replace(day=1):
                    errors["expiry"] = "Card has expired."

            except ValueError:
                errors["expiry"] = "Invalid expiry date."

        # ---------------------------
        # Return Errors
        # ---------------------------

        if errors:

            for field, error in errors.items():
                messages.error(request, error)

            return render(
                request,
                "purchase/checkout.html",
                {
                    "cart": cart,
                    "errors": errors,
                    "form_data": form_data,
                },
            )

        # ---------------------------
        # Logged-in User
        # ---------------------------

        user = request.user

        # ---------------------------
        # Create Order
        # ---------------------------

        order = Order.objects.create(
            user=user,
            full_name=full_name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            zip_code=zip_code,
            total_amount=cart.total_amount(),
            status="Pending",
        )

        # ---------------------------
        # Create Order Items
        # ---------------------------

        for item in cart.items.all():

            OrderItem.objects.create(
                order=order,
                product=item.product,
                color=item.color.color_name
                if item.color else "",
                size=item.size.size_label
                if item.size else "",
                price=item.total_price / item.quantity,
                quantity=item.quantity,
            )

        # ---------------------------
        # Payment Record
        # ---------------------------

        Payment.objects.create(
            order=order,
            card_number=card_number[-4:].rjust(
                16,
                "*"
            ),
            expiry=expiry,
            cvv="***",
            payment_status="Success",
        )

        # ---------------------------
        # Confirmation Email
        # ---------------------------

        html_content = render_to_string(
            "purchase/order_confirmation.html",
            {
                "order": order,
                "items": order.items.all(),
            },
        )

        email_message = EmailMultiAlternatives(
            subject=f"MarketHub - Order #{order.id}",
            body="Thank you for shopping with MarketHub.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[order.email],
        )

        email_message.attach_alternative(html_content, "text/html")

        email_message.send(fail_silently=False)

    
        # ---------------------------
        # Clear Cart
        # ---------------------------

        cart.items.all().delete()

        messages.success(
            request,
            f"Order #{order.id} placed successfully!"
        )

        return redirect(
            "order_confirmation",
            order_id=order.id,
        )

    return render(
        request,
        "purchase/checkout.html",
        {
            "cart": cart,
            "user": request.user,
        },
    )


@login_required(login_url="login")
def order_confirmation(request, order_id):
    

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
    )

    return render(
        request,
        "purchase/order_success.html",
        {
            "order": order,
        },
    )