from datetime import date, datetime
from decimal import Decimal

from app.db.models.inv.i_nvoice import InvoiceDB
from app.db.models.inv.i_nvoice_item import InvoiceItemDB
from app.db.models.inv.i_nvoice_payment import InvoicePaymentDB


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def invoice_to_content(
    invoice: InvoiceDB,
    items: list[InvoiceItemDB],
    payments: list[InvoicePaymentDB],
) -> str:
    lines: list[str] = [
        "INVOICE HEADER",
        f"invoice_id={invoice.id}",
        f"invoice_number={_fmt(invoice.inv_number)}",
        f"invoice_title={_fmt(invoice.inv_title)}",
        f"invoice_date={_fmt(invoice.inv_date)}",
        f"invoice_due_date={_fmt(invoice.inv_due_date)}",
        f"invoice_currency={_fmt(invoice.inv_currency)}",
        f"invoice_reference={_fmt(invoice.inv_reference)}",
        f"invoice_payment_status={_fmt(invoice.inv_payment_status)}",
        f"subtotal={_fmt(invoice.inv_subtotal)}",
        f"discount={_fmt(invoice.inv_discount)}",
        f"tax_label={_fmt(invoice.inv_tax_label)}",
        f"tax_rate={_fmt(invoice.inv_tax_rate)}",
        f"tax_amount={_fmt(invoice.inv_tax_amount)}",
        f"shipping={_fmt(invoice.inv_shipping)}",
        f"handling={_fmt(invoice.inv_handling)}",
        f"deposit={_fmt(invoice.inv_deposit)}",
        f"adjustment={_fmt(invoice.inv_adjustment)}",
        f"other_charges_label={_fmt(invoice.inv_other_charges_label)}",
        f"other_charges_amount={_fmt(invoice.inv_other_charges_amount)}",
        f"total={_fmt(invoice.inv_total)}",
        f"paid_total={_fmt(invoice.inv_paid_total)}",
        f"balance_due={_fmt(invoice.inv_balance_due)}",
        "",
        "CLIENT",
        f"client_id={_fmt(invoice.client_id)}",
        f"client_number={_fmt(invoice.client_number)}",
        f"client_company_name={_fmt(invoice.client_company_name)}",
        f"client_contact_name={_fmt(invoice.client_contact_name)}",
        f"client_email={_fmt(invoice.client_email)}",
        f"client_mainphone={_fmt(invoice.client_mainphone)}",
        "",
        f"ITEMS count={len(items)}",
    ]

    for idx, item in enumerate(items, start=1):
        lines.append(
            " | ".join(
                [
                    f"item_{idx}",
                    f"name={_fmt(item.item_name)}",
                    f"number={_fmt(item.item_number)}",
                    f"sku={_fmt(item.item_sku)}",
                    f"qty={_fmt(item.item_quantity)}",
                    f"unit={_fmt(item.item_unit)}",
                    f"uom={_fmt(item.item_unit_of_measure)}",
                    f"rate={_fmt(item.item_rate)}",
                    f"amount={_fmt(item.item_amount)}",
                    f"description={_fmt(item.item_description)}",
                ]
            )
        )

    lines.append("")
    lines.append(f"PAYMENTS count={len(payments)}")
    for idx, payment in enumerate(payments, start=1):
        lines.append(
            " | ".join(
                [
                    f"payment_{idx}",
                    f"method={_fmt(payment.pm_name)}",
                    f"amount={_fmt(payment.pay_amount)}",
                    f"date={_fmt(payment.pay_date)}",
                    f"reference={_fmt(payment.pay_reference)}",
                    f"note={_fmt(payment.pay_note)}",
                ]
            )
        )

    if invoice.inv_notes:
        lines.extend(["", "INVOICE NOTES", _fmt(invoice.inv_notes)])
    if invoice.inv_terms_conditions:
        lines.extend(["", "TERMS", _fmt(invoice.inv_terms_conditions)])

    return "\n".join(lines).strip()
