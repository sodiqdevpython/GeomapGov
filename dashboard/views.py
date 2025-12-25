from django.contrib.auth import login
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required
from reports.models import Report, ReportRead, ReportAcceptance, ReportAssignment, ReportRedirect, ReportRejection
from reports.choices import ReportStatus
from organizations.models import Organization, OrganizationMember
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from datetime import timedelta
from django.http import Http404
from users.choices import UserChoices
from django.http import HttpResponseForbidden
from django.db.models import Prefetch
from utils.telegram import send_telegram_message


from .forms import LoginForm


User = get_user_model()

def custom_404_view(request, exception=None):
    if not request.user.is_authenticated:
        return redirect("dashboard:login")
    if request.user.is_superuser:
        return redirect("dashboard:home")
    if getattr(request.user, "user_type", None) == UserChoices.DISPATCHER:
        return redirect("dashboard:org-dashboard")
    return redirect("dashboard:home")


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
        Report.objects
        .select_related("user", "organization")
        .prefetch_related(
            "attachments",

            # ✅ reads ichida organization/read_by ni ham olib kelamiz
            Prefetch(
                "reads",
                queryset=ReportRead.objects.select_related("organization", "read_by").order_by("-read_at"),
            ),

            # ✅ assignments (sizdagi model nomi ReportAssignment bo'lsa)
            Prefetch(
                "assignments",
                queryset=ReportAssignment.objects.select_related(
                    "assigned_to", "assigned_by", "organization"
                )
            ),

            # ✅ redirects (sizdagi model nomi ReportRedirect bo'lsa)
            Prefetch(
                "redirects",
                queryset=ReportRedirect.objects.select_related(
                    "from_organization", "to_organization", "redirected_by"
                )
            ),

            # (ixtiyoriy) status history bo'lsa:
            # Prefetch("status_logs", queryset=ReportStatusLog.objects.select_related("changed_by").order_by("-created_at")),
        ),
        pk=pk
    )

    # ✅ Permission (sizdagi kabi)
    if not request.user.is_superuser:
        if not report.organization_id:
            raise Http404()

        is_member = OrganizationMember.objects.filter(
            user=request.user,
            organization_id=report.organization_id
        ).exists()
        if not is_member:
            raise Http404()

        # ✅ READ log
        ReportRead.objects.get_or_create(
            report=report,
            organization_id=report.organization_id,
            defaults={"read_by": request.user},
        )

    phone = _get_user_phone(report.user)

    # =========================
    # ✅ TIMELINE: hamma voqealarni bitta ro'yxatga yig'amiz
    # =========================
    timeline = []

    for rr in report.reads.all():
        timeline.append({
            "type": "read",
            "at": rr.read_at,
            "title": "O‘qildi",
            "who": getattr(rr.read_by, "username", "-"),
            "org": getattr(rr.organization, "name", "-"),
            "details": "",
        })

    for a in report.assignments.all():
        timeline.append({
            "type": "assign",
            "at": a.created_at,
            "title": "Biriktirildi",
            "who": getattr(a.assigned_by, "username", "-"),
            "org": getattr(getattr(a, "organization", None), "name", "-"),
            "details": f"Kimga: {getattr(a.assigned_to, 'username', '-')}"
                       + (f" | Izoh: {a.note}" if getattr(a, "note", "") else ""),
        })

    for r in report.redirects.all():
        timeline.append({
            "type": "redirect",
            "at": r.created_at,
            "title": "Yo‘naltirildi",
            "who": getattr(r.redirected_by, "username", "-"),
            "org": f"{getattr(r.from_organization, 'name', '-')}"
                   f" → {getattr(r.to_organization, 'name', '-')}",
            "details": f"Sabab: {r.reason}" if getattr(r, "reason", "") else "",
        })

    # ✅ Rad etish / qabul qilish: sizda qayerda saqlansa shunga ulang
    # Variant A: Report ichida field bo'lsa (misol)
    if getattr(report, "rejected_at", None):
        timeline.append({
            "type": "reject",
            "at": report.rejected_at,
            "title": "Rad etildi",
            "who": getattr(getattr(report, "rejected_by", None), "username", "-"),
            "org": getattr(getattr(report, "organization", None), "name", "-"),
            "details": f"Sabab: {getattr(report, 'rejection_reason', '')}" if getattr(report, "rejection_reason", "") else "",
        })

    if getattr(report, "accepted_at", None):
        timeline.append({
            "type": "accept",
            "at": report.accepted_at,
            "title": "Qabul qilindi",
            "who": getattr(getattr(report, "accepted_by", None), "username", "-"),
            "org": getattr(getattr(report, "organization", None), "name", "-"),
            "details": "",
        })

    timeline.sort(key=lambda x: x["at"] or 0, reverse=True)

    return render(request, "report_detail.html", {
        "report": report,
        "phone": phone,
        "timeline": timeline,
    })


STATUS_OPTIONS = [
    ("new", "Yangi"),
    ("sent", "Tashkilotga yuborildi"),
    ("read", "Tashkilot tomonidan o‘qildi"),
    ("accepted", "Tashkilot qabul qildi"),
    ("assigned", "Xodimga biriktirildi"),
    ("in_progress", "Jarayonda"),
    ("resolved", "Hal qilindi"),
    ("rejected", "Rad etildi"),
    ("redirected", "Boshqa tashkilotga yo‘naltirildi"),
]


def _status_uz(status: str) -> str:
    m = dict(STATUS_OPTIONS)
    return m.get(status, str(status))


@login_required
def superadmin_dashboard(request):
    if not request.user.is_superuser:
        return redirect("dashboard:org-dashboard")

    # --------- Base queryset (for global stats) ----------
    base_qs = Report.objects.select_related("user", "organization").order_by("-created_at")

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    # Global counters
    total_count = base_qs.count()
    today_count = base_qs.filter(created_at__gte=today_start).count()
    week_count = base_qs.filter(created_at__gte=week_start).count()

    # Status counters (global)
    status_counts_global = dict(
        base_qs.values("status").annotate(c=Count("id")).values_list("status", "c")
    )

    # --------- Filters (GET) ----------
    org_id = request.GET.get("org") or ""
    q = request.GET.get("q") or ""
    # status can be multi: ?status=new&status=read...
    selected_statuses = request.GET.getlist("status")
    if not selected_statuses:
        # allow single value too
        s = request.GET.get("status")
        if s:
            selected_statuses = [s]

    qs = base_qs
    if org_id:
        qs = qs.filter(organization_id=org_id)

    if selected_statuses:
        qs = qs.filter(status__in=selected_statuses)

    if q:
        qs = qs.filter(description__icontains=q) | qs.filter(user__username__icontains=q) | qs.filter(user__email__icontains=q)

    # organizations
    organizations = Organization.objects.filter(is_active=True).order_by("name")

    # --------- Map points (limit) ----------
    map_reports = qs.exclude(latitude__isnull=True).exclude(longitude__isnull=True)[:1500]
    points = []
    for r in map_reports:
        points.append({
            "id": str(r.id),
            "lat": float(r.latitude),
            "lng": float(r.longitude),
            "status": r.status,
            "status_label": _status_uz(r.status),
            "org": r.organization.name if r.organization else "-",
            "org_id": str(r.organization_id) if r.organization_id else "",
            "created_at": r.created_at.isoformat(),
            "user": r.user.username,
            "user_full_name": f"{(r.user.first_name or '').strip()} {(r.user.last_name or '').strip()}".strip(),
            "user_username": r.user.username or "",
            "description": r.description or ""
        })

    # --------- Table pagination ----------
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    # --------- Charts data ----------
    # 1) Filterlangan status taqsimoti
    status_counts_filtered = dict(
        qs.values("status").annotate(c=Count("id")).values_list("status", "c")
    )

    chart_status_labels = [label for _, label in STATUS_OPTIONS]
    chart_status_values_filtered = [status_counts_filtered.get(key, 0) for key, _ in STATUS_OPTIONS]
    chart_status_values_global = [status_counts_global.get(key, 0) for key, _ in STATUS_OPTIONS]

    # 2) 7 kunlik trend: har kun nechta report
    days = []
    day_counts = []
    for i in range(6, -1, -1):
        d0 = (today_start - timedelta(days=i))
        d1 = d0 + timedelta(days=1)
        days.append(d0.strftime("%d/%m"))
        day_counts.append(qs.filter(created_at__gte=d0, created_at__lt=d1).count())

    context = {
        # cards
        "total_count": total_count,
        "today_count": today_count,
        "week_count": week_count,
        "status_counts_global": status_counts_global,

        # filters
        "organizations": organizations,
        "status_options": STATUS_OPTIONS,
        "selected_org": org_id,
        "selected_statuses": selected_statuses,
        "q": q,

        # map/table
        "points": points,
        "page_obj": page_obj,

        # charts
        "chart_status_labels": chart_status_labels,
        "chart_status_values_filtered": chart_status_values_filtered,
        "chart_status_values_global": chart_status_values_global,
        "chart_days_labels": days,
        "chart_days_values": day_counts,
    }
    return render(request, "superadmin/dashboard.html", context)


@login_required
def report_detail_json(request, pk):
    if not request.user.is_superuser:
        raise Http404()

    r = (
        Report.objects.select_related("user", "organization")
        .prefetch_related(
            "attachments",
            "reads__organization", "reads__read_by",
            "assignments__assigned_to", "assignments__assigned_by",
            "redirects__from_organization", "redirects__to_organization",
        )
        .get(pk=pk)
    )

    attachments = []
    for a in r.attachments.all():
        attachments.append({
            "type": getattr(a, "type", ""),
            "name": getattr(a, "original_name", "") or "file",
            "url": a.file.url if getattr(a, "file", None) else "",
        })

    events = []
    for rr in r.reads.all():
        events.append({
            "title": "Shikoyat o‘qildi",
            "meta": f"{rr.organization.name}" + (f" — {rr.read_by.username}" if rr.read_by else ""),
            "at": rr.read_at.isoformat(),
        })

    if hasattr(r, "acceptance") and r.acceptance:
        acc = r.acceptance
        events.append({
            "title": "Tashkilot qabul qildi",
            "meta": f"{acc.organization.name}" + (f" — {acc.accepted_by.username}" if acc.accepted_by else ""),
            "at": acc.accepted_at.isoformat(),
        })

    for a in r.assignments.all():
        events.append({
            "title": "Xodimga biriktirildi",
            "meta": f"{a.organization.name} — {a.assigned_to.username}" + (f" (biriktirdi: {a.assigned_by.username})" if a.assigned_by else ""),
            "at": a.assigned_at.isoformat(),
        })

    for red in r.redirects.all():
        events.append({
            "title": "Boshqa tashkilotga yo‘naltirildi",
            "meta": f"{red.from_organization.name} → {red.to_organization.name} | Sabab: {red.reason}",
            "at": red.redirected_at.isoformat(),
        })

    events.sort(key=lambda x: x["at"])

    phone = ""
    for attr in ("phone_number", "phone", "mobile", "tel", "phoneNumber"):
        if hasattr(r.user, attr) and getattr(r.user, attr):
            phone = str(getattr(r.user, attr))
            break

    return JsonResponse({
        "id": str(r.id),
        "status": r.status,
        "status_label": _status_uz(r.status),
        "description": r.description,
        "created_at": r.created_at.isoformat(),
        "lat": float(r.latitude),
        "lng": float(r.longitude),
        "organization": r.organization.name if r.organization else "-",
        "user": {"username": r.user.username, "email": getattr(r.user, "email", "") or "", "phone": phone},
        "attachments": attachments,
        "events": events,
    })



def _get_org_admin_membership(request):
    """
    Org adminni aniqlaydi va organizationni qaytaradi.
    Sizda adminlik role=admin orqali.
    """
    membership = OrganizationMember.objects.filter(
        user=request.user,
        role=OrganizationMember.ROLE_ADMIN
    ).select_related("organization").first()
    return membership


@login_required
def org_reports_list(request):
    """
    Organization admin uchun:
    - Kelgan shikoyatlar (resolved emas)
    - Hal qilingan (resolved)
    Har biri alohida paginator + search + per_page.
    """
    membership = _get_org_admin_membership(request)
    if not membership:
        return HttpResponseForbidden("Siz organization admin emassiz")

    org = membership.organization

    # TAB
    tab = (request.GET.get("tab") or "incoming").strip()  # incoming | resolved

    # Incoming filters
    iq = (request.GET.get("iq") or "").strip()
    iper_page = request.GET.get("iper_page") or "10"
    ipage = request.GET.get("ipage") or 1

    # Resolved filters
    rq = (request.GET.get("rq") or "").strip()
    rper_page = request.GET.get("rper_page") or "10"
    rpage = request.GET.get("rpage") or 1

    def parse_per_page(v):
        try:
            x = int(v)
        except ValueError:
            x = 10
        return x if x in (10, 25, 50, 100) else 10

    iper_page = parse_per_page(iper_page)
    rper_page = parse_per_page(rper_page)

    base_qs = Report.objects.filter(organization=org).select_related("user", "organization").order_by("-created_at")

    # ======= KPI / statistikalar =======
    total_count = base_qs.count()
    new_count = base_qs.filter(status=ReportStatus.NEW).count()
    sent_count = base_qs.filter(status=ReportStatus.SENT).count()
    read_count = base_qs.filter(status=ReportStatus.READ).count()
    accepted_count = base_qs.filter(status=ReportStatus.ACCEPTED).count()
    in_progress_count = base_qs.filter(status=ReportStatus.IN_PROGRESS).count()
    resolved_count = base_qs.filter(status=ReportStatus.RESOLVED).count()
    rejected_count = base_qs.filter(status=ReportStatus.REJECTED).count()
    redirected_count = base_qs.filter(status=ReportStatus.REDIRECTED).count()

    # ======= Incoming (resolved emas) =======
    incoming_qs = base_qs.exclude(status=ReportStatus.RESOLVED)

    if iq:
        incoming_qs = incoming_qs.filter(
            Q(description__icontains=iq) |
            Q(user__username__icontains=iq) |
            Q(user__first_name__icontains=iq) |
            Q(user__last_name__icontains=iq)
        )

    incoming_page_obj = Paginator(incoming_qs, iper_page).get_page(ipage)

    # ======= Resolved =======
    resolved_qs = base_qs.filter(status=ReportStatus.RESOLVED)

    if rq:
        resolved_qs = resolved_qs.filter(
            Q(description__icontains=rq) |
            Q(user__username__icontains=rq) |
            Q(user__first_name__icontains=rq) |
            Q(user__last_name__icontains=rq)
        )

    resolved_page_obj = Paginator(resolved_qs, rper_page).get_page(rpage)

    return render(request, "organization_admin/reports_list.html", {
        "org": org,
        "tab": tab,

        # KPI
        "total_count": total_count,
        "new_count": new_count,
        "sent_count": sent_count,
        "read_count": read_count,
        "accepted_count": accepted_count,
        "in_progress_count": in_progress_count,
        "resolved_count": resolved_count,
        "rejected_count": rejected_count,
        "redirected_count": redirected_count,

        # incoming
        "incoming_page_obj": incoming_page_obj,
        "iq": iq,
        "iper_page": iper_page,

        # resolved
        "resolved_page_obj": resolved_page_obj,
        "rq": rq,
        "rper_page": rper_page,
    })



def _org_admin_membership(user):
    return OrganizationMember.objects.filter(
        user=user,
        role=OrganizationMember.ROLE_ADMIN
    ).select_related("organization").first()


def _full_name(u):
    n = f"{u.first_name} {u.last_name}".strip()
    return n if n else u.username



@login_required
def org_report_detail(request, pk):
    membership = _org_admin_membership(request.user)
    if not membership:
        return HttpResponseForbidden("Siz organization admin emassiz")

    org = membership.organization

    report = get_object_or_404(
        Report.objects.select_related("user", "organization").prefetch_related("attachments"),
        pk=pk,
        organization=org
    )

    # ========== READ (1 marta) ==========
    read_obj, created = ReportRead.objects.get_or_create(
        report=report,
        organization=org,
        defaults={"read_by": request.user}
    )
    if created:
        if report.status in (ReportStatus.NEW, ReportStatus.SENT):
            report.status = ReportStatus.READ
            report.save(update_fields=["status", "updated_at"])

        if getattr(report.user, "telegram_id", None):
            msg = (
                f"👀 Sizning shikoyatingiz o‘qildi.\n"
                f"Tashkilot: {org.name}\n"
                f"Admin: {_full_name(request.user)}"
            )
            send_telegram_message(report.user.telegram_id, msg)

    # ========== ACTION faqat NEW/SENT/READ ==========
    can_act = report.status in (ReportStatus.NEW, ReportStatus.SENT, ReportStatus.READ)

    # ========== MODAL open flags ==========
    open_assign = (request.GET.get("open_assign") or "") == "1"
    open_reject = (request.GET.get("open_reject") or "") == "1"

    # ========== MEMBERS LIST (ROLE tekshiruvi YO‘Q) ==========
    staff_q = (request.GET.get("staff_q") or "").strip()
    staff_page = request.GET.get("staff_page") or 1
    staff_per_page = request.GET.get("staff_per_page") or "10"

    try:
        staff_per_page = int(staff_per_page)
    except ValueError:
        staff_per_page = 10
    if staff_per_page not in (10, 25, 50, 100):
        staff_per_page = 10

    staff_memberships = (
        OrganizationMember.objects
        .filter(organization=org)
        .select_related("user")
        .order_by("-joined_at")
    )

    if staff_q:
        staff_memberships = staff_memberships.filter(
            Q(user__username__icontains=staff_q) |
            Q(user__first_name__icontains=staff_q) |
            Q(user__last_name__icontains=staff_q) |
            Q(user__phone_number__icontains=staff_q)
        )

    staff_page_obj = Paginator(staff_memberships, staff_per_page).get_page(staff_page)

    # ========== POST actions ==========
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        if not can_act:
            messages.error(request, "Bu shikoyat bo‘yicha amal bajarib bo‘lmaydi (status mos emas).")
            return redirect(request.path)

        # ---- Qabul + biriktirish ----
        if action == "accept_assign":
            staff_ids = request.POST.getlist("staff_ids")
            # dublikatlarni olib tashlash (JS hidden input ko‘p bo‘lishi mumkin)
            staff_ids = list(dict.fromkeys([str(x) for x in staff_ids if str(x).strip()]))

            if not staff_ids:
                messages.error(request, "Kamida 1 ta a’zo tanlang.")
                return redirect(f"{request.path}?open_assign=1&staff_q={staff_q}&staff_per_page={staff_per_page}")

            # Faqat shu org a’zolari bo‘lsa bo‘ldi (role tekshiruvi yo‘q!)
            valid_memberships = list(
                OrganizationMember.objects.filter(
                    organization=org,
                    user_id__in=staff_ids
                ).select_related("user")
            )

            if not valid_memberships:
                messages.error(request, "Tanlangan foydalanuvchilar shu tashkilot a’zosi emas.")
                return redirect(f"{request.path}?open_assign=1&staff_q={staff_q}&staff_per_page={staff_per_page}")

            # acceptance (1 marta)
            ReportAcceptance.objects.get_or_create(
                report=report,
                defaults={"organization": org, "accepted_by": request.user}
            )

            # assignments
            for m in valid_memberships:
                ReportAssignment.objects.get_or_create(
                    report=report,
                    organization=org,
                    assigned_to=m.user,
                    defaults={"assigned_by": request.user}
                )

            # status -> IN_PROGRESS
            report.status = ReportStatus.IN_PROGRESS
            report.save(update_fields=["status", "updated_at"])

            # telegram notify
            if getattr(report.user, "telegram_id", None):
                assignees = ", ".join([_full_name(m.user) for m in valid_memberships])
                msg = (
                    f"✅ Shikoyat qabul qilindi va biriktirildi.\n"
                    f"Tashkilot: {org.name}\n"
                    f"Biriktirildi: {assignees}\n"
                    f"Shikoyat holati: Jarayonda"
                )
                send_telegram_message(report.user.telegram_id, msg)

            messages.success(request, "Qabul qilindi va tanlangan a’zolarga biriktirildi. Status: Jarayonda.")
            return redirect(request.path)

        # ---- Rad etish ----
        if action == "reject":
            reason = (request.POST.get("reason") or "").strip()
            if len(reason) < 20:
                messages.error(request, "Sabab kamida 20 ta belgi bo‘lishi kerak.")
                return redirect(f"{request.path}?open_reject=1")

            ReportRejection.objects.update_or_create(
                report=report,
                defaults={
                    "organization": org,
                    "reason": reason,
                    "rejected_by": request.user,
                }
            )

            report.status = ReportStatus.REJECTED
            report.save(update_fields=["status", "updated_at"])

            if getattr(report.user, "telegram_id", None):
                msg = (
                    f"⛔ Shikoyat rad etildi.\n"
                    f"Tashkilot: {org.name}\n"
                    f"Rad etgan: {_full_name(request.user)}\n"
                    f"Sabab: {reason}\n"
                    f"Shikoyat id raqami: {report.id}"
                )
                send_telegram_message(report.user.telegram_id, msg)

            messages.success(request, "Rad etildi va sabab reporterga yuborildi.")
            return redirect(request.path)

        messages.error(request, "Noto‘g‘ri amal.")
        return redirect(request.path)

    # ========== current assignments ==========
    current_assignments = (
        ReportAssignment.objects.filter(report=report, organization=org)
        .select_related("assigned_to")
        .order_by("-assigned_at")
    )

    return render(request, "organization_admin/report_detail.html", {
        "org": org,
        "report": report,
        "read_obj": read_obj,
        "can_act": can_act,

        "open_assign": open_assign,
        "open_reject": open_reject,

        "staff_page_obj": staff_page_obj,
        "staff_q": staff_q,
        "staff_per_page": staff_per_page,

        "current_assignments": current_assignments,
    })

