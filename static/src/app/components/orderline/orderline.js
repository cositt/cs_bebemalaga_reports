import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";

patch(Orderline.prototype, {
    /**
     * El ticket de tienda muestra por línea la referencia del artículo, el
     * precio unitario y el descuento en formato "(20% Dto)", todo en un
     * único renglón bajo la descripción.
     */
    get lineScreenValues() {
        const vals = super.lineScreenValues;
        if (this.props.mode !== "receipt" || !this.line.order_id) {
            return vals;
        }
        const line = this.line;
        const discount = line.getDiscountStr();
        return {
            ...vals,
            bmProductRef: line.product_id?.default_code || "",
            bmUnitPrice: line.currencyDisplayPriceUnit,
            bmDiscount: discount && discount !== "0" ? `(${discount}% Dto)` : "",
        };
    },
});
