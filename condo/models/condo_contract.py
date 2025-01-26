# © 2024 Daniel Eduardo Diaz Mateo <daniel.diaz@isjo-technology.com>

import time
from decimal import Decimal, getcontext

from odoo import api, fields, models, _
from datetime import datetime, date
from datetime import date as dt_date
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import logging
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare

_logger = logging.getLogger(__name__)

# Ajuste de precisión decimal
getcontext().prec = 6

class CondoContract(models.Model):
    _name = 'condo.contract'
    _description = 'Condo Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    @api.depends('initial_total')
    def _compute_initial_total(self):
        for rec in self:
            rec.amount = rec.initial_total

    @api.depends('inceptive_amount', 'separacion')
    def _compute_initial_complete(self):
        for rec in self:
            rec.initial_total = rec.inceptive_amount - rec.separacion

    @api.depends('partner_id')
    def _compute_project_name(self):
        for rec in self:
            rec.project_name = rec.partner_id.project_name if rec.partner_id else ''


    @api.model
    def _compute_out_invoices(self):
        for record in self:
            record.invoice_ids = record.env['account.move'].search([('move_type', '=', 'out_invoice'),('contract_id', '=', int(record.id))])

    @api.model
    def _compute_payment(self):
        for record in self:
            record.payment_ids = record.env['view.report.pay.invoice'].search([('id_contract_paid', '=', int(record.id))])

    @api.depends('state')
    def _compute_is_payment_interval_readonly(self):
        for record in self:
            record.is_payment_interval_readonly = record.state in ['confirm', 'done', 'cancelled']

    def _default_name_sequence(self):
        return self.env['ir.sequence'].next_by_code('seq.condo.contract')

    def _default_company(self):
        return self.env.company.id

    def _get_default_journal_id(self):
        journal_id = self.env['ir.config_parameter'].sudo().get_param('condo.default.journal')
        return int(journal_id) if journal_id else False

    @api.depends("invoice_ids")
    def _compute_invoice_id_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    @api.depends("payment_ids")
    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)

    # @api.onchange('inceptive_amount')
    # def _onchange_apartment_amount_total(self):
    #     for rec in self:
    #         _logger.info(f"Processing record ID: {rec.id}")
    #         _logger.info(f"Apartment Amount Total before change: {rec.aparment_amount_total}")
    # 
    #         if rec.aparment_amount_total is not None:
    #             rec.aparment_amount_total -= rec.inceptive_amount
    # 
    #         rec.diferent_invoice = rec.aparment_amount_total or 0.0
    #         _logger.info(f"Apartment Amount Total after change: {rec.aparment_amount_total}")

    name = fields.Char(
        copy=False,
        store=True,
        required=True,
        readonly=True,
        default=_default_name_sequence
    )
    
    aparment_amount_total = fields.Monetary(
        string='Monto Contrato',
        currency_field='currency_id',
        required=True,
        default=0.0
    )

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        required=True,
        string='Customer',
        states={'confirm': [('readonly', True)], 'done': [('readonly', True)], 'cancelled': [('readonly', True)]},
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=_default_company,
        states={'confirm': [('readonly', True)], 'done': [('readonly', True)], 'cancelled': [('readonly', True)]},
    )

    cuote_completed = fields.Boolean(
        string='Cuotas Completadas',
        default=False
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirmed'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        required=True,
        copy=False,
        default='draft',
    )

    apt_number = fields.Char(
        string='Apartment Number',
        required=True
    )

    project_name = fields.Char(
        string='Project Name',
        required=True,
        compute='_compute_project_name'
    )

    line_ids = fields.One2many(
        comodel_name='condo.contract.line',
        inverse_name='contract_id',
        copy=False,
    )

    period = fields.Integer(
        string='Payment Period',
        required=True,
        default=12,
        help='Number of periods that the loan will last',
    )

    start_date = fields.Date(
        help='Start of the moves',
        copy=False,
        required=True,
        default=fields.Date.today(),
    )

    diferent_invoice = fields.Monetary(
        string='Diferent Invoice',
        currency_field='currency_id',
        default=0.0,
        help='This amount reflects the difference to be paid by the bank and the completeness of the invoice.',
        required=True
    )

    applied_cuote_atomatic = fields.Boolean(
        string='Apply quotas automatically',
        default=False
    )

    automatic_cuote = fields.Float(
        default=0.0,
        string='Percentage rate, for automatic calculation',
        help='We will save this field in the system to automate late payments in the system.',
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        compute='_compute_initial_total',
    )

    initial_total = fields.Monetary(
        string='Pendiente del Inicial',
        currency_field='currency_id',
        readonly=True,
        store=True,
        compute='_compute_initial_complete'
    )

    inceptive_amount = fields.Monetary(
        string='Inceptive Amount',
        currency_field='currency_id',
        required=True
    )

    separacion = fields.Monetary(
        string='Separacion',
        currency_field='currency_id',
        required=True
    )

    payment_interval = fields.Integer(
        string='Payment Interval',
        required=True,
        default=1
    )

    invoice_ids = fields.One2many(
        comodel_name='account.move',
        inverse_name='contract_id',
        string='Invoice',
        copy=False,
        compute='_compute_out_invoices'
    )

    payment_ids = fields.One2many(
        comodel_name='view.report.pay.invoice',
        inverse_name='id_contract_paid',
        string='Payment',
        copy=False,
        compute='_compute_payment'
    )

    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        required=True,
        default=_get_default_journal_id,
    )

    invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_invoice_id_count'
    )

    payment_count = fields.Integer(
        string='Payment Count',
        compute='_compute_payment_count'
    )

    amount_paid = fields.Monetary(
        string='Amount Paid'
    )
    
    amount_total = fields.Monetary(
        compute='_compute_amount_due_total',
        string='Amount Total',
    )

    amount_due_total = fields.Monetary(
        string='Total Due Amount',
    )

    done_fully_payment = fields.Boolean(
        string='Done Fully', 
        copy=False, 
        compute='_compute_done_fully_payment'
    )
    amount_charge = fields.Monetary(
        compute='_compute_amount_due_total',
        string='Charge Amount',
        store=True
    )

    history_ids = fields.One2many(
        'condo.charge.history',
        'contract_id',
        string='History'
    )

    def button_cancel(self):
        if all([line.state == 'paid' for line in self.line_ids]) and self.amount_due_total <= 0.0:
            raise UserError(
                _(
                    'This process once finished cannot be canceled...'
                )
            )
        if not all([line.state == 'paid' for line in self.line_ids]):
            for line in self.line_ids:
                if line.state == 'open':
                    line.state = 'cancel'
            for invoice in self.invoice_ids:
                invoice.button_cancel()
        self.state = "cancelled"

    @api.depends('line_ids.charge_amount', 'line_ids.amount_due', 'line_ids.patial_payment')
    def _compute_amount_due_total(self):
        """Recalcular los totales en el contrato basado en los pagos registrados."""
        for record in self:
            # Inicializar los montos
            amount_paid = 0.0
            amount_total = 0.0
            amount_charge = 0.0
            diferent_invoice = record.diferent_invoice

            # Buscar todos los pagos relacionados con este contrato
            payments = self.env['account.payment'].search([('contract_id', '=', record.id)])

            # Sumar los montos pagados desde los pagos en account.payment
            for payment in payments:
                amount_paid += payment.amount

            # Calcular el total adeudado y los cargos basados en las líneas del contrato
            for line in record.line_ids:
                amount_total += line.amount_due
                amount_charge += line.charge_amount

            # Actualizar los campos con los nuevos valores
            record.amount_paid = amount_paid
            record.amount_total = amount_total + amount_charge
            record.amount_charge = amount_charge

            # Calcular el monto pendiente
            record.amount_due_total = diferent_invoice + amount_total + amount_charge - amount_paid

    def _apply_payment(self, monto):
        for record in self:
            if monto > 0.0:
                # Actualizar el amount_due_total restando el monto pagado
                if monto <= record.amount_due_total:
                    record.amount_due_total -= monto
                else:
                    record.amount_due_total = 0.0

                # Sumar el monto al amount_paid
                record.amount_paid += monto

    def _compute_done_fully_payment(self):
        for obj in self:
            obj.done_fully_payment = obj.amount_paid >= obj.amount_total

    @api.depends('initial_total')
    def _compute_initial_total(self):
        for rec in self:
            rec.amount = rec.initial_total

    def action_confirm(self):
        if not self.line_ids:
            raise UserError(_("Payment schedule line cannot be empty"))
        product = self.env.ref("condo.contract_product")
        accounts = product.product_tmpl_id._get_product_accounts()
        payload = {
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": self.start_date,
            "invoice_date_due": self._get_due_date(),
            "company_id": self.company_id.id,
            "contract_id": self.id,
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "name": f"Contrato: {self.name} - {'APT.No. ' + self.apt_number if self.apt_number else ''} [{self.partner_id.project_name}] {self.partner_id.name}",
                        "price_unit": self.amount_due_total,
                        "account_id": accounts.get("income").id,
                    },
                )
            ],
        }
        inv = self.env["account.move"].create(payload)
        # inv.action_post()
        self.write({"state": "confirm"})

    def _get_due_date(self):
        return max(self.line_ids.sorted(key=lambda r: r.sequence, reverse=True)).date

    def action_show_invoices(self):
        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [('id', 'in', self.invoice_ids.ids)],
        }

    def action_show_payments(self):
        return {
            'name': 'Payments',
            'type': 'ir.actions.act_window',
            'res_model': 'view.report.pay.invoice',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': [['id', 'in', self.payment_ids.ids]],
        }

    def _action_calulate_amount(self, principal, period):
        if period:
            return Decimal(principal) / Decimal(period)
        else:
            raise UserError(period)

    def action_compute_payment_schedule(self):
        """
        Computes the payment schedule based on the start date
        :return: Amount to be paid on the annuity
        """
        if not self.start_date:
            raise UserError(_("The contract must have a start date to compute the payment schedule."))

        # Usar la fecha de inicio del contrato
        datePaid = self.start_date
        delta = relativedelta(months=self.payment_interval)  # Intervalo de meses entre pagos
        amount = self.initial_total
        period = self.period

        # Limpiar las líneas anteriores
        for amortizacion in self:
            amortizacion.line_ids.unlink()

        # Calcular el monto de cada cuota
        p_amount = self._action_calulate_amount(amount, period)
        principal_amount = float(format(p_amount, ".2f"))
        decimal_error = amount - float(principal_amount) * period
        decimal_error = float(format(decimal_error, ".2f"))
        separacion = float(format(self.separacion, ".2f"))

        # Inicializar la fecha de separación si aplica
        separacion_date = self.start_date

        # Recorrer el período y generar las líneas de pago
        datePaid += delta  # Incrementar la fecha de pago para la primera cuota
        for i in range(2, period + 2):  # Comenzar desde la segunda cuota
            payload = {
                "contract_id": self.id,
                "sequence": i - 1,
                "date": datePaid,
                "amount_due": principal_amount + decimal_error if i == period + 1 else principal_amount,
                "left_payment": principal_amount + decimal_error if i == period + 1 else principal_amount,
                "amount_subtotal": principal_amount + decimal_error if i == period + 1 else principal_amount,
                "partner_id": self.partner_id.id,
            }
            self.env["condo.contract.line"].create(payload)
            datePaid += delta  # Avanzar a la siguiente fecha de pago

        # Ajustar el primer pago si hay errores de redondeo
        sumation = float(format(sum([a.amount_due for a in self.line_ids]), ".2f"))
        if sumation < amount:
            error = float(format(amount - sumation, ".2f"))
            self.line_ids.filtered(lambda r: r.sequence == 1).write({
                "amount_due": float(format(self.line_ids.filtered(lambda r: r.sequence == 1).amount_due + error, ".2f"))
            })
        elif sumation > amount:
            error = float(format(sumation - amount, ".2f"))
            self.line_ids.filtered(lambda r: r.sequence == 1).write({
                "amount_due": float(format(self.line_ids.filtered(lambda r: r.sequence == 1).amount_due - error, ".2f"))
            })

        # Crear la línea de separación si existe
        if self.separacion:
            separacion_payload = {
                "contract_id": self.id,
                "sequence": 0,
                "date": separacion_date,
                "amount_due": separacion,
                "left_payment": separacion,
                "amount_subtotal": separacion,
                "partner_id": self.partner_id.id,
            }
            self.env["condo.contract.line"].create(separacion_payload)
        else:
            raise UserError(_("The payment schedule cannot be computed because the contract amount is zero."))

    _sql_constraints = [
        ("name_uniq", "unique(name, company_id)", "Contract name must be unique"),
    ]

    @api.model
    def create(self, vals):
        contract = super(CondoContract, self).create(vals)
        return contract

    def action_done(self):
        line_ids = self.line_ids.filtered(lambda r: r.charge_amount == False)
        if not all([line.state == 'paid' for line in line_ids]):
            raise UserError(
                _(
                    'This action cannot be performed until all payment has been registered.'
                )
            )
        if self.state != 'confirm':
            raise UserError(
                _(
                    'Please make sure you confirm the record first before generating payment.'
                )
            )

        if not self.invoice_ids.filtered(lambda l: l.journal_id.id == int(self.env['ir.config_parameter'].sudo().get_param('condo.default.journal'))):
            raise UserError(
                _(
                    'Please make sure that there is an invoice associated with the document to proceed to process payments.'
                )
            )
        for inv in self.invoice_ids.filtered(lambda l: l.journal_id.id == int(self.env['ir.config_parameter'].sudo().get_param('condo.default.journal'))):
            if inv.state == 'posted':
                continue
            inv.action_post()
        self.write({'state': 'done'})
        return {'type': 'ir.actions.act_window_close'}

    def action_draft_contract(self):
        #         print "==============action_reset============="
        if not all([line.state in ('partial','paid') for line in self.line_ids]):
            raise UserError(
                _(
                    'This action cannot be performed because there must be no payments made or partially made.'
                )
            )
        for line in self.line_ids:
            line.unlink()
        self.cuote_completed = False
        self.state = 'draft'

    def _get_report_filename(self):
        return self.name + '_Condo_' + self.partner_id.name + '.pdf'

    def ir_cron_condo_email_remainder(self, days):
        delta = relativedelta(days=days)
        date = fields.Date.context_today(self) + delta
        # domain = [("date", ">=", dt_date(2024, 8, 1)), ("date", "<=", dt_date(2024, 8, 30))]
        domain = [("date", ">=", fields.Date.context_today(self)), ("date", "<=", date)]
        contracts = self.env["condo.contract.line"].search(domain).mapped("contract_id")
        template = self.env.ref("condo.email_template_condo_contract")
        for contract in contracts:
            due_line = contract.line_ids.filtered(lambda r: r.state == "open")
            if due_line:
                due_line = due_line[0]
                ctx = {"amount_due": due_line.amount_due, "payment_date": due_line.date}
                template.with_context(ctx).send_mail(contract.id, force_send=True)

    def action_compute_charge_for_late_payment(self):
        today = fields.Date.context_today(self)
        first_day_next_month = today.replace(day=1) + relativedelta(months=1)

        # Cuotas fuera del mes actual que aún estén abiertas
        domain = [
            ("date", "<", first_day_next_month),  # Cuotas antes del próximo mes
            ("state", "=", "open")  # Solo cuotas que aún están abiertas (ajusta según tu estado)
        ]

        # Aquí podrías hacer la búsqueda de las cuotas
        cuotas_abiertas_fuera_mes_actual = self.env['condo.contract.line'].search(domain)
        if not cuotas_abiertas_fuera_mes_actual:
            return # Si no hay cuotas, termina la función aquí
        for cuota in cuotas_abiertas_fuera_mes_actual:
            # Buscar la factura de mora relacionada con la línea del contrato
            mora_invoice = self.env['account.move'].search(
                [('contract_line_id', '=', cuota.id), ('move_type', '=', 'out_invoice'),
                 ('journal_id.is_active', '=', True), ('payment_state', '!=', 'paid')], limit=1)
            if cuota.contract_id.applied_cuote_atomatic and cuota.contract_id.automatic_cuote > 0.0:
                porcent_mora = cuota.contract_id.automatic_cuote / 100

                mora_payment_amount = cuota.left_payment * porcent_mora
                if not mora_invoice:
                #     mora_payment_amount = min(auto_payment, mora_invoice.amount_residual)
                    if mora_payment_amount > 0:
                        # crear factura cargo a mora
                        product = self.env.ref("condo.contract_product_charge")
                        accounts = product.product_tmpl_id._get_product_accounts()
                        payload = {
                            "move_type": "out_invoice",
                            "partner_id": cuota.contract_id.partner_id.id,
                            "invoice_date": fields.Date.today(),  # self.start_date,
                            "journal_id": self.env['account.journal'].search([('is_active', '=', True)], limit=1).id,
                            "invoice_date_due": fields.Date.today() + timedelta(days=30),
                            # Calcular la fecha de vencimiento (por ejemplo, 30 días después de la fecha actual)
                            "company_id": cuota.contract_id.company_id.id,
                            "contract_id": cuota.contract_id.id,
                            "contract_line_id": cuota.id,
                            "invoice_line_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "product_id": product.id,
                                        "name": f"Cargo por mora: {mora_payment_amount} - Contrato: {cuota.name} / [{cuota.contract_id.project_name}] {cuota.contract_id.partner_id.name}",
                                        "price_unit": mora_payment_amount,
                                        "account_id": accounts.get("income").id,
                                    },
                                )
                            ],
                        }
                        inv = self.env["account.move"].create(payload)
                        inv.action_post()

                        cuota.write({
                            'charge_amount': cuota.charge_amount + mora_payment_amount, # Sumar mora pagada (si existe) más el nuevo cargo
                            'late_payment': mora_payment_amount  # Mantener o actualizar el valor de mora no pagada
                        })


