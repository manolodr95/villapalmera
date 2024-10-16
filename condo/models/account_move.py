# © 2024 Daniel Eduardo Diaz Mateo <daniel.diaz@isjo-technology.com>

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    contract_id = fields.Many2one(comodel_name='condo.contract', string='Contract')
    contract_line_id = fields.Many2one(comodel_name='condo.contract.line', string='Charge')
    # is_interest = fields.Boolean(string='Is Interest', default=False)




class AccountPayment(models.Model):
    _inherit = 'account.payment'

    contract_id = fields.Many2one(
        comodel_name='condo.contract', string='Contract Payment'
    )
    contract_line_id = fields.Many2one(
        comodel_name='condo.contract.line', string='Contract Payment Line'
    )
    amount_with_interest = fields.Monetary(string='Total Amount', required=False)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    project_name = fields.Char(
        string='Project Name',
        index=True
    )

class AccountJournal(models.Model):
    _inherit = 'account.journal'
    _description = 'Account Journal'

    is_active = fields.Boolean(string="usar en Mora?")

    @api.onchange('is_active')
    def onchnage_is_active(self):
        journals = self.env['account.journal'].search([])
        for rec in journals:
            if rec.id == self._origin.id:
                rec.is_active = True
            else:
                rec.is_active = False
