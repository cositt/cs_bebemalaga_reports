import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";

/**
 * El ticket de tienda muestra por línea la referencia del artículo, el precio
 * unitario y el descuento en formato "(20% Dto)", todo en un único renglón
 * bajo la descripción.
 *
 * Getters propios en lugar de ampliar `lineScreenValues`: ese getter (y el
 * `vals` de la plantilla) solo existe en compilaciones de Odoo 19 posteriores
 * a la de producción (19.0-20250918), donde la plantilla lee `line` y
 * `props.mode` directamente. Con `vals` el TPV se quedaba en blanco al añadir
 * la primera línea.
 */
patch(Orderline.prototype, {
    get bmIsReceipt() {
        return this.props.mode === "receipt";
    },

    get bmProductRef() {
        return this.line.product_id?.default_code || "";
    },

    get bmUnitPrice() {
        return this.formatCurrency(this.line.unitDisplayPrice);
    },

    get bmDiscount() {
        const discount = this.line.getDiscountStr();
        return discount && discount !== "0" ? `(${discount}% Dto)` : "";
    },
});
