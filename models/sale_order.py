from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    amount_paid = fields.Monetary(
        string="Importe cobrado",
        compute="_compute_amount_paid",
        currency_field="currency_id",
        help="Suma de lo efectivamente cobrado en las facturas publicadas "
        "del pedido, descontando los abonos.",
    )
    amount_pending = fields.Monetary(
        string="Importe pendiente",
        compute="_compute_amount_paid",
        currency_field="currency_id",
    )

    @api.depends(
        "amount_total",
        "invoice_ids.state",
        "invoice_ids.move_type",
        "invoice_ids.amount_total",
        "invoice_ids.amount_residual",
    )
    def _compute_amount_paid(self):
        for order in self:
            paid = 0.0
            posted = order.invoice_ids.filtered(lambda m: m.state == "posted")
            for move in posted:
                sign = -1 if move.move_type == "out_refund" else 1
                paid += sign * (move.amount_total - move.amount_residual)
            order.amount_paid = paid
            order.amount_pending = order.amount_total - paid
