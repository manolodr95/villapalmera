# © 2024 Daniel Eduardo Diaz Mateo <daniel.diaz@isjo-technology.com>

from decimal import Decimal, getcontext
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp

getcontext().prec = 6


class CondoChargeHistory(models.Model):
    _name = 'condo.charge.history'

    contract_line_id = fields.Many2one('condo.contract.line', string='Contract Line')
    contract_id = fields.Many2one('condo.contract', string='Contract')
    amount_status = fields.Float(string='Amount')
    charge_status = fields.Float(string='Charge')
    charge_create_date = fields.Date(string='charge Create Date')


class CondoContractLine(models.Model):
    _name = 'condo.contract.line'
    _description = 'Condo Contract Line'
    _order = 'sequence asc'

    state = fields.Selection(
        selection=[
            ('open', 'Open'),
            ('partial', 'Partial Payment'),
            ('paid', 'Paid'),
            ('cancel','Cancel')
        ],
        default='open',
        readonly=True,
    )

    name = fields.Char(
        compute='_compute_name',
        store=True
    )

    contract_id = fields.Many2one(
        comodel_name='condo.contract',
        required=True,
        readonly=True,
        ondelete='cascade',
    )

    contract_state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancelled', 'Cancelled'),
            ('closed', 'Closed'),
        ],
        related='contract_id.state',
        readonly=True,
        store=True,
        string='Contract State',
    )

    charge_line = fields.Boolean(
        string='Charge Line',
        default=False
    )

    late_payment = fields.Monetary(
        required=False,
        string='Late Payment',
        currency_field='currency_id',
        digits=dp.get_precision('charge'),
    )

    sequence = fields.Integer(
        required=True,
        readonly=True
    )

    date = fields.Date(
        required=True,
        help='Date when the payment will be accounted',
        string='Due Date'
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='contract_id.currency_id'
    )

    amount_due = fields.Monetary(
        required=True,
        string='Amount',
        currency_field='currency_id'
    )

    payment_id = fields.Many2one(
        comodel_name='account.payment',
        string='Payment',
        readonly=True
    )

    charge_amount = fields.Monetary(
        required=False,
        string='Late Fee',
        currency_field='currency_id',
        digits=dp.get_precision('charge'),
    )

    move_id = fields.Many2one(
        comodel_name='account.move',
        copy=False
    )

    amount_subtotal = fields.Monetary(
        string='Subtotal',
        currency_field='currency_id'
    )

    patial_payment = fields.Float(
        string='Total Partial Payment'
    )

    auto_payment = fields.Float(
        string='Auto Payment'
    )

    left_payment = fields.Float(
        string='Left Payment',
        compute='_compute_amount_left_to_payment',
        store=True
    )

    line_paid_status = fields.Boolean(
        string='Line Fully Paid',
        compute='_compute_paid_status',
        store=True
    )

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        related='contract_id.partner_id'
    )

    @api.depends('auto_payment', 'amount_due')
    def _compute_paid_status(self):
        for obj in self:
            obj.line_paid_status = obj.auto_payment >= obj.amount_due

    def action_generate_partial_payment(self, amount):
        if self.contract_id.state != 'confirm':
            raise UserError(
                _(
                    'Please make sure you confirm the record first before generating payment.'
                )
            )
        payment_method_id = self.env['account.payment.method'].search(
            [('payment_type', '=', 'inbound')], limit=1
        )
        payload = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.contract_id.partner_id.id,
            'payment_method_id': payment_method_id.id,
            'amount': amount,
            'journal_id': self.contract_id.journal_id.id,
            'payment_date': fields.Date.today(),
            'contract_id': self.contract_id.id,
            'contract_line_id': self.id,
        }
        if not self.payment_id:
            payment = self.env['account.payment'].create(payload)
            self.write({'payment_id': payment.id, 'state': 'partial'})
            if amount >= self.amount_subtotal:
                self.payment_id.post()
                self.write({'state': 'paid', 'patial_payment': amount})
            else:
                amount = self.patial_payment + amount
                self.payment_id.write({'amount': amount})
                self.write({'patial_payment': amount, 'state': 'partial'})
            self.auto_payment = amount
        else:
            amount = self.patial_payment + amount
            self.auto_payment = amount
            self.payment_id.write({'amount': amount})
            self.write({'patial_payment': amount, 'state': 'partial'})
            if amount >= self.amount_subtotal:
                self.payment_id.post()
                self.write({'state': 'paid'})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.onchange('amount_due', 'charge_amount')
    def _onchange_amount_subtotal(self):
        for rec in self:
            if rec.amount_due < rec.auto_payment:
                raise UserError(
                    _('Subtotal amount cannot be less than done payment amount')
                )
            rec.amount_subtotal = rec.amount_due + rec.charge_amount

    @api.onchange('charge_amount')
    def _onchange_charge_amount(self):
        """Recalcular el subtotal cuando cambie el cargo por mora."""
        for record in self:
            if record.charge_amount:
                record.amount_subtotal = record.amount_due + record.charge_amount

    @api.depends(
        'amount_due',
        'charge_amount',
        'payment_id',
        'move_id',
        'patial_payment',
        'auto_payment',
    )
    def _compute_amount_left_to_payment(self):
        for rec in self:
            rec.left_payment = (rec.amount_due + rec.charge_amount) - rec.auto_payment

    @api.depends('contract_id.name', 'sequence')
    def _compute_name(self):
        for record in self:
            record.name = '%s-%d' % (record.contract_id.name, record.sequence)

    @api.model
    def action_generate_payment(self):
        if self.contract_id.state != 'confirm':
            raise UserError(
                _(
                    'Please make sure you confirm the record first before generating payment.'
                )
            )
        payment_method_id = self.env['account.payment.method'].search(
            [('payment_type', '=', 'inbound')], limit=1
        )
        payload = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.contract_id.partner_id.id,
            'payment_method_id': payment_method_id.id,
            'amount': self.amount_due,
            'journal_id': self.contract_id.journal_id.id,
            'payment_date': fields.Date.today(),
            'contract_id': self.contract_id.id,
            'contract_line_id': self.id,
        }
        self.auto_payment += self.amount_due
        payment = self.env['account.payment'].create(payload)
        self.write({'payment_id': payment.id, 'state': 'paid'})
        payment.post()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_generate_extra_invoice(self):
        if self.contract_id.state == 'cancelled':
            raise UserError(
                _(
                    'It is not possible to add late fees when the document has already been cancelled.'
                )
            )
        """Este método abre el wizard de 'Aplicar Cargo por Mora'"""
        self.ensure_one()

        # Llamar a la acción para abrir el wizard
        return {
            'type': 'ir.actions.act_window',
            'name': 'Apply Late Fee',
            'res_model': 'wizard.apply.late.fee',
            'view_mode': 'form',
            'view_id': self.env.ref('condo.view_wizard_apply_late_fee_form').id,
            'target': 'new',
            'context': {
                'default_contract_line_id': self.id,
            }
        }
