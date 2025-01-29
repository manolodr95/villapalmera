# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError

class ViewReportPayInvoice(models.Model):
    _name = 'view.report.pay.invoice'
    _description = 'Report Product on Invoices lines Statistics'
    _auto = False # es una vista virtual
    # _rec_name = 'move_name'
    _order = 'no_paid desc'

    # ==== Invoice fields ====

    id = fields.Integer(
        string='Id',
        readonly=True,
        store=True
    )

    no_paid = fields.Char(
        string='No. Pago',
        readonly=True,
        store=True,
        index=True
    )

    date_receipt = fields.Date(
        string='Fecha Recibo',
        readonly=True,
        store=True,
        index=True
    )

    total_paid = fields.Float(
        string='Total Pagado',
        readonly=True,
        store=True
    )

    comment = fields.Char(
        string='Memo',
        readonly=True,
        store=True,
        index=True
    )

    id_contract_paid = fields.Integer(
        string='Id Contract Paid',
        readonly=True,
        store=True
    )

    contract_name = fields.Char(
        string='Contrat Condo',
        readonly=True,
        store=True
    )

    _depends = {
        'account.move': [
            'name',
            'ref',
            'date'
        ],
        'condo.contract': [
            'name'
        ],
        'account.payment': [
            'contract_id',
            'amount'
        ],
    }

    def _get_payment_receipt_report_values(self):
        """ Get the extra values when rendering the Payment Receipt PDF report.

        :return: A dictionary:
            * display_invoices: Display the invoices table.
            * display_payment_method: Display the payment method value.
        """
        self.ensure_one()
        return {
            'display_invoices': True,
            'display_payment_method': True,
        }

    def action_print_report(self):
        # Impresión del ticket de cuota
        return self.env.ref('condo.action_fee_ticket').report_action(self)

    @property
    def _table_query(self):
        return '%s %s' % (self._select(), self._from()) # , self._where()

    @api.model
    def _select(self):
        return '''
                SELECT
                    move.id As id, 
                    move.name As no_paid,
                    ap.contract_id As id_contract_paid,
                    cc.name As contract_name, 
                    move.date As date_receipt, 
                    ap.amount As total_paid, 
                    ap.payment_method_id As payment_method,
                    move.payment_reference As referent, 
                    move.ref As comment, 
                    ap.is_reconciled As reconcile
            '''

    @api.model
    def _from(self):
        return '''
                FROM
                    account_payment ap
                INNER JOIN
                    account_move move ON ap.move_id = move.id
                INNER JOIN
                    condo_contract cc on ap.contract_id = cc.id and move.contract_id = cc.id
            '''

    @api.model
    def _where(self):
        return '''
                WHERE
                    aj.type = 'sale' AND line.display_type = 'product' AND move.state = 'posted'
                    AND line.product_id IS NOT NULL and pp.is_report_pay = true -- Excluir apuntes contables (líneas sin producto)
                    AND move.move_type != 'entry' -- AND move.ref = 'S00105-8'
                ORDER BY
                    move.id DESC
            '''
