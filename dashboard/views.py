from django.contrib.auth import login
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required
from reports.models import Report
from reports.choices import ReportStatus
from organizations.models import Organization, OrganizationMember
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib import messages
from .forms import LoginForm


User = get_user_model()


@require_http_methods(["GET", "POST"])
def sign_in(request):
    if request.user.is_authenticated:
        # login bo'lib bo'lgan bo'lsa, dashboardga yuboramiz
        return redirect("dashboard:home")

    form = LoginForm(request.POST or None, request=request)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)

        # remember_me: yoqilmagan bo'lsa browser yopilganda session tugaydi
        remember = form.cleaned_data.get("remember_me")
        if not remember:
            request.session.set_expiry(0)

        next_url = request.GET.get("next")
        if next_url:
            return redirect(next_url)

        return redirect("dashboard:home")

    return render(request, "auth/sign-in.html", {"form": form})



@login_required
def home(request):
    return render(request, "superadmin/dashboard.html")


@login_required
def complaints_list(request):
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()

    per_page_raw = request.GET.get("per_page") or "10"
    try:
        per_page = int(per_page_raw)
    except ValueError:
        per_page = 10
    if per_page not in (10, 25, 50, 100):
        per_page = 10

    qs = Report.objects.all().order_by("-created_at")

    if q:
        qs = qs.filter(
            Q(description__icontains=q) |
            Q(id__icontains=q)
        )

    if status:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, per_page)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    status_choices = ReportStatus.choices

    context = {
        "page_obj": page_obj,
        "paginator": paginator,
        "q": q,
        "status": status,
        "per_page": per_page,
        "status_choices": status_choices,
    }
    return render(request, "superadmin/complaints.html", context)



@login_required
def organizations_list(request):
    q = (request.GET.get("q") or "").strip()
    is_active = (request.GET.get("is_active") or "").strip()  # "1" / "0" / ""

    per_page_raw = request.GET.get("per_page") or "10"
    try:
        per_page = int(per_page_raw)
    except ValueError:
        per_page = 10
    if per_page not in (10, 25, 50, 100):
        per_page = 10

    qs = (
        Organization.objects
        .annotate(members_count=Count("members"))
        .order_by("-created_at")
    )

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q)
        )

    if is_active == "1":
        qs = qs.filter(is_active=True)
    elif is_active == "0":
        qs = qs.filter(is_active=False)

    paginator = Paginator(qs, per_page)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    return render(request, "superadmin/organizations_list.html", {
        "page_obj": page_obj,
        "q": q,
        "is_active": is_active,
        "per_page": per_page,
    })


@login_required
def organization_detail(request, pk: int):
    org = get_object_or_404(Organization, pk=pk)

    # members filter/search
    mq = (request.GET.get("mq") or "").strip()
    role = (request.GET.get("role") or "").strip()  # "admin"/"staff"/""

    members_qs = (
        OrganizationMember.objects
        .filter(organization=org)
        .select_related("user")
        .order_by("-joined_at")
    )

    if mq:
        members_qs = members_qs.filter(
            Q(user__username__icontains=mq) |
            Q(user__email__icontains=mq) |
            Q(user__first_name__icontains=mq) |
            Q(user__last_name__icontains=mq)
        )

    if role in ("admin", "staff"):
        members_qs = members_qs.filter(role=role)

    paginator = Paginator(members_qs, 10)
    page_number = request.GET.get("page") or 1
    members_page = paginator.get_page(page_number)

    return render(request, "superadmin/organization_detail.html", {
        "org": org,
        "members_page": members_page,
        "mq": mq,
        "role": role,
        "role_choices": OrganizationMember.ROLE_CHOICES,
    })


@login_required
def users_list(request):
    q = (request.GET.get("q") or "").strip()
    is_active = (request.GET.get("is_active") or "").strip()  # "1"/"0"/""
    is_staff = (request.GET.get("is_staff") or "").strip()    # "1"/"0"/""

    per_page_raw = request.GET.get("per_page") or "10"
    try:
        per_page = int(per_page_raw)
    except ValueError:
        per_page = 10
    if per_page not in (10, 25, 50, 100):
        per_page = 10

    qs = User.objects.all().order_by("-date_joined")

    if q:
        qs = qs.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)
        )

    if is_active == "1":
        qs = qs.filter(is_active=True)
    elif is_active == "0":
        qs = qs.filter(is_active=False)

    if is_staff == "1":
        qs = qs.filter(is_staff=True)
    elif is_staff == "0":
        qs = qs.filter(is_staff=False)

    paginator = Paginator(qs, per_page)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    return render(request, "superadmin/users_list.html", {
        "page_obj": page_obj,
        "q": q,
        "is_active": is_active,
        "is_staff": is_staff,
        "per_page": per_page,
    })


@login_required
def user_detail(request, pk: int):
    user = get_object_or_404(User, pk=pk)

    memberships = (
        OrganizationMember.objects
        .filter(user=user)
        .select_related("organization")
        .order_by("-joined_at")
    )

    return render(request, "superadmin/user_detail.html", {
        "u": user,
        "memberships": memberships,
    })


def _get_user_phone(u) -> str:
    """
    User modelda telefon field nomi har xil bo‘lishi mumkin.
    Shu listdagi nomlardan qaysi biri bo‘lsa, o‘shani chiqaramiz.
    """
    for attr in ("phone_number", "phone", "mobile", "tel", "phoneNumber"):
        if hasattr(u, attr):
            val = getattr(u, attr)
            if val:
                return str(val)
    return ""


@login_required
def report_detail(request, pk):
    report = get_object_or_404(
        Report.objects.select_related("user", "organization").prefetch_related(
            "attachments",
            "reads",
            "assignments",
            "redirects",
        ),
        pk=pk
    )

    # ✅ Permission:
    # - Superadmin hammasini ko'radi
    # - Organization admin/staff faqat o'z organization reportlarini ko'radi
    if not request.user.is_superuser:
        if not report.organization_id:
            # organization yo'q reportni org admin ko'rmasin
            raise Http404()

        is_member = OrganizationMember.objects.filter(
            user=request.user,
            organization_id=report.organization_id
        ).exists()

        if not is_member:
            raise Http404()

        # ✅ READ log: statusni o'zgartirmaymiz, faqat o'qilganini log qilamiz
        ReportRead.objects.get_or_create(
            report=report,
            organization_id=report.organization_id,
            defaults={"read_by": request.user},
        )

    phone = _get_user_phone(report.user)

    return render(request, "report_detail.html", {
        "report": report,
        "phone": phone,
    })

