# © 2024 Daniel Eduardo Diaz Mateo <daniel.diaz@isjo-technology.com>

from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    condo_default_journal = fields.Many2one(
        comodel_name='account.journal',
        string='Mora Diario',
        config_parameter='condo.default.journal'
    )

    account_charge = fields.Many2one(
        comodel_name='account.account',
        string='Otro Ingreso por Mora',
        domain=[('account_type', 'in', ['income_other', 'income'])],
        config_parameter='condo.charge.account'
    )

    condo_journal = fields.Many2one(
        comodel_name='account.journal',
        string='Condo Diario',
        config_parameter='condo.condo.journal',
        domain=[('type', 'in', ['bank', 'cash'])]
    )
