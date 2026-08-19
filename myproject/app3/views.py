from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction as db_transaction
from django.http import JsonResponse
from app2.models import SavingsAccount
from .models import TransactionHistory
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator

# download_statement function requires these additional imports
from django.http import HttpResponse
from datetime import datetime, timedelta
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import KeepTogether
from reportlab.lib.pdfencrypt import StandardEncryption
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
import io
import re

import json
from pyzbar.pyzbar import decode as qr_decode
from PIL import Image
from django.views.decorators.csrf import csrf_exempt


def _send_transaction_email(account, action_label, amount, is_credit, remark=None):
    """Send a styled HTML email after a deposit/withdraw."""
    accent   = "#2e7d32" if is_credit else "#e53935"
    sign     = "+" if is_credit else "−"
    bg_chip  = "#e8f5e9" if is_credit else "#fdecea"

    subject = f"{'Money Credited' if is_credit else 'Money Debited'} — Apex Bank"
    text_body = (
        f"Hi {account.full_name},\n\n"
        f"₹{amount} {action_label}.\nNew Balance: ₹{account.balance}"
    )

    html_body = f"""
    <html>
    <body style="font-family:Arial,sans-serif;background:#f4f6fb;padding:30px;">
      <div style="max-width:480px;margin:auto;background:#fff;border-radius:12px;
                  padding:32px;box-shadow:0 4px 20px rgba(0,0,0,.08);">
        <h2 style="color:#1a73e8;margin-bottom:4px;">Apex Bank</h2>
        <p style="color:#555;margin-top:0;">Transaction Alert</p>
        <hr style="border:none;border-top:1px solid #eee;margin:16px 0;">
        <p style="color:#333;">Dear <strong>{account.full_name}</strong>,</p>
        <p style="color:#333;">Your account has been {'credited' if is_credit else 'debited'} successfully.</p>

        <div style="text-align:center;margin:24px 0;">
          <span style="display:inline-block;background:{bg_chip};color:{accent};
                       font-size:28px;font-weight:700;padding:10px 24px;border-radius:8px;">
            {sign} ₹{amount}
          </span>
        </div>

        <table style="width:100%;background:#f8f9fa;border-radius:8px;padding:16px;
                      margin:16px 0;border-collapse:collapse;">
          <tr>
            <td style="color:#888;padding:6px 0;">Account No.</td>
            <td style="color:#333;font-weight:600;">{account.account_number}</td>
          </tr>
          <tr>
            <td style="color:#888;padding:6px 0;">Transaction</td>
            <td style="color:#333;font-weight:600;text-transform:capitalize;">{action_label}</td>
          </tr>
          {f'<tr><td style="color:#888;padding:6px 0;">Remark</td><td style="color:#333;">{remark}</td></tr>' if remark else ''}
          <tr>
            <td style="color:#888;padding:6px 0;">Available Balance</td>
            <td style="color:{accent};font-weight:700;">₹{account.balance}</td>
          </tr>
        </table>

        <div style="background:#fdecea;border-left:4px solid #e53935;border-radius:6px;padding:12px 16px;margin:16px 0;">
          <p style="color:#e53935;font-weight:700;margin:0;">⚠️ If this wasn't you, contact Apex Bank support immediately.</p>
        </div>

        <p style="color:#888;font-size:12px;margin-top:24px;">
          This is an automated message. Do not reply to this email.
        </p>
      </div>
    </body>
    </html>
    """

    msg = EmailMultiAlternatives(subject, text_body, None, [account.email])
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=True)



# ─────────────────────────────
#  DEPOSIT
# ─────────────────────────────
@login_required
def deposit(request):
    try:
        account = SavingsAccount.objects.get(user=request.user)
    except SavingsAccount.DoesNotExist:
        messages.error(request, "Please create a savings account first.")
        return redirect("saving_ac_create")
    except InvalidOperation:
        messages.error(
            request,
            "Account data is corrupted. Please contact support."
        )
        return redirect("profile")

    if account.mpin_locked_until and timezone.now() < account.mpin_locked_until:
        messages.error(request, "Account locked! Try again after 24 hours.")
        return redirect(request.META.get('HTTP_REFERER', 'profile'))
    elif account.mpin_locked_until:
        account.failed_mpin_attempts = 0
        account.mpin_locked_until = None
        account.save()

    if request.method == "POST":
        try:
            amount = Decimal(request.POST["amount"])
            mpin   = request.POST["mpin"]

            if amount <= 0:
                messages.error(request, "Enter a valid amount greater than 0!")
                return redirect(request.META.get('HTTP_REFERER', 'profile'))

            if account.mpin == mpin:
                account.failed_mpin_attempts = 0
                account.mpin_locked_until    = None
                account.balance += amount
                account.save()

                TransactionHistory.objects.create(
                    account=account,
                    transaction_type='deposit',
                    amount=amount,
                    balance_after=account.balance,
                    remark='Self Deposit'
                )

                _send_transaction_email(account, "credited", amount, is_credit=True, remark="Self Deposit")

                messages.success(request, f"✓ Deposit of ₹{amount} successful!")
            else:
                account.failed_mpin_attempts += 1
                if account.failed_mpin_attempts >= 3:
                    account.mpin_locked_until = timezone.now() + timedelta(hours=24)
                    account.save()
                    messages.error(request, "Too many wrong attempts! Locked for 24 hours.")
                else:
                    account.save()
                    messages.error(request, f"Wrong MPIN! {3 - account.failed_mpin_attempts} attempt(s) left.")

        except (KeyError, ValueError, InvalidOperation):
            messages.error(request, "Invalid input.")

    return redirect(request.META.get('HTTP_REFERER', 'profile'))


# ─────────────────────────────
#  WITHDRAW
# ─────────────────────────────
@login_required
def withdraw(request):
    try:
        account = SavingsAccount.objects.get(user=request.user)
    except SavingsAccount.DoesNotExist:
        messages.error(request, "Please create a savings account first.")
        return redirect("saving_ac_create")

    if account.tpin_locked_until and timezone.now() < account.tpin_locked_until:
        messages.error(request, "Account locked! Try again after 24 hours.")
        return redirect(request.META.get('HTTP_REFERER', 'profile'))
    elif account.tpin_locked_until:
        account.failed_tpin_attempts = 0
        account.tpin_locked_until    = None
        account.save()

    if request.method == "POST":
        try:
            amount = Decimal(request.POST["amount"])
            tpin   = request.POST["tpin"]

            if amount <= 0:
                messages.error(request, "Enter a valid amount greater than 0!")
                return redirect(request.META.get('HTTP_REFERER', 'profile'))

            if account.tpin == tpin:
                if amount > account.balance:
                    messages.error(request, f"Insufficient balance! Current: ₹{account.balance}")
                    return redirect(request.META.get('HTTP_REFERER', 'profile'))

                account.failed_tpin_attempts = 0
                account.tpin_locked_until    = None
                account.balance -= amount
                account.save()

                TransactionHistory.objects.create(
                    account=account,
                    transaction_type='withdraw',
                    amount=amount,
                    balance_after=account.balance,
                    remark='Self Withdrawal'
                )

                _send_transaction_email(account, "debited", amount, is_credit=False, remark="Self Withdrawal")

                messages.success(request, f"✓ Withdrawal of ₹{amount} successful!")
            else:
                account.failed_tpin_attempts += 1
                if account.failed_tpin_attempts >= 3:
                    account.tpin_locked_until = timezone.now() + timedelta(hours=24)
                    account.save()
                    messages.error(request, "Too many wrong attempts! Locked for 24 hours.")
                else:
                    account.save()
                    messages.error(request, f"Wrong TPIN! {3 - account.failed_tpin_attempts} attempt(s) left.")

        except (KeyError, ValueError, InvalidOperation):
            messages.error(request, "Invalid input.")

    return redirect(request.META.get('HTTP_REFERER', 'profile'))


# ─────────────────────────────
#  TRANSFER
# ─────────────────────────────
@login_required
def transfer(request):
    try:
        sender = SavingsAccount.objects.get(user=request.user)
        prefill_account = request.GET.get('receiver', '')
    except SavingsAccount.DoesNotExist:
        messages.error(request, "Please create a savings account first.")
        return redirect("saving_ac_create")

    if sender.tpin_locked_until and timezone.now() < sender.tpin_locked_until:
        messages.error(request, "Account locked! Try again after 24 hours.")
        return render(request, 'transfer.html', {'sender': sender})
    elif sender.tpin_locked_until:
        sender.failed_tpin_attempts = 0
        sender.tpin_locked_until    = None
        sender.save()

    if request.method == "POST":
        receiver_acc_no = request.POST.get("receiver_account_number", "").strip()
        amount_str      = request.POST.get("amount", "").strip()
        tpin            = request.POST.get("tpin", "").strip()
        remark          = request.POST.get("remark", "").strip()

        if not receiver_acc_no:
            messages.error(request, "Please enter receiver account number.")
            return render(request, 'transfer.html', {'sender': sender})

        if receiver_acc_no == sender.account_number:
            messages.error(request, "You cannot transfer to your own account!")
            return render(request, 'transfer.html', {'sender': sender})

        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError
        except (ValueError, InvalidOperation):
            messages.error(request, "Enter a valid amount greater than 0.")
            return render(request, 'transfer.html', {'sender': sender})

        if amount > sender.balance:
            messages.error(request, f"Insufficient balance! Your balance: ₹{sender.balance}")
            return render(request, 'transfer.html', {'sender': sender})

        try:
            receiver = SavingsAccount.objects.get(account_number=receiver_acc_no)
        except SavingsAccount.DoesNotExist:
            messages.error(request, "Receiver account not found!")
            return render(request, 'transfer.html', {'sender': sender})

        if sender.tpin != tpin:
            sender.failed_tpin_attempts += 1
            if sender.failed_tpin_attempts >= 3:
                sender.tpin_locked_until = timezone.now() + timedelta(hours=24)
                sender.save()
                messages.error(request, "Too many wrong attempts! Locked for 24 hours.")
            else:
                sender.save()
                messages.error(request, f"Wrong TPIN! {3 - sender.failed_tpin_attempts} attempt(s) left.")
            return render(request, 'transfer.html', {'sender': sender})

        # ── Atomic transfer ──
        with db_transaction.atomic():
            sender.failed_tpin_attempts = 0
            sender.tpin_locked_until    = None
            sender.balance -= amount
            sender.save()

            receiver.balance += amount
            receiver.save()

            TransactionHistory.objects.create(
                account=sender,
                transaction_type='transfer_sent',
                amount=amount,
                balance_after=sender.balance,
                related_account_number=receiver.account_number,
                related_account_name=receiver.full_name,
                remark=remark or f"Transfer to {receiver.full_name}"
            )
            TransactionHistory.objects.create(
                account=receiver,
                transaction_type='transfer_received',
                amount=amount,
                balance_after=receiver.balance,
                related_account_number=sender.account_number,
                related_account_name=sender.full_name,
                remark=remark or f"Transfer from {sender.full_name}"
            )

        send_mail("Money Transferred — Apex Bank",
            f"Hi {sender.full_name},\n\n₹{amount} transferred to {receiver.full_name}.\nBalance: ₹{sender.balance}",
            None, [sender.email], fail_silently=True)
        send_mail("Money Received — Apex Bank",
            f"Hi {receiver.full_name},\n\n₹{amount} received from {sender.full_name}.\nBalance: ₹{receiver.balance}",
            None, [receiver.email], fail_silently=True)

        messages.success(request, f"✓ ₹{amount} transferred to {receiver.full_name} successfully!")
        return redirect('transfer')

    return render(request, 'transfer.html', {'sender': sender, 'prefill_account': prefill_account})


# ─────────────────────────────
#  TRANSFER using qr code
# ─────────────────────────────
@login_required
def scan_qr_transfer(request):
    if request.method != "POST" or "qr_image" not in request.FILES:
        return JsonResponse({"ok": False, "error": "No image uploaded."})

    try:
        img = Image.open(request.FILES["qr_image"])
        decoded = qr_decode(img)

        if not decoded:
            return JsonResponse({"ok": False, "error": "No QR code detected in image."})

        qr_text = decoded[0].data.decode("utf-8")

        # Expected format: APEXBANK|account_number|full_name|ifsc_code
        parts = qr_text.split("|")
        if len(parts) < 3 or parts[0] != "APEXBANK":
            return JsonResponse({"ok": False, "error": "This is not a valid Apex Bank QR code."})

        account_number = parts[1]

        try:
            receiver = SavingsAccount.objects.get(account_number=account_number)
        except SavingsAccount.DoesNotExist:
            return JsonResponse({"ok": False, "error": "Receiver account not found."})

        if receiver.user == request.user:
            return JsonResponse({"ok": False, "error": "You cannot transfer to your own account."})

        return JsonResponse({
            "ok": True,
            "account_number": receiver.account_number,
            "full_name": receiver.full_name,
        })

    except Exception:
        return JsonResponse({"ok": False, "error": "Could not read QR code. Try a clearer image."})

# ─────────────────────────────
#  AJAX — verify receiver
# ─────────────────────────────
@login_required
def verify_receiver(request):
    acc_no = request.GET.get('account_number', '').strip()
    try:
        acc = SavingsAccount.objects.get(account_number=acc_no)
        return JsonResponse({'found': True, 'name': acc.full_name, 'branch': acc.branch_name})
    except SavingsAccount.DoesNotExist:
        return JsonResponse({'found': False})


# ─────────────────────────────
#  TRANSACTION HISTORY
# ─────────────────────────────

@login_required
def transaction_history(request):
    try:
        account = SavingsAccount.objects.get(user=request.user)
    except SavingsAccount.DoesNotExist:
        messages.error(request, "No account found!")
        return redirect('profile')

    transactions = TransactionHistory.objects.filter(account=account)

    # Filter by type
    filter_type = request.GET.get('type', 'all')
    if filter_type != 'all':
        transactions = transactions.filter(transaction_type=filter_type)

    # Summary totals (always from all transactions, not filtered)
    all_tx         = TransactionHistory.objects.filter(account=account)
    total_deposit  = sum(t.amount for t in all_tx.filter(transaction_type='deposit'))
    total_withdraw = sum(t.amount for t in all_tx.filter(transaction_type='withdraw'))
    total_sent     = sum(t.amount for t in all_tx.filter(transaction_type='transfer_sent'))
    total_received = sum(t.amount for t in all_tx.filter(transaction_type='transfer_received'))

    # Pagination — 5 per page
    paginator   = Paginator(transactions, 5)
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

    return render(request, 'transaction_history.html', {
        'account':        account,
        'transactions':   page_obj,        # ← now a page object
        'page_obj':       page_obj,
        'filter_type':    filter_type,
        'total_deposit':  total_deposit,
        'total_withdraw': total_withdraw,
        'total_sent':     total_sent,
        'total_received': total_received,
    })




# ─────────────────────────────────────────────────────────────

# ── COLOR PALETTE ──
NAVY    = colors.HexColor('#0a1628')
BLUE    = colors.HexColor('#1a56db')
SKY     = colors.HexColor('#38bdf8')
LIGHT   = colors.HexColor('#e8f0fe')
MUTED   = colors.HexColor('#64748b')
SUCCESS = colors.HexColor('#16a34a')
DANGER  = colors.HexColor('#dc2626')
WHITE   = colors.white
GRAY_BG = colors.HexColor('#f8fafc')
BORDER  = colors.HexColor('#e2e8f0')


def _build_styles():
    return {
        'bank_name': ParagraphStyle('bank_name',
            fontName='Helvetica-Bold', fontSize=22,
            textColor=NAVY, leading=26),

        'bank_sub': ParagraphStyle('bank_sub',
            fontName='Helvetica', fontSize=9,
            textColor=MUTED, leading=13),

        'section_title': ParagraphStyle('section_title',
            fontName='Helvetica-Bold', fontSize=10,
            textColor=NAVY, leading=14, spaceBefore=4),

        'label': ParagraphStyle('label',
            fontName='Helvetica', fontSize=8,
            textColor=MUTED, leading=11),

        'value': ParagraphStyle('value',
            fontName='Helvetica-Bold', fontSize=9,
            textColor=NAVY, leading=13),

        'footer': ParagraphStyle('footer',
            fontName='Helvetica', fontSize=7.5,
            textColor=MUTED, alignment=TA_CENTER, leading=11),

        'center': ParagraphStyle('center',
            fontName='Helvetica', fontSize=9,
            alignment=TA_CENTER, textColor=MUTED),

        'amount_cr': ParagraphStyle('amount_cr',
            fontName='Helvetica-Bold', fontSize=9,
            textColor=SUCCESS, alignment=TA_RIGHT),

        'amount_dr': ParagraphStyle('amount_dr',
            fontName='Helvetica-Bold', fontSize=9,
            textColor=DANGER, alignment=TA_RIGHT),

        'bal': ParagraphStyle('bal',
            fontName='Helvetica', fontSize=8,
            textColor=MUTED, alignment=TA_RIGHT),

        'tx_title': ParagraphStyle('tx_title',
            fontName='Helvetica-Bold', fontSize=8.5,
            textColor=NAVY, leading=12),

        'tx_sub': ParagraphStyle('tx_sub',
            fontName='Helvetica', fontSize=7.5,
            textColor=MUTED, leading=11),
    }


@login_required
def download_statement(request):
    """
    GET /history/statement/?period=1m|6m|1y
    Returns a beautiful branded PDF bank statement.
    """
    try:
        account = SavingsAccount.objects.get(user=request.user)
    except SavingsAccount.DoesNotExist:
        messages.error(request, "No account found!")
        return redirect('profile')

    # ── Period filter ──
    period = request.GET.get('period', '1m')
    now    = timezone.now()
    period_map = {
        '1m': ('1 Month',  now - timedelta(days=30)),
        '6m': ('6 Months', now - timedelta(days=180)),
        '1y': ('1 Year',   now - timedelta(days=365)),
    }
    period_label, from_date = period_map.get(period, period_map['1m'])

    transactions = (
        TransactionHistory.objects
        .filter(account=account, created_at__gte=from_date)
        .order_by('created_at')
    )

    # ── Summary totals for the period ──
    total_cr = sum(t.amount for t in transactions
                   if t.transaction_type in ('deposit', 'transfer_received'))
    total_dr = sum(t.amount for t in transactions
                   if t.transaction_type in ('withdraw', 'transfer_sent'))

    opening_bal = transactions.first().balance_after - transactions.first().amount \
        if transactions.exists() else account.balance
    closing_bal = transactions.last().balance_after \
        if transactions.exists() else account.balance

    styles = _build_styles()
    buffer = io.BytesIO()

    # ── Password-protect the PDF using the account holder's phone number ──
    pdf_password = re.sub(r'\D', '', account.mobile_number or '')
    enc = StandardEncryption(pdf_password, ownerPassword=pdf_password,
                              canPrint=1, canModify=0, canCopy=0, canAnnotate=0)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=15*mm,   bottomMargin=15*mm,
        encrypt=enc,
    )

    W = A4[0] - 30*mm   # usable width
    story = []

    # ════════════════════════════════════
    # HEADER BANNER
    # ════════════════════════════════════
    header_data = [[
        Paragraph('<b>APEX BANK</b>', ParagraphStyle('h',
            fontName='Helvetica-Bold', fontSize=20,
            textColor=WHITE, leading=24)),
        Paragraph(
            'Apex Tower, BKC, Mumbai — 400051<br/>'
            'support@apexbank.in  |  1800-123-4567<br/>'
            'IFSC: ' + account.ifsc_code,
            ParagraphStyle('hs', fontName='Helvetica', fontSize=8,
                           textColor=colors.HexColor('#93c5fd'),
                           leading=12, alignment=TA_RIGHT)
        ),
    ]]
    header_tbl = Table(header_data, colWidths=[W * 0.45, W * 0.55])
    header_tbl.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, -1), NAVY),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING',(0, 0), (-1, -1), 12),
        ('TOPPADDING',  (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING',(0,0), (-1, -1), 14),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 5*mm))

    # ── Statement title bar ──
    title_data = [[
        Paragraph('ACCOUNT STATEMENT', ParagraphStyle('st',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=BLUE, leading=14)),
        Paragraph(
            f'Period: <b>{period_label}</b>  '
            f'({from_date.strftime("%d %b %Y")} – {now.strftime("%d %b %Y")})',
            ParagraphStyle('sp', fontName='Helvetica', fontSize=8.5,
                           textColor=MUTED, alignment=TA_RIGHT)
        ),
    ]]
    title_tbl = Table(title_data, colWidths=[W * 0.5, W * 0.5])
    title_tbl.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), LIGHT),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING',   (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 8),
        ('LINEBELOW',    (0, 0), (-1, -1), 1.5, BLUE),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 5*mm))

    # ════════════════════════════════════
    # ACCOUNT INFO + SUMMARY SIDE BY SIDE
    # ════════════════════════════════════
    def info_cell(label, value):
        return [
            Paragraph(label, styles['label']),
            Paragraph(value, styles['value']),
        ]

    acct_block = Table([
        [Paragraph('ACCOUNT HOLDER DETAILS', styles['section_title']), ''],
        *[info_cell(l, v) for l, v in [
            ('Account Name',    account.full_name),
            ('Account Number',  account.account_number),
            ('Customer ID',     account.customer_id),
            ('Branch',          account.branch_name),
            ('IFSC Code',       account.ifsc_code),
            ('Mobile',          account.mobile_number),
            ('Email',           account.email),
            ('Statement Date',  now.strftime('%d %b %Y, %I:%M %p')),
        ]],
    ], colWidths=[W * 0.22, W * 0.28])
    acct_block.setStyle(TableStyle([
        ('SPAN',        (0, 0), (1, 0)),
        ('BACKGROUND',  (0, 0), (1, 0), LIGHT),
        ('TOPPADDING',  (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0,0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',(0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_BG]),
        ('LINEBELOW',   (0, 0), (-1, -1), 0.3, BORDER),
        ('BOX',         (0, 0), (-1, -1), 1, BORDER),
    ]))

    # Summary box
    def sum_row(label, val, color=NAVY, bold=False):
        fn = 'Helvetica-Bold' if bold else 'Helvetica'
        return [
            Paragraph(label, ParagraphStyle('sl', fontName=fn, fontSize=8.5,
                                            textColor=MUTED if not bold else NAVY)),
            Paragraph(val, ParagraphStyle('sv', fontName='Helvetica-Bold',
                                          fontSize=8.5, textColor=color,
                                          alignment=TA_RIGHT)),
        ]

    opening = transactions.first()
    open_bal_val = float(opening.balance_after) - float(opening.amount) \
        if opening else float(account.balance)

    sum_block = Table([
        [Paragraph('PERIOD SUMMARY', styles['section_title']), ''],
        sum_row('Opening Balance',  f'Rs. {open_bal_val:,.2f}'),
        sum_row('Total Credits (+)',f'Rs. {float(total_cr):,.2f}', SUCCESS),
        sum_row('Total Debits (−)', f'Rs. {float(total_dr):,.2f}', DANGER),
        sum_row('Closing Balance',  f'Rs. {float(closing_bal):,.2f}', BLUE, bold=True),
        sum_row('Total Transactions', str(transactions.count())),
    ], colWidths=[W * 0.22, W * 0.28])
    sum_block.setStyle(TableStyle([
        ('SPAN',         (0, 0), (1, 0)),
        ('BACKGROUND',   (0, 0), (1, 0), LIGHT),
        ('TOPPADDING',   (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
        ('LEFTPADDING',  (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [WHITE, GRAY_BG]),
        ('LINEBELOW',    (0, 0), (-1, -1), 0.3, BORDER),
        ('BOX',         (0, 0), (-1, -1), 1, BORDER),
        ('LINEABOVE',    (0, 4), (-1, 4), 1.2, BLUE),   # closing bal divider
    ]))

    combined = Table([[acct_block, Spacer(4*mm, 1), sum_block]],
                     colWidths=[W * 0.5, 4*mm, W * 0.5 - 4*mm])
    combined.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
    ]))
    story.append(combined)
    story.append(Spacer(1, 6*mm))

    # ════════════════════════════════════
    # TRANSACTION TABLE
    # ════════════════════════════════════
    story.append(Paragraph('TRANSACTION DETAILS', styles['section_title']))
    story.append(Spacer(1, 2*mm))

    # Header row
    col_widths = [W*0.13, W*0.13, W*0.32, W*0.18, W*0.12, W*0.12]
    hdr_style  = ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=8,
                                 textColor=WHITE)

    tx_rows = [[
        Paragraph('Date', hdr_style),
        Paragraph('Type', hdr_style),
        Paragraph('Description', hdr_style),
        Paragraph('Amount', ParagraphStyle('thr', fontName='Helvetica-Bold',
                                            fontSize=8, textColor=WHITE,
                                            alignment=TA_RIGHT)),
        Paragraph('Cr/Dr', ParagraphStyle('thc', fontName='Helvetica-Bold',
                                           fontSize=8, textColor=WHITE,
                                           alignment=TA_CENTER)),
        Paragraph('Balance', ParagraphStyle('thrb', fontName='Helvetica-Bold',
                                             fontSize=8, textColor=WHITE,
                                             alignment=TA_RIGHT)),
    ]]

    TYPE_LABELS = {
        'deposit':           'Deposit',
        'withdraw':          'Withdraw',
        'transfer_sent':     'Sent',
        'transfer_received': 'Received',
    }

    for tx in transactions:
        is_credit = tx.transaction_type in ('deposit', 'transfer_received')
        sign      = '+' if is_credit else '−'
        amt_style = styles['amount_cr'] if is_credit else styles['amount_dr']
        cr_dr     = ParagraphStyle('crd', fontName='Helvetica-Bold', fontSize=8,
                                   textColor=SUCCESS if is_credit else DANGER,
                                   alignment=TA_CENTER)

        desc_lines = [tx.transaction_type.replace('_', ' ').title()]
        if tx.related_account_name:
            action = 'To' if tx.transaction_type == 'transfer_sent' else 'From'
            desc_lines.append(f'{action}: {tx.related_account_name}')
        if tx.remark:
            desc_lines.append(tx.remark)
        if tx.related_account_number:
            desc_lines.append(f'Acc: {tx.related_account_number}')

        desc_para = Paragraph(
            desc_lines[0] + ('<br/>' if len(desc_lines) > 1 else '') +
            '<br/>'.join(f'<font size="7" color="#64748b">{l}</font>'
                         for l in desc_lines[1:]),
            ParagraphStyle('desc', fontName='Helvetica-Bold', fontSize=8.5,
                           textColor=NAVY, leading=12)
        )

        tx_rows.append([
            Paragraph(tx.created_at.strftime('%d %b %Y\n%I:%M %p'),
                      ParagraphStyle('dt', fontName='Helvetica', fontSize=7.5,
                                     textColor=MUTED, leading=11)),
            Paragraph(TYPE_LABELS.get(tx.transaction_type, ''),
                      ParagraphStyle('ty', fontName='Helvetica', fontSize=8,
                                     textColor=NAVY)),
            desc_para,
            Paragraph(f'{sign} Rs.{float(tx.amount):,.2f}', amt_style),
            Paragraph('CR' if is_credit else 'DR', cr_dr),
            Paragraph(f'Rs.{float(tx.balance_after):,.2f}',
                      ParagraphStyle('bal', fontName='Helvetica', fontSize=8,
                                     textColor=MUTED, alignment=TA_RIGHT)),
        ])

    if not transactions.exists():
        tx_rows.append([
            Paragraph('No transactions in this period.',
                       ParagraphStyle('nt', fontName='Helvetica', fontSize=9,
                                      textColor=MUTED, alignment=TA_CENTER)),
            '', '', '', '', ''
        ])

    tx_tbl = Table(tx_rows, colWidths=col_widths, repeatRows=1)

    row_count = len(tx_rows)
    tx_tbl.setStyle(TableStyle([
        # Header
        ('BACKGROUND',   (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR',    (0, 0), (-1, 0), WHITE),
        ('TOPPADDING',   (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING',(0, 0), (-1, 0), 8),
        ('LEFTPADDING',  (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        # Rows
        ('TOPPADDING',   (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING',(0, 1), (-1, -1), 6),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [WHITE, GRAY_BG]),
        ('LINEBELOW',    (0, 0), (-1, -1), 0.3, BORDER),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX',          (0, 0), (-1, -1), 1, BORDER),
        # No transactions span
        *([('SPAN', (0, 1), (-1, 1))] if not transactions.exists() else []),
    ]))
    story.append(tx_tbl)
    story.append(Spacer(1, 6*mm))

    # ════════════════════════════════════
    # FOOTER
    # ════════════════════════════════════
    story.append(HRFlowable(width='100%', thickness=1, color=BORDER))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        'This is a system-generated statement and does not require a signature. '
        'For queries contact support@apexbank.in or call 1800-123-4567 (24x7 Toll-Free).<br/>'
        f'Generated on {now.strftime("%d %b %Y at %I:%M %p")}  |  '
        f'Apex Bank — IFSC: {account.ifsc_code}  |  RBI Regulated',
        styles['footer']
    ))

    doc.build(story)
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()

    fname = f"ApexBank_Statement_{account.account_number}_{period}.pdf"

    # ── Email the password-protected statement to the account holder ──
    email = EmailMessage(
        subject="Your Apex Bank Account Statement",
        body=(
            f"Hi {account.full_name},\n\n"
            f"Please find attached your Apex Bank account statement for the "
            f"period: {period_label}.\n\n"
            f"This PDF is password protected for your security.\n"
            f"Password: your registered mobile number (e.g. 9876543210)\n\n"
            f"Regards,\nApex Bank"
        ),
        from_email=None,
        to=[account.email],
    )
    email.attach(fname, pdf_bytes, 'application/pdf')
    email.send(fail_silently=True)

    messages.success(
        request,
        f"✓ Statement sent to {account.email}! Check your inbox "
        f"(password = your registered mobile number)."
    )
    return redirect('home')