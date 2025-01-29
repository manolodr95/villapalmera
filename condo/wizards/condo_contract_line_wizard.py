# © 2024 Daniel Eduardo Diaz Mateo <daniel.diaz@isjo-technology.com>

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CondoContractLineWizard(models.TransientModel):
    _name = 'condo.contract.line.wizard'
    _description = 'Condo Contract Line Wizard'

    amount = fields.Float(string='Amount', required=True)

    def action_generate_partial_payment(self):
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            line = self.env['condo.contract.line'].browse(active_ids)
            if self.amount <= 0:
                raise ValidationError(_('Patial payment amount must be greater than 0'))
            line.action_generate_partial_payment(self.amount)
        return {'type': 'ir.actions.act_window_close'}
