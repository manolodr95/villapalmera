# -*- coding: utf-8 -*-
# Copyright 2024 Daniel Diaz (<http://www.isjo-technology.com/>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Condo',
    'summary': 'Condo Management',
    'description': '''Module for managing condominium fees, contracts, and related payments.''',
    'author': 'ISJO TECHNOLOGY, SRL',
    'website': 'http://www.isjo-technology.com',
    'category': 'Property Management',
    'version': '17.0.1.0.0',
    'depends': [
        'account',
        'web'
    ],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizards/condo_contract_line_wizard.xml',
        'wizards/mark_payment_views.xml',
        'views/condo_contract.xml',
        'views/account_move.xml',
        'views/account_payment.xml',
        'views/condo_contract_line_views.xml',
        'views/view_report_pay_invoice.xml',
        'wizards/condo_charge_report_views.xml',
        'wizards/wizard_late_fee.xml',
        'wizards/account_register_payment.xml',
        'data/sequence.xml',
        'data/product.xml',
        'data/account_journal.xml',
        'data/ir_cron.xml',
        'data/mail_template.xml',
        # 'reports/report.xml',
        'reports/paperformat.xml',
        'reports/menu_rep.xml',
        'reports/report_ticket_fee.xml',
        'reports/report_action.xml',
        'reports/report_condo_charge.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

