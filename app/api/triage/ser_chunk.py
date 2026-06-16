from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ai.ai_embedding import Embedding1024DB
from app.db.models.inv import InvoiceDB, InvoiceItemDB, InvoicePaymentDB
from app.schemas.sch_ai import JWType

from .inv2content import invoice_to_content


class InvChunkService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def rebuild_chunks(self, zjwt: JWType) -> dict:
        await self.db.execute(delete(Embedding1024DB))
        await self.db.commit()

        result = await self.db.execute(select(InvoiceDB))
        invoices = result.scalars().all()
        invoice_ids = [inv.id for inv in invoices]

        items_by_inv: dict = {}
        payments_by_inv: dict = {}
        if invoice_ids:
            item_res = await self.db.execute(select(InvoiceItemDB).where(InvoiceItemDB.inv_id.in_(invoice_ids)))
            for item in item_res.scalars().all():
                items_by_inv.setdefault(item.inv_id, []).append(item)

            pay_res = await self.db.execute(
                select(InvoicePaymentDB).where(InvoicePaymentDB.inv_id.in_(invoice_ids))
            )
            for payment in pay_res.scalars().all():
                payments_by_inv.setdefault(payment.inv_id, []).append(payment)

        rows: list[Embedding1024DB] = []
        for invoice in invoices:
            content = invoice_to_content(
                invoice=invoice,
                items=items_by_inv.get(invoice.id, []),
                payments=payments_by_inv.get(invoice.id, []),
            )
            if not content:
                continue
            rows.append(
                Embedding1024DB(
                    source_id=invoice.id,
                    ten_id=invoice.ten_id,
                    biz_id=invoice.biz_id,
                    cli_id=invoice.cli_id,
                    usr_id=invoice.usr_id,
                    created_by=invoice.created_by,
                    chunk=content,
                    emb1024=[0.0] * 1024,
                )
            )

        if rows:
            self.db.add_all(rows)
        await self.db.commit()

        return {
            "invoices_processed": len(invoices),
            "invoices_chunked": len(rows),
            "chunks_created": len(rows),
        }
