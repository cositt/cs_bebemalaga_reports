# Bebemálaga — Documentos comerciales

Módulo de Odoo 19 que adapta los documentos comerciales de **Bebemálaga / Pequeño Planeta 2016 SL** al formato solicitado por la tienda: presupuesto, pedido, albarán, factura, documento de mercancía retirada y ticket de TPV.

No sustituye ninguna plantilla del núcleo: todo se aplica por herencia XPath sobre anclas `name=`/`id=` de las plantillas estándar de Odoo.

## Documentos que modifica

| Documento | Plantilla heredada | Fichero |
|-----------|--------------------|---------|
| Presupuesto y pedido de venta | `sale.report_saleorder_document` | `report/sale_order_report.xml` |
| Factura | `account.report_invoice_document` | `report/account_move_report.xml` |
| Albarán de entrega | `stock.report_delivery_document` | `report/stock_picking_report.xml` |
| Mercancía retirada (nuevo) | — | `report/goods_withdrawal_report.xml` |
| Ticket de TPV | `point_of_sale` (OWL) | `static/src/app/**` |

## Qué cambia en los PDF

Comunes a presupuesto, pedido, albarán y factura:

- **Columna de impuestos eliminada** y **columna de descuento siempre visible** (el núcleo la oculta cuando no hay descuentos).
- **Cantidad sin unidad de medida** y sin decimales.
- **"Base imponible"** en lugar de la traducción por defecto "Importe base" (`document_tax_totals_bm`, `document_tax_totals_bm_account`).
- **Recuadro de firma de conformidad** (plantilla compartida `conformity_signature`).
- **Avisos legales** al pie (plantilla compartida `legal_notes`): plazo de recogida, condiciones de OUTLET, plazo de devolución por vale e indicación de IVA.

Específicos:

- **Pedido / presupuesto:** forma de pago, importe cobrado e importe pendiente.
- **Factura:** cobrado y pendiente calculados desde `amount_residual` nativo.
- **Albarán:** cabeceras en español (Descripción / Pedido / Entregado), sin la columna "Unidades".

### Avisos legales (`legal_notes`)

Van en el módulo y **no** en `res.company.report_footer` de forma deliberada: el pie de empresa se imprimiría también en documentos de compra e inventario, donde estos avisos no aplican.

El bloque lleva `page-break-inside: avoid`; sin eso se parte entre páginas en presupuestos largos.

En la **factura** el bloque se ancla a `//div[@id='right-elements']/..` y no a `//div[@id='total']`, porque ese último nodo vive dentro de una columna estrecha flotada (`col-5 float-end`) y la firma y los avisos salían comprimidos a media anchura.

## Documento de mercancía retirada

Informe nuevo sobre `stock.picking`, disponible en el menú **Imprimir** del albarán (acción `action_report_goods_withdrawal`).

Los precios no se almacenan: se resuelven en `models/stock_picking.py`.

- `_bm_withdrawal_price()` busca el precio en `move.sale_line_id` y, si el albarán viene del TPV, en la línea de `pos_order_id` con el mismo producto. Si no hay ninguno de los dos devuelve cero en vez de inventar un precio.
- `_bm_withdrawal_lines()` prorratea el importe sobre la **cantidad entregada**, no sobre la pedida, para que una entrega parcial no imprima el total del pedido.
- `_bm_withdrawal_totals()` calcula base imponible, IVA y total con `taxes.compute_all()`.

## Ticket de TPV

- Cabecera de columnas en las líneas y **Id Caja** en el `ReceiptHeader`.
- Sin bloque de dirección de tienda ni "Con tecnología de Odoo".
- Por línea: referencia interna, precio unitario y descuento como `(20% Dto)`.

  ```
  1  Carrito de bebé City Tour 2 Baby Jogger (Exposición)  899,00 €
     AUTO-92364 · 899,00 €/ud
  ```

- Al **imprimir**, la letra baja a 11px (`receipt_print.scss`).

Dos detalles no evidentes:

- Las líneas usan `align-items-start`. La plantilla base centra verticalmente cantidad y descripción; al añadir la referencia, los nombres largos caían en una columna estrecha a media altura e ilegibles.
- `getQuantityStr()` devuelve un **objeto**, no una cadena, así que el guard del núcleo `line.getQuantityStr() != 1` nunca es falso y el precio unitario ya se imprime siempre, también con cantidad 1. No volver a añadirlo "porque el núcleo lo oculta": salen dos renglones repetidos.

El paso a 11px es paliativo: un ticket con muchas líneas volverá a paginar al imprimir en hoja. En rollo térmico continuo no aplica.

## Campos añadidos

`sale.order` (`models/sale_order.py`), ambos calculados y no almacenados:

| Campo | Descripción |
|-------|-------------|
| `amount_paid` | Suma de lo cobrado en las facturas publicadas del pedido, descontando abonos (`out_refund` resta). |
| `amount_pending` | `amount_total - amount_paid`. |

## Instalación

```bash
# El módulo debe estar en el addons_path del contenedor
odoo -c /etc/odoo/odoo.conf -i cs_bebemalaga_reports -d <base> --stop-after-init --no-http
```

Actualizar tras un cambio:

```bash
odoo -c /etc/odoo/odoo.conf -u cs_bebemalaga_reports -d <base> --stop-after-init --no-http
# reiniciar el contenedor para recompilar los assets del TPV
```

Dependencias: `sale_management`, `sale_stock`, `account`, `stock`, `point_of_sale`.

## Antes de instalar en producción

Comprobar que la arquitectura guardada en la base de destino coincide con la del código del contenedor. La plantilla `stock.stock_report_delivery_aggregated_move_lines` de producción envuelve los spans en un `<t t-if>` que no está en todas las compilaciones de Odoo 19; si el XPath no encuentra su ancla, la actualización del módulo falla.

Regla general para tocar estas plantillas: escribir los XPath contra el código del contenedor **y** contra la `arch` guardada en la base, nunca contra el repositorio de GitHub de Odoo.

## Verificación

Con el módulo instalado, `/report/html/<report_name>/<id>` recarga al instante; `/report/pdf/...` genera el PDF real, que es donde aparecen los problemas de paginación y anchura.

```
/report/html/sale.report_saleorder/<id>
/report/html/account.report_invoice/<id>
/report/html/stock.report_deliveryslip/<id>
/report/html/cs_bebemalaga_reports.report_goods_withdrawal/<id>
```

El ticket de TPV se renderiza siempre en `.render-container`, oculto fuera de impresión. `Imprimir recibo` llama a `window.print()` directamente y el diálogo modal congela el renderer, así que para inspeccionarlo conviene neutralizar `window.print` antes de pulsar y hacer visible ese contenedor.

## Licencia

LGPL-3.
