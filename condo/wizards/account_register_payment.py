# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import date

import logging

_logger = logging.getLogger(__name__)

from odoo import fields, models, api, _

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    contract_id = fields.Many2one(
        comodel_name='condo.contract',
        string='Contract',
        domain=[('state', 'in', ['confirm', 'done'])]
    )

    @api.onchange('contract_id')
    def _onchange_ref(self):
        for rec in self:
            rec.communication += ' - ' + rec.contract_id.name if rec.contract_id else ''

    def _create_payments(self):
        # Lógica de creación de pagos
        payments = super(AccountPaymentRegister, self)._create_payments()

        # Si el campo condo_contract_id está presente, pasa el valor al pago.
        if self.contract_id:
            for payment in payments:
                payment.write({
                    'contract_id': self.contract_id.id,
                })
        return payments

    def action_register_payment(self):
        return {
            'name': 'Register Payment',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'default_contract_id': self.contract_id.id,  # Aquí se pasa el contract_id
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_create_payments(self):
        payments = self._create_payments()

        # Actualizar el valor de contract_id en los pagos generados
        if self.contract_id:
            for payment in payments:
                payment.contract_id = self.contract_id.id
                self.contract_id._apply_payment(monto=payment.amount)

        if self._context.get('dont_redirect_to_payments'):
            return True

        action = {
            'name': _('Pagos'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }

        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })

        return action

