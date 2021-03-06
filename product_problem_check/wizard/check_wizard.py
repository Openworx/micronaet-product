# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################


import os
import sys
import logging
import openerp
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)


class ModuleWizard(orm.TransientModel):
    ''' Wizard for check product code and bom presence
    '''
    _name = 'product.product.check.bom.wizard'

    # --------
    # Utility:
    # --------
    def _get_product_list(self, cr, uid, mode, context=None):
        ''' Check data depend on mode
        '''
        product_pool = self.pool.get('product.product')        
        if mode == 'code':    
            return (
                product_pool.check_product_default_code_presence(
                    cr, uid, context=context),                
                _('Result for no code check'),
                )
        elif mode == 'bom':                    
            return (
                product_pool.check_product_bom_presence(
                    cr, uid, with_report=False, context=context),
                _('Result for BOM check'),
                )
        elif mode == 'multi':
            return (
                product_pool.check_product_double_code_presence(
                    cr, uid, context=context),
                _('Result for multi code check'),
                ) 
        else:
            raise osv.except_osv(_('Error'), _('Mode error'))
        
    # --------------------
    # Wizard button event:
    # --------------------    
    def action_print_report(self, cr, uid, mode, context=None):
        ''' Print report for bom
        '''
        datas = {}
        report_name = 'product_check_bom_report'
        
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
            }
        
    def action_check_product_mode(self, cr, uid, ids, context=None):
        ''' Event for button done
        '''
        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]
        (product_ids, message) = self._get_product_list(
            cr, uid, wiz_proxy.mode, context=context)

        model_pool = self.pool.get('ir.model.data')
        tree_view_id = model_pool.get_object_reference(
            cr, uid,
            'product_problem_check', 
            'view_product_product_check_tree')[1]

        return {
            'type': 'ir.actions.act_window',
            'name': message,
            'view_type': 'form',
            'view_mode': 'tree,form',
            #'res_id': 1,
            'res_model': 'product.product',
            'view_id': tree_view_id,
            'views': [(tree_view_id, 'tree'), (False, 'form')],
            'domain': [('id', 'in', product_ids)],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }

    _columns = {
        'mode': fields.selection([
            ('code', 'Default code not present'),
            ('bom', 'No BOM present for production'),
            ('multi', 'Multicode present for product'),
            ], 'Check mode', required=True),
        'note': fields.text('Comment'),
        }
        
    _defaults = {
        'note': lambda *x: '''
            Check some problems in product like:<br/>
            <b>BOM</b> for production,<br>
            <b>default code</b> presence and
            <b>double code</b> elements<br/>
            In all product for sale and production purposes.
            ''',
        'mode': lambda *x: 'code',
        }    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


