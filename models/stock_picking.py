from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _bm_withdrawal_price(self, move):
        """Precio unitario y descuento de una línea de movimiento.

        El albarán puede venir de un pedido de venta o de un ticket de TPV;
        se busca el origen en ese orden. Si no hay ninguno de los dos, se
        devuelve cero en lugar de inventar un precio.
        """
        sale_line = move.sale_line_id
        if sale_line:
            return sale_line.price_unit, sale_line.discount, sale_line.tax_ids

        pos_order = self.pos_order_id
        if pos_order:
            pos_line = pos_order.lines.filtered(
                lambda line: line.product_id == move.product_id
            )[:1]
            if pos_line:
                return pos_line.price_unit, pos_line.discount, pos_line.tax_ids

        return 0.0, 0.0, self.env["account.tax"]

    def _bm_withdrawal_lines(self):
        """Líneas del documento de mercancía retirada.

        Devuelve la cantidad realmente retirada junto con su importe. El
        importe se prorratea sobre la cantidad entregada, no sobre la pedida,
        para que una entrega parcial no imprima el total del pedido.
        """
        self.ensure_one()
        lines = []
        for move in self.move_ids.filtered(lambda m: m.quantity):
            price_unit, discount, _taxes = self._bm_withdrawal_price(move)
            lines.append(
                {
                    "ref": move.product_id.default_code or "",
                    "name": move.product_id.name,
                    "quantity": move.quantity,
                    "price_unit": price_unit,
                    "discount": discount,
                    "subtotal": price_unit * (1 - discount / 100.0) * move.quantity,
                }
            )
        return lines

    def _bm_withdrawal_totals(self):
        """Base imponible, IVA y total del documento de mercancía retirada."""
        self.ensure_one()
        untaxed = 0.0
        tax_amount = 0.0
        currency = self.company_id.currency_id
        for move in self.move_ids.filtered(lambda m: m.quantity):
            price_unit, discount, taxes = self._bm_withdrawal_price(move)
            base = price_unit * (1 - discount / 100.0) * move.quantity
            untaxed += base
            if taxes:
                computed = taxes.compute_all(
                    base,
                    currency=currency,
                    quantity=1.0,
                    product=move.product_id,
                    partner=self.partner_id,
                )
                tax_amount += computed["total_included"] - computed["total_excluded"]
        return {
            "untaxed": untaxed,
            "tax": tax_amount,
            "total": untaxed + tax_amount,
        }
