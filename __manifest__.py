{
    "name": "Bebemálaga - Documentos comerciales",
    "version": "19.0.1.0.0",
    "summary": "Presupuesto, pedido, albarán, factura, mercancía retirada y ticket TPV con el formato de Bebemálaga",
    "category": "Sales",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "sale_stock",
        "account",
        "stock",
        "point_of_sale",
    ],
    "data": [
        "report/report_actions.xml",
        "report/sale_order_report.xml",
        "report/account_move_report.xml",
        "report/stock_picking_report.xml",
        "report/goods_withdrawal_report.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "cs_bebemalaga_reports/static/src/app/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
