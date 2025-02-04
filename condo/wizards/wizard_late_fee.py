# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from datetime import timedelta

import logging

_logger = logging.getLogger(__name__)


class WizardApplyLateFee(models.TransientModel):
    _name = 'wizard.apply.late.fee'
    _description = 'Apply Late Fee'

    def _get_due_date(self):
        return max(self.line_ids.sorted(key=lambda r: r.sequence, reverse=True)).date

    contract_line_id = fields.Many2one(
        comodel_name='condo.contract.line',
        string='Contract Line',
        required=True
    )

    charge_amount = fields.Monetary(
        string='Late Fee',
        required=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='contract_line_id.currency_id',
        readonly=True
    )

    def action_apply_late_fee(self):
        self.ensure_one()
        contract_line = self.contract_line_id

        #buscamos si ya existe un documento de mora para este registro
        not_paid_invs = contract_line.env['account.move'].search([
            ('contract_line_id', '=', int(self.contract_line_id.id)),
            ('payment_state', 'not in', ('paid', 'in_payment')),
            ('move_type','in', ('out_invoice', 'out_refund'))
        ])
        # price_unit = 0.0
        # buscar la factura y revisar si la misma ya existe y si esta pagada pues no debe hacer nada sino esta pagada ni partialmente pagada entonces
        # debera buscar la factura y buscar los montos
        for inv in not_paid_invs:
            if inv and inv.payment_state not in ['paid', 'in_payment']:
                # Factura existe y no está pagada (ni totalmente ni parcialmente)
                # Cambiar el valor de la mora o el monto total de la factura
                inv.button_draft()
                for inv_line in inv.invoice_line_ids:
                    # price_unit += inv_line.price_unit
                    inv_line.write({
                        'price_unit': self.charge_amount # + inv_line.price_unit
                    })
                inv.action_post()
        # Buscar los pagos por mora que se hayan realizado
        charge_paid = contract_line.env['account.move'].search([
            ('contract_line_id', '=', self.contract_line_id.id),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('journal_id', '=', self.env['account.journal'].search([('is_active', '=', True)], limit=1).id) # Filtra por diario de mora si existe
        ])
        # Inicializar las variables
        charge_amount = 0.0
        late_payment = self.charge_amount or 0.0  # Valor de mora no pagada
        # Si se han encontrado registros de pagos de mora
        if charge_paid:
            # Sumar el total de las moras pagadas previamente
            for charge in charge_paid:
                charge_amount += charge.amount_total
            # Si solo hay un pago de mora, entonces charge_amount debe ser igual a late_payment
            if len(charge_paid) == 1:
                charge_amount = late_payment
        if contract_line.state == 'partial':
            # Si hay moras previas, sumar la nueva mora al charge_amount
            # Si no hay pagos previos, charge_amount será igual a late_payment
            contract_line.write({
                'charge_amount': charge_amount if charge_amount > 0.0 else late_payment,  # Sumar mora pagada (si existe) más el nuevo cargo
                'late_payment': late_payment  # Mantener o actualizar el valor de mora no pagada
            })

            # Actualizar el subtotal
            contract_line._onchange_amount_subtotal()
            if not not_paid_invs:
                # crear factura cargo a mora
                product = self.env.ref("condo.contract_product_charge")
                accounts = product.product_tmpl_id._get_product_accounts()
                payload = {
                    "move_type": "out_invoice",
                    "partner_id": contract_line.partner_id.id,
                    "invoice_date": fields.Date.today(),  # self.start_date,
                    "journal_id": self.env['account.journal'].search([('is_active', '=', True)], limit=1).id,
                    "invoice_date_due": fields.Date.today() + timedelta(days=30),
                    # Calcular la fecha de vencimiento (por ejemplo, 30 días después de la fecha actual)
                    "company_id": contract_line.contract_id.company_id.id,
                    "contract_id": contract_line.contract_id.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": product.id,
                                "name": f"Cargo por mora: {self.charge_amount} - Contrato: {contract_line.name} / [{contract_line.partner_id.project_name}] {contract_line.partner_id.name}",
                                "price_unit": self.charge_amount,
                                "account_id": accounts.get("income").id,
                            },
                        )
                    ],
                }
                inv = self.env["account.move"].create(payload)
                inv.action_post()

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

        # Si hay moras previas, sumar la nueva mora al charge_amount
        # Si no hay pagos previos, charge_amount será igual a late_payment
        contract_line.write({
            'charge_amount': charge_amount if charge_amount > 0.0 else late_payment,  # Sumar mora pagada (si existe) más el nuevo cargo
            'late_payment': late_payment  # Mantener o actualizar el valor de mora no pagada
        })

        if not not_paid_invs:
            # crear factura cargo a mora
            product = self.env.ref("condo.contract_product_charge")
            accounts = product.product_tmpl_id._get_product_accounts()
            payload = {
                "move_type": "out_invoice",
                "partner_id": contract_line.partner_id.id,
                "invoice_date": fields.Date.today(), # self.start_date,
                "journal_id": self.env['account.journal'].search([('is_active', '=', True)], limit=1).id,
                "invoice_date_due": fields.Date.today() + timedelta(days=30), # Calcular la fecha de vencimiento (por ejemplo, 30 días después de la fecha actual)
                "company_id": contract_line.contract_id.company_id.id,
                "contract_id": contract_line.contract_id.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "name": f"Cargo por mora: {self.charge_amount} - Contrato: {contract_line.name} / [{contract_line.partner_id.project_name}] {contract_line.partner_id.name}",
                            "price_unit": self.charge_amount,
                            "account_id": accounts.get("income").id,
                        },
                    )
                ],
            }
            inv = self.env["account.move"].create(payload)
            inv.action_post()

        # Actualizar el subtotal
        contract_line._onchange_amount_subtotal()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
