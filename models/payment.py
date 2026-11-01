import re
from datetime import date
from decimal import Decimal
from db import query, execute
from models.notification import Notification
from models.quotation import Quotation
from models.user import User


class Payment:
    """Mga bayad sa isang quotation. Ang Paid ay kinukuwenta ng system: buo na ang bayad."""

    RECEIPT_RE = re.compile(r'^[A-Za-z0-9-]{1,20}$')

    @staticmethod
    def paid_total(quotation_id):
        return query("SELECT COALESCE(SUM(amount), 0) AS n FROM payments "
                     "WHERE quotation_id = %s AND voided_at IS NULL", (quotation_id,), one=True)['n']

    @classmethod
    def summary(cls, quotation):
        paid = cls.paid_total(quotation['id'])
        return {'total': quotation['total'], 'paid': paid, 'balance': max(quotation['total'] - paid, Decimal('0'))}

    @staticmethod
    def history(quotation_id):
        return query("SELECT p.*, u.first_name, u.last_name FROM payments p "
                     "LEFT JOIN users u ON u.id = p.recorded_by "
                     "WHERE p.quotation_id = %s ORDER BY p.id DESC", (quotation_id,))

    @classmethod
    def sync(cls, quotation_id):
        """I-update ang paid_at ng quotation: may petsa kapag buo na ang bayad, wala kapag may balance."""
        row = query("SELECT total, paid_at FROM quotations WHERE id = %s", (quotation_id,), one=True)
        fully_paid = cls.paid_total(quotation_id) >= row['total']
        if fully_paid and row['paid_at'] is None:
            execute("UPDATE quotations SET paid_at = NOW() WHERE id = %s", (quotation_id,))
        elif not fully_paid and row['paid_at'] is not None:
            execute("UPDATE quotations SET paid_at = NULL WHERE id = %s", (quotation_id,))
        return fully_paid

    @classmethod
    def clean(cls, form, quotation):
        """Sinusuri ang form ng bayad. Ibinabalik ang (data, errors)."""
        data, errors = {}, []
        balance = cls.summary(quotation)['balance']

        raw = form.get('amount', '').strip().replace(',', '')
        if Quotation.MONEY_RE.match(raw) and Decimal(raw) > 0:
            data['amount'] = Decimal(raw)
            if data['amount'] > balance:
                errors.append('The amount is more than the balance (P{:,.2f}).'.format(balance))
        else:
            errors.append('Enter the amount paid, like 5000 or 5000.50.')

        receipt = form.get('receipt_no', '').strip().upper()
        if not cls.RECEIPT_RE.match(receipt):
            errors.append('Enter the Receipt No. (letters, numbers and hyphens, up to 20 characters).')
        elif query("SELECT id FROM payments WHERE receipt_no = %s", (receipt,), one=True):
            errors.append(f'Receipt No. {receipt} was already recorded.')
        data['receipt_no'] = receipt

        try:
            paid_on = date.fromisoformat(form.get('paid_on', '').strip())
            if paid_on > date.today():
                raise ValueError
            data['paid_on'] = paid_on
        except ValueError:
            errors.append('Enter a valid payment date (not in the future).')

        note = ' '.join(form.get('note', '').split())
        if len(note) > 120:
            errors.append('The note is too long (120 characters maximum).')
        data['note'] = note or None
        return data, errors

    @classmethod
    def record(cls, application, quotation, data, by_user):
        execute("INSERT INTO payments (quotation_id, amount, receipt_no, paid_on, note, recorded_by) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (quotation['id'], data['amount'], data['receipt_no'], data['paid_on'], data['note'], by_user.id))
        fully_paid = cls.sync(quotation['id'])
        summary = cls.summary(quotation)
        details = [('Receipt No.', data['receipt_no']), ('Amount received', 'PHP {:,.2f}'.format(data['amount'])),
                   ('Balance', 'PHP {:,.2f}'.format(summary['balance']))]
        owner = User.find(application.user_id)
        if fully_paid:
            Notification.notify(owner, 'Payment received', 'Payment complete',
                                'Thank you! Your tuition is fully paid. The Registrar will now prepare your '
                                'Certificate of Registration.', details)
        else:
            Notification.notify(owner, 'Payment received', 'Payment received',
                                'We received your payment. Please see your remaining balance below.', details)
        return fully_paid

    @classmethod
    def void(cls, application, quotation, payment_id, by_user):
        """Kinakansela ang maling bayad. Hindi na puwede kapag may COR na (hindi na For Enrollment)."""
        if application.status != 'For Enrollment':
            raise ValueError('This student is already enrolled, so payments can no longer be voided.')
        row = query("SELECT * FROM payments WHERE id = %s AND quotation_id = %s", (payment_id, quotation['id']), one=True)
        if row is None:
            raise ValueError('Payment not found.')
        if row['voided_at'] is not None:
            raise ValueError('This payment was already voided.')
        execute("UPDATE payments SET voided_at = NOW(), voided_by = %s WHERE id = %s", (by_user.id, payment_id))
        cls.sync(quotation['id'])
        return row