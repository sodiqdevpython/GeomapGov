from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q, Exists, OuterRef
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from users.models import User
from users.choices import UserChoices
from reports.models import Report
from organizations.models import Organization, OrganizationMember
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
import json


def org_admin_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        print(request.user.user_type)
        print(getattr(request.user, "user_type", None))
        if getattr(request.user, "user_type", None) != UserChoices.DISPATCHER:
            return HttpResponseForbidden("Forbidden")
        return view_func(request, *args, **kwargs)
    return _wrapped


def get_my_organization(user: User):
    """
    Org admin qaysi organization ga tegishli ekanini topish.
    Sizning loyihangizda qanday bog'langan bo'lsa shunga moslab o'zgartirasiz.
    """
    # 1) user.organization FK bo'lsa:
    org = getattr(user, "organization", None)
    if org:
        return org

    # 2) user.organizations m2m bo'lsa:
    orgs = getattr(user, "organizations", None)
    if orgs and hasattr(orgs, "first"):
        return orgs.first()

    return None


def get_org_members_manager(org: Organization):
    """
    Organization ichidagi reporterlar manager'i.
    Sizda qaysi field bo'lsa shuni qoldiring: members/users/reporters...
    """
    for attr in ("members", "users", "reporters"):
        manager = getattr(org, attr, None)
        if manager is not None and hasattr(manager, "all") and hasattr(manager, "add") and hasattr(manager, "remove"):
            return manager
    raise AttributeError(
        "Organization modelida reporterlar uchun ManyToMany topilmadi. "
        "Organization.members yoki Organization.users kabi field qo'shing."
    )


@login_required
def org_users_list(request):
    # =========================
    # 1. Organization ADMIN tekshiruvi
    # =========================
    admin_membership = (
        OrganizationMember.objects
        .filter(user=request.user, role__iexact=OrganizationMember.ROLE_ADMIN)
        .select_related("organization")
        .first()
    )

    if not admin_membership:
        # (diagnostika uchun) userning barcha membershiplarini ko'rsatamiz
        my_roles = list(
            OrganizationMember.objects
            .filter(user=request.user)
            .select_related("organization")
            .values_list("organization__name", "role")
        )
        return HttpResponseForbidden(f"Siz organization admin emassiz. Membershiplar: {my_roles}")

    org = admin_membership.organization

    # =========================
    # 2. POST: biriktirish / chiqarish
    # =========================
    if request.method == "POST":
        action = request.POST.get("action")
        user_id = request.POST.get("user_id")

        target = get_object_or_404(User, pk=user_id)

        if action == "assign":
            # faqat reporter
            if target.user_type != UserChoices.REPORTER:
                messages.error(request, "Faqat reporterlarni biriktirish mumkin")
                return redirect("dashboard:org_users")

            # oldin report yuborgan bo‘lsa -> YO‘Q
            if Report.objects.filter(user=target).exists():
                messages.error(
                    request,
                    "Bu reporter oldin report yuborgan, biriktirib bo‘lmaydi"
                )
                return redirect("dashboard:org_users")

            # allaqachon a’zo bo‘lsa
            if OrganizationMember.objects.filter(
                user=target,
                organization=org
            ).exists():
                messages.info(request, "Bu reporter allaqachon a’zo")
                return redirect("dashboard:org_users")

            with transaction.atomic():
                OrganizationMember.objects.create(
                    user=target,
                    organization=org,
                    role=OrganizationMember.ROLE_STAFF
                )
                # ✅ darrov executer ga o‘tkazamiz
                target.user_type = UserChoices.EXECUTOR   # <-- sizdagi choices nomiga mos bo‘lsin
                target.save(update_fields=["user_type"])
            messages.success(request, "Reporter organizationga biriktirildi")

        elif action == "remove":
            with transaction.atomic():
                OrganizationMember.objects.filter(user=target, organization=org).delete()

                # ✅ agar boshqa orglarda ham a’zo bo‘lmasa reporterga qaytaramiz
                still_member_somewhere = OrganizationMember.objects.filter(user=target).exists()
                if not still_member_somewhere:
                    target.user_type = UserChoices.REPORTER
                    target.save(update_fields=["user_type"])

            messages.success(request, "Foydalanuvchi organizationdan chiqarildi")

        return redirect("dashboard:org_users")

    # =========================
    # 3. TAB
    # =========================
    tab = request.GET.get("tab", "reporters")

    # =========================
    # 4. REPORTERS TAB
    # =========================
    rq = (request.GET.get("rq") or "").strip()
    rpage = request.GET.get("rpage", 1)

    reporters_qs = User.objects.filter(
        user_type=UserChoices.REPORTER
    ).annotate(
        has_reports=Exists(
            Report.objects.filter(user_id=OuterRef("pk"))
        ),
        is_member=Exists(
            OrganizationMember.objects.filter(
                user_id=OuterRef("pk"),
                organization=org
            )
        )
    ).filter(
        has_reports=False,   # ✅ report yuborganlar ko'rinmaydi
        is_member=False      # ✅ allaqachon a'zo bo'lganlar ham ko'rinmaydi
    ).order_by("-date_joined")


    if rq:
        reporters_qs = reporters_qs.filter(
            Q(username__icontains=rq) |
            Q(first_name__icontains=rq) |
            Q(last_name__icontains=rq)
        )

    reporters_page_obj = Paginator(reporters_qs, 10).get_page(rpage)

    # =========================
    # 5. MEMBERS TAB
    # =========================
    mq = (request.GET.get("mq") or "").strip()
    mpage = request.GET.get("mpage", 1)

    members_qs = User.objects.filter(
        organization_memberships__organization=org
    ).exclude(
        pk=request.user.pk
    ).order_by("-date_joined")


    if mq:
        members_qs = members_qs.filter(
            Q(username__icontains=mq) |
            Q(first_name__icontains=mq) |
            Q(last_name__icontains=mq)
        )

    members_page_obj = Paginator(members_qs, 10).get_page(mpage)

    return render(request, "organization_admin/users_list.html", {
        "org": org,
        "tab": tab,
        "reporters_page_obj": reporters_page_obj,
        "members_page_obj": members_page_obj,
        "rq": rq,
        "mq": mq,
    })


def _org_admin_membership(user):
    return OrganizationMember.objects.filter(
        user=user,
        role=OrganizationMember.ROLE_ADMIN
    ).select_related("organization").first()


def _full_name(u):
    s = f"{u.first_name} {u.last_name}".strip()
    return s if s else u.username


def _staff_role_list():
    """
    Sizdagi OrganizationMember role constantlari turlicha bo‘lishi mumkin.
    Shuning uchun bor bo‘lsa qo‘shib ketamiz.
    """
    roles = []

    # Admin / Staff
    for attr in ("ROLE_ADMIN", "ROLE_STAFF"):
        if hasattr(OrganizationMember, attr):
            roles.append(getattr(OrganizationMember, attr))

    # Executor variantlari (projectlarda turlicha yoziladi)
    for attr in ("ROLE_EXECUTOR", "ROLE_EXECUTER", "ROLE_EXECUTANT", "ROLE_WORKER", "ROLE_EMPLOYEE"):
        if hasattr(OrganizationMember, attr):
            roles.append(getattr(OrganizationMember, attr))

    # dublikatlarni olib tashlash
    return list(dict.fromkeys([r for r in roles if r]))




def _is_org_admin(user):
    if not user or not user.is_authenticated:
        return False
    # ✅ superuser ham kiradi
    if user.is_superuser:
        return True
    # ✅ Dispatcher ham org-admin hisoblanadi
    return (getattr(user, "user_type", "") or "").lower() == "dispatcher"



def _get_user_organization(user):
    if not user or not user.is_authenticated:
        return None

    # ✅ 1) Avval membership orqali topamiz (sizdagi real bog‘lanish shu)
    m = (
        OrganizationMember.objects
        .filter(user=user)
        .select_related("organization")
        .first()
    )
    if m and m.organization:
        return m.organization

    # ✅ 2) Fallback: user.organization FK bo'lsa
    org = getattr(user, "organization", None)
    if org:
        return org

    # ✅ 3) Fallback: user.organization_id bo'lsa
    org_id = getattr(user, "organization_id", None)
    if org_id:
        return Organization.objects.filter(id=org_id).first()

    return None


@login_required
@user_passes_test(_is_org_admin, login_url="/login/")
def organization_admin_dashboard(request):
    org = _get_user_organization(request.user)
    if not org:
        # organization topilmasa - dashboard'ni ochmasin
        return render(request, "organization_admin/no_organization.html", status=403)

    # ---- Filters (org fixed) ----
    q = (request.GET.get("q") or "").strip()
    selected_statuses = request.GET.getlist("status")  # bo'sh bo'lsa -> hammasi

    reports = Report.objects.select_related("user", "organization").filter(organization=org)

    if q:
        reports = reports.filter(
            Q(description__icontains=q)
            | Q(user__username__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__phone_number__icontains=q)
        )

    if selected_statuses:
        reports = reports.filter(status__in=selected_statuses)

    # ---- KPI ----
    now = timezone.localtime()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    total_count = reports.count()
    today_count = reports.filter(created_at__gte=today_start).count()
    week_count = reports.filter(created_at__gte=week_start).count()

    status_counts_global_qs = reports.values("status").annotate(c=Count("id"))
    status_counts_global = {row["status"]: row["c"] for row in status_counts_global_qs}

    # ---- Status options (sizdagi choice/label'ga mos) ----
    # Agar Report modelida status choices bo'lsa:
    status_options = getattr(Report, "STATUS_CHOICES", None) or getattr(Report, "status_choices", None)

    # fallback: modeldan choices olib ketamiz
    if not status_options:
        try:
            status_options = Report._meta.get_field("status").choices
        except Exception:
            status_options = [
                ("new", "Yangi"),
                ("sent", "Yuborildi"),
                ("read", "O‘qildi"),
                ("accepted", "Qabul qilindi"),
                ("assigned", "Biriktirildi"),
                ("in_progress", "Jarayonda"),
                ("resolved", "Hal qilingan"),
                ("rejected", "Rad etilgan"),
                ("redirected", "Yo‘naltirilgan"),
            ]

    # ---- Points (Leaflet uchun) ----
    points = []
    for r in reports:
        # status label (agar get_status_uz bo'lsa ishlatamiz, bo'lmasa display)
        if hasattr(r, "get_status_uz"):
            status_label = r.get_status_uz()
        else:
            try:
                status_label = r.get_status_display()
            except Exception:
                status_label = r.status

        u = r.user
        points.append(
            {
                "id": str(r.id),
                "lat": float(r.latitude) if r.latitude is not None else None,
                "lng": float(r.longitude) if r.longitude is not None else None,
                "status": r.status,
                "status_label": status_label,
                "description": r.description or "",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "org": org.name,

                "user_username": getattr(u, "username", "") if u else "",
                "user_full_name": (f"{getattr(u,'first_name','') or ''} {getattr(u,'last_name','') or ''}").strip() if u else "",
                "user_phone": getattr(u, "phone_number", "") if u else "",
                "user": getattr(u, "username", "") if u else "",
            }
        )

    # ---- Charts ----
    # Status chart (labels/values) - filtered holat bo'yicha
    chart_status_labels = [lbl for key, lbl in status_options]
    chart_status_values_filtered = [status_counts_global.get(key, 0) for key, _lbl in status_options]

    # 7 kunlik trend
    days = []
    day_labels = []
    for i in range(6, -1, -1):
        d = today_start - timedelta(days=i)
        days.append(d)
        day_labels.append(d.strftime("%d/%m"))

    day_values = []
    for d in days:
        d2 = d + timedelta(days=1)
        day_values.append(reports.filter(created_at__gte=d, created_at__lt=d2).count())

    context = {
        "org": org,

        "q": q,
        "selected_statuses": selected_statuses,
        "status_options": status_options,

        "total_count": total_count,
        "today_count": today_count,
        "week_count": week_count,
        "status_counts_global": status_counts_global,

        "points": json.dumps(points, ensure_ascii=False),

        "chart_status_labels": json.dumps(chart_status_labels, ensure_ascii=False),
        "chart_status_values_filtered": json.dumps(chart_status_values_filtered, ensure_ascii=False),
        "chart_days_labels": json.dumps(day_labels, ensure_ascii=False),
        "chart_days_values": json.dumps(day_values, ensure_ascii=False),
    }
    return render(request, "organization_admin/dashboard.html", context)

