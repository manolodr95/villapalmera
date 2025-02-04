# © 2024 Daniel Eduardo Diaz Mateo <daniel.diaz@isjo-technology.com>

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class MakePayment(models.TransientModel):
    _name = "make.payment"
    _description = "Make Payment"

    auto_select = fields.Boolean(
        string="Applied unique paid",
        default=True,
        store=True
    )

    contract_line_ids = fields.Many2many(
        "condo.contract.line",
        "first_contract_line",
        "first_contract_line_id",
        "contract_line_rel",
        string="Contract Line",
    )

    condo_contract_line_ids = fields.Many2many(
        "condo.contract.line",
        "second_contract_line",
        "second_contract_line_id",
        "second_contract_line_rel",
        string="Contract Line",
    )
    condo_contract_id = fields.Many2one("condo.contract", string="Contract")
    payment_amount = fields.Float(string="Payment Amount")
    payment_date = fields.Date(string="Payment Date", default=fields.Date.today())
    comment = fields.Text(string="Comment")

    def make_full_payment(self, amount_due, contract_id, contract_line_id):
        payment_method_id = payment = self.env["account.payment.method"].search(
            [("payment_type", "=", "inbound")], limit=1, order="id desc"
        )
        payload = {
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": contract_id.partner_id.id,
            "payment_method_id": payment_method_id.id,
            "amount": amount_due,
            "journal_id": 6, # contract_id.journal_id.id,
            "date": self.payment_date,
            "ref": self.comment,
            "contract_id": contract_id.id,
            "contract_line_id": contract_line_id.id,
        }
        contract_line_id.auto_payment += amount_due
        contract_line_id.left_payment = (
            contract_line_id.amount_subtotal - contract_line_id.auto_payment
        )
        payment_done = contract_line_id.patial_payment + amount_due
        payment = self.env["account.payment"].create(payload)
        contract_line_id.write(
            {"payment_id": payment.id, "state": "paid", "patial_payment": payment_done}
        )
        payment.action_post()
        return True

    def make_partial_payment(self, amount, contract_id, contract_line_id):
        payment_method_id = payment = self.env["account.payment.method"].search(
            [("payment_type", "=", "inbound")], limit=1, order="id desc"
        )
        payload = {
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": contract_id.partner_id.id,
            "payment_method_id": payment_method_id.id,
            "amount": amount,
            "journal_id": contract_id.journal_id.id,
            "date": self.payment_date,
            "ref": self.comment,
            "contract_id": contract_id.id,
            "contract_line_id": contract_line_id.id,
        }
        if not contract_line_id.payment_id:
            payment = self.env["account.payment"].create(payload)
            contract_line_id.write({"payment_id": payment.id, "state": "partial"})
            if amount >= contract_line_id.amount_subtotal:

                contract_line_id.payment_id.action_post()
                contract_line_id.patial_payment += amount
                contract_line_id.state = "paid"
            else:
                amount = contract_line_id.patial_payment + amount
                contract_line_id.state = "partial"
                contract_line_id.patial_payment += amount

            contract_line_id.auto_payment = amount
            contract_line_id.left_payment = (
                contract_line_id.amount_subtotal - contract_line_id.auto_payment
            )
        else:
            amount = contract_line_id.patial_payment + amount
            contract_line_id.auto_payment = amount
            contract_line_id.left_payment = (
                contract_line_id.amount_subtotal - contract_line_id.auto_payment
            )
            contract_line_id.write({"patial_payment": amount, "state": "partial"})
            if amount >= contract_line_id.amount_subtotal:
                contract_line_id.payment_id.action_post()
                contract_line_id.write({"state": "paid"})

    # funcion anterior
    @api.onchange("contract_line_ids")
    def onchange_contract_line(self):
        for obj in self:
            payment_amount = 0
            for line in obj.contract_line_ids:
                payment_amount += line.left_payment
            obj.payment_amount = payment_amount

    @api.model
    def default_get(self, vals):
        res = super(MakePayment, self).default_get(vals)
        active_id = self.env.context.get("active_id")
        if active_id:
            contract_id = self.env["condo.contract"].browse(active_id)
            res["condo_contract_id"] = contract_id.id
            contract_lines = []
            for line in contract_id.line_ids:
                if line.state != "paid":
                    contract_lines.append(line.id)
            res["condo_contract_line_ids"] = [(6, 0, contract_lines)]
        return res

    def action_generate_partial_payment(self):
        if self.condo_contract_id.state != 'confirm':
            raise UserError("No se pueden realizar pagos hasta que el documento esté en estado 'Confirmado'.")

        payment_method_id = self.env['account.payment.method'].search([('payment_type', '=', 'inbound')], limit=1)
        condo_journal_id = int(self.env['ir.config_parameter'].sudo().get_param('condo.default.journal'))
        condo_payment_id = int(self.env['ir.config_parameter'].sudo().get_param('condo.condo.journal'))
        condo_charge_account_id = int(self.env['ir.config_parameter'].sudo().get_param('condo.charge.account'))

        if self.auto_select:
            unique_auto_payment = auto_payment = self.payment_amount
            mora_payment = None

            # Ordenar las líneas de contrato pendientes por fecha de vencimiento
            ordered_lines = self.condo_contract_id.line_ids.filtered(lambda l: l.state in ('open', 'partial')).sorted(
                'date')
         
            for line in ordered_lines:
                if auto_payment <= 0:
                    break  # Detener si no hay más monto disponible para pagar

                # Buscar la factura de mora relacionada con la línea del contrato
                mora_invoice = self.env['account.move'].search(
                    [('contract_line_id', '=', line.id), ('move_type', '=', 'out_invoice'),
                     ('journal_id.is_active', '=', True), ('payment_state', '!=', 'paid')], limit=1)

                mora_payment_amount = 0.0
                if mora_invoice:
                    mora_payment_amount = min(auto_payment, mora_invoice.amount_residual)
                    if mora_payment_amount > 0:
                        mora_payment_payload = {
                            'payment_type': 'inbound',
                            'partner_type': 'customer',
                            'partner_id': line.partner_id.id,
                            'payment_method_id': payment_method_id.id,
                            'amount': mora_payment_amount,
                            'journal_id': condo_payment_id,
                            'date': self.payment_date,
                            'ref': f"Mora - {self.comment if self.comment else ''} {'- ' if self.comment else ''}{line.name}",
                            'contract_id': self.condo_contract_id.id,
                            'contract_line_id': line.id,
                        }
                        mora_payment = self.env['account.payment'].create(mora_payment_payload)
                        mora_payment.action_post()  # Registrar el pago de la mora
                        auto_payment -= mora_payment_amount  # Restar el monto pagado de mora del pago disponible
                        unique_auto_payment -= mora_payment_amount  # Restar el monto pagado de mora del pago disponible

                        # Aplicar el pago a la factura de mora
                        mora_invoice.js_assign_outstanding_line(
                            mora_payment.line_ids.filtered(
                                lambda l: l.account_id.account_type == 'asset_receivable').id)
                        # Actualizar el saldo restante de la mora
                        line.late_payment -= mora_payment_amount
                

                payment_needed = line.amount_subtotal - line.patial_payment

                # if payment_needed <= auto_payment:
                if payment_needed >= auto_payment:
                    # Caso de pago completo
                    line_payment = payment_needed
                    auto_payment -= line_payment
                    line.patial_payment = 0 # line_payment
                    line.left_payment = 0  # No queda nada por pagar
                    line.auto_payment += line_payment
                    line.line_paid_status = True
                    line.state = 'paid'
                    line.payment_id = mora_payment.id if mora_payment else None
                else:
                    # Caso de pago parcial
                    line_payment = auto_payment
                    line.patial_payment += line_payment
                    line.left_payment -= line_payment
                    line.auto_payment += line_payment
                    line.state = 'partial'
                    line.payment_id = mora_payment.id if mora_payment else None
                    auto_payment = 0  # Todo el auto_payment fue usado

                # Asegurarse de que no quede residual en left_payment
                if abs(line.left_payment) < 0.01:
                    line.left_payment = 0
                    line.state = 'paid'
                
            # Si queda algún monto después de pagar la mora, aplicarlo al contrato principal
            if unique_auto_payment > 0:
                payment_amount = unique_auto_payment
                payment_payload = {
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': line.partner_id.id,
                    'payment_method_id': payment_method_id.id,
                    'amount': payment_amount,
                    'journal_id': condo_payment_id,
                    'date': self.payment_date,
                    'ref': f"Cuota - {self.comment if self.comment else ''} {'- ' if self.comment else ''}",
                    'contract_id': self.condo_contract_id.id,
                    'contract_line_id': line.id,
                }
                payment = self.env['account.payment'].create(payment_payload)
                payment.action_post()  # Registrar el pago del contrato principal
                unique_auto_payment -= payment_amount

            # Verificar si todas las cuotas están pagadas
            all_paid = all(line.state == 'paid' for line in self.condo_contract_id.line_ids)
            self.condo_contract_id.cuote_completed = all_paid

        if not self.auto_select:
            auto_payment = self.payment_amount

            for contract in self.contract_line_ids:
                if contract.id in self.contract_line_ids.ids:
                    # Ordenar las líneas de contrato por la fecha de vencimiento
                    ordered_lines = self.contract_line_ids.contract_id.line_ids.sorted(lambda l: l.date)
                    previous_unpaid_found = False
                    previous_unpaid_id = 0
                    cuote_previous = None
                    # Obtener las líneas seleccionadas para pago que no estén completamente pagadas, ordenadas por fecha
                    selected_lines = self.contract_line_ids.filtered(lambda l: l.state in ('open', 'partial')).sorted(lambda l: l.date)
                    cuote_previous_unpaid_found = [item for item in ordered_lines.filtered(lambda l: l.state in ('open', 'partial')).sorted(lambda l: l.date).ids if item not in selected_lines.filtered(lambda l: l.state in ('open', 'partial')).sorted(lambda l: l.date).ids ]
                    # Obtener la última línea en el contrato ordenado (por fecha) como la primera a pagar
                    cuote_separation = ordered_lines[0]  # Cambiar aquí a la última línea
                    # Recorrer las líneas de contrato
                    for index, line in enumerate(selected_lines):
                        # si es la primera cuota
                        if contract.id == cuote_separation.id or previous_unpaid_found and previous_unpaid_id < line.id:
                            break
                        if cuote_separation.id != contract.id:
                            # Verificar si cuote_previous_unpaid_found tiene elementos
                            if cuote_previous_unpaid_found:
                                # Obtener el registro anterior en la lista ordenada y que aun sigue abierto y no fue seleccionado
                                cuote_previous = ordered_lines.browse(cuote_previous_unpaid_found[0]) or None

                                # Aquí puedes validar si cuote_previous es None o un registro
                                if cuote_previous:
                                    print(f"Cuota anterior: {cuote_previous.name}")
                                else:
                                    print("No hay cuota anterior")

                        if contract.id in selected_lines.ids and cuote_separation.id != contract.id:

                            # esta parte del codigo ocurrira unicamente sin no se ha pagado la cuota inicial
                            if cuote_separation.state in ('open', 'partial'):
                                previous_unpaid_found = True
                            if previous_unpaid_found and cuote_separation.state in ('open', 'partial'):
                                raise UserError(
                                    'No puedes pagar una cuota nueva sin antes pagar completamente las anteriores.')

                            if previous_unpaid_found and line.state in ('open', 'partial') or (cuote_previous and cuote_previous.id < contract.id):
                                raise UserError(
                                    'No puedes pagar una cuota nueva sin antes pagar completamente las anteriores.')
                            # # Si encontramos una cuota sin pagar, marcamos la variable
                            # if line.state in ('open', 'partial'):
                            #     previous_unpaid_found = True
                            #     previous_unpaid_id = line.id

                    # Buscar la factura de mora relacionada con la línea del contrato
                    mora_invoice = self.env['account.move'].search(
                        [('contract_line_id', '=', contract.id), ('move_type', '=', 'out_invoice'),
                         ('journal_id.is_active', '=', True), ('payment_state', '!=', 'paid')], limit=1)
                    mora_payment_amount = 0.0
                    if mora_invoice:
                        mora_payment_amount = min(auto_payment, mora_invoice.amount_residual)
                        if mora_payment_amount > 0:
                            mora_payment_payload = {
                                'payment_type': 'inbound',
                                'partner_type': 'customer',
                                'partner_id': contract.partner_id.id,
                                'payment_method_id': payment_method_id.id,
                                'amount': mora_payment_amount,
                                'journal_id': condo_payment_id,
                                'date': self.payment_date,
                                'ref': f"Mora - {self.comment if self.comment else ''} {'- ' if self.comment else ''}{contract.name}",
                                'contract_id': self.condo_contract_id.id,
                                'contract_line_id': contract.id,
                            }
                            mora_payment = self.env['account.payment'].create(mora_payment_payload)
                            mora_payment.action_post()  # Registrar el pago de la mora
                            auto_payment -= mora_payment_amount  # Restar el monto pagado de mora del pago disponible

                            # Aplicar el pago a la factura de mora
                            mora_invoice.js_assign_outstanding_line(
                                mora_payment.line_ids.filtered(
                                    lambda l: l.account_id.account_type == 'asset_receivable').id)
                            # Actualizar el saldo restante de la mora a 0 porque se ha pagado por completo
                            contract.late_payment -= mora_payment_amount # 0

                    # Si queda algún monto después de pagar la mora, aplicarlo al contrato principal
                    if auto_payment > 0:
                        payment_amount = min(auto_payment, contract.amount_due)
                        payment_payload = {
                            'payment_type': 'inbound',
                            'partner_type': 'customer',
                            'partner_id': contract.partner_id.id,
                            'payment_method_id': payment_method_id.id,
                            'amount': payment_amount,
                            'journal_id': condo_payment_id,
                            'date': self.payment_date,
                            'ref': f"Cuota - {self.comment if self.comment else ''} {'- ' if self.comment else ''}{contract.name}",
                            'contract_id': self.condo_contract_id.id,
                            'contract_line_id': contract.id,
                        }
                        payment = self.env['account.payment'].create(payment_payload)
                        payment.action_post()  # Registrar el pago del contrato principal
                        auto_payment -= payment_amount

                    # Procesar las líneas seleccionadas
                    selected_lines = self.contract_line_ids.filtered(lambda x: x.id == contract.id)

                    for line in selected_lines:
                        # Monto necesario para completar esta línea
                        payment_needed = line.amount_subtotal - line.patial_payment

                        # if (payment_needed <= auto_payment or payment_needed <= (payment_amount + mora_payment_amount)) and auto_payment > 0:
                        if (payment_needed >= auto_payment or payment_needed >= (payment_amount + mora_payment_amount)):
                            # Caso de pago completo
                            line_payment = payment_needed
                            # auto_payment -= line_payment
                            # line.patial_payment += line_payment
                            line.left_payment = 0  # No queda nada por pagar
                            line.auto_payment += line_payment
                            line.line_paid_status = True
                            line.state = 'paid'
                            line.payment_id = payment.id
                        else:
                            # Caso de pago parcial
                            line_payment = payment_amount
                            if payment_amount < payment_needed:
                                line.patial_payment += line_payment
                            else:
                                line.patial_payment = 0
                            line.left_payment -= line_payment
                            line.auto_payment += line_payment
                            line.state = 'partial' if payment_amount < payment_needed else 'paid'
                            line.payment_id = payment.id
                            auto_payment = 0  # Todo el auto_payment fue usado
                        # Asegurarse de que no quede residual en left_payment
                        if abs(line.left_payment) < 0.01:
                            line.left_payment = 0
                            line.state = 'paid'
                    # Si encontramos una cuota sin pagar, marcamos la variable
                    if line.state in ('open', 'partial'):
                        previous_unpaid_found = True
                        previous_unpaid_id = line.id

                # Verificar si todas las cuotas están pagadas
                all_paid = all(line.state == 'paid' for line in contract.contract_id.line_ids)
                contract.contract_id.cuote_completed = all_paid

        return True
