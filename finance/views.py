from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from .services import get_dashboard_stats


@staff_member_required
def dashboard(request):
    stats = get_dashboard_stats()
    return render(request, "finance/dashboard.html", {"stats": stats})
