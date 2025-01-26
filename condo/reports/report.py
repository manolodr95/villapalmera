# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta, date, datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError, UserError
import calendar
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class ReceiptFee(models.AbstractModel):
    _name = 'report.condo.report_ticket_fee'
    _description = 'Ticket Fee'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not docids:
            _logger.error("No se proporcionaron docids.")
            raise ValueError("No se proporcionaron identificadores de cuotas.")

        payment = self.env['account.payment'].browse(docids)

        if not payment:
            _logger.error(f"No se encontraron cuotas para los docids proporcionados: {docids}")
            raise ValueError("No se encontraron cuotas con los identificadores proporcionados.")

        return {
            'docs': payment,
            'company': self.env.company,
            'data': data,
        }


class ChargeReport(models.AbstractModel):
    _name = "report.condo.report_condo_charge"
    _description = "Report Condo Charge"

    @api.model
    def _get_report_values(self, docids, data=None):
        start_date = data["form"]["start_date"]
        end_date = data["form"]["end_date"]
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        start_year = start_date.strftime("%Y")
        end_year = end_date.strftime("%Y")
        start_month = start_date.strftime("%m")
        end_month = end_date.strftime("%m")
        final_dict = {}
        months = [
            datetime.strptime("%2.2d-%2.2d" % (y, m), "%Y-%m").strftime("%B-%Y")
            for y in range(start_date.year, end_date.year + 1)
            for m in range(
                start_date.month if y == start_date.year else 1,
                end_date.month + 1 if y == end_date.year else 13,
            )
        ]

        contract_date_range = {}
        if months:
            contract_start_date = start_date
            contract_end_date = end_date
            for m in months:

                if months.index(m) == 0 and len(months) == 1:
                    contract_start_date = start_date
                    contract_end_date = end_date
                    contract_date_range.update({contract_start_date: contract_end_date})
                else:
                    start_year = contract_start_date.strftime("%Y")
                    start_month = contract_start_date.strftime("%m")
                    year, month = int(start_year), int(start_month)
                    end_date_of_month = calendar.monthrange(year, month)[1]
                    contract_end_date = datetime(year, month, end_date_of_month)
                    contract_end_date = contract_end_date.date()
                    if end_date < contract_end_date:
                        contract_end_date = end_date
                    contract_date_range.update({contract_start_date: contract_end_date})
                    contract_start_date = contract_start_date + relativedelta(months=1)
                    contract_start_date = contract_start_date.replace(day=1)
        contract_line_count = 0
        contract_lines = {}
        contract_line_ids = self.env["condo.contract.line"].search([])
        for contract_date in contract_date_range:
            range_start_date = contract_date
            range_end_date = contract_date_range.get(contract_date)
            domain = [
                ("date", ">=", range_start_date),
                ("date", "<=", range_end_date),
                ("contract_state", "in", ("draft", "confirm")),
                ("left_payment", ">", 0),
            ]
            contract_line_ids = self.env["condo.contract.line"].search(domain)
            contract_lines.update({months[contract_line_count]: contract_line_ids})
            contract_line_count += 1

        return {
            "months": months,
            "contract_lines": contract_lines,
            "start_date": start_date,
            "end_date": end_date,
        }
