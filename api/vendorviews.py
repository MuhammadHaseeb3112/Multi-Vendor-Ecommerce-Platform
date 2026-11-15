from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AdminVendorForm, VendorForm
from .models import Vendor

User = get_user_model()





def is_admin(user):
    return user.is_superuser


@login_required
@user_passes_test(is_admin)
def vendor_list(request):
    vendors = Vendor.objects.select_related('user').order_by('-created_at')
    return render(request, 'admin/vendor_list.html', {'vendors': vendors})


@login_required
@user_passes_test(is_admin)
def vendor_create(request):
    if request.method == 'POST':
        form = AdminVendorForm(request.POST, request.FILES)
        if form.is_valid():
            vendor = form.save()
            vendor.user.is_vendor = True
            vendor.user.save(update_fields=['is_vendor'])
            messages.success(request, 'Vendor created successfully.')
            return redirect('vendor_list')
    else:
        form = AdminVendorForm()
    return render(request, 'admin/vendor_form.html', {'form': form, 'title': 'Create Vendor'})


@login_required
@user_passes_test(is_admin)
def vendor_edit(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk)
    if request.method == 'POST':
        form = VendorForm(request.POST, request.FILES, instance=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vendor updated successfully.')
            return redirect('vendor_list')
    else:
        form = VendorForm(instance=vendor)
    return render(request, 'admin/vendor_form.html', {'form': form, 'title': 'Edit Vendor'})


@login_required
@user_passes_test(is_admin)
def vendor_delete(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk)
    if request.method == 'POST':
        vendor.delete()
        messages.success(request, 'Vendor deleted successfully.')
        return redirect('vendor_list')
    return render(request, 'admin/vendor_confirm_delete.html', {'vendor': vendor})
