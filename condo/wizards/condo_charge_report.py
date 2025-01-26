# © 2024 Daniel Eduardo Diaz Mateo <daniel.diaz@isjo-technology.com>

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CondoContractLineWizard(models.TransientModel):
    _name = 'condo.charge.report'
    _description = 'Condo charge Report'

    partner_ids = fields.Many2many('res.partner', string='Contract')
    all_partners = fields.Boolean(string='Select All Contract')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    def action_generate_charge_report(self):
        domain = [
            ('date', '>', self.start_date),
            ('date', '<', self.end_date),
            ('line_paid_status', '=', False),
        ]
        contract_lines = self.env['condo.contract.line'].search(domain)
        if not contract_lines:
            raise UserError(_('No record found...!'))
        else:
            data = {'ids': [], 'model_id': self.id, 'form': self.read()[0], 'contract_lines': contract_lines}
            return self.env.ref('condo.action_report_condo_charge').report_action(
                self, data=data
            )
