# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import os
import sys
import logging
import openerp
import xlrd
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class ProductProductImportInventory(orm.Model):
    ''' Importation log element
    ''' 
    _inherit = 'product.product.import.inventory'

    # -------------
    # Button event:
    # -------------
    def action_import_product_from_csv(self, cr, uid, ids, context=None):
        ''' Import detail button
        '''
        # Pool used:
        move_pool = self.pool.get('stock.move')
        product_pool = self.pool.get('product.product')
        current_proxy = self.browse(cr, uid, ids, context=context)[0]

        filename = '/home/administrator/photo/xls/inventory' # TODO parametrize
        
        # ----------------
        # Read parameters:
        # ----------------
        # From import procedure:
        fullname = current_proxy.fullname
        max_line = current_proxy.max_line or 15000
        type_cl_id = current_proxy.cl_picking_type_id.id
        type_sl_id = current_proxy.sl_picking_type_id.id
        
        # Calculated:
        date = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # Log activity:
        if not fullname:
            raise osv.except_osv(
                _('Import error'), 
                _('Need a file name to import in path %s' % fullname),
                )
        _logger.info('Start import from path: %s' % filename)

        # ----------------
        # Header creation:        
        # ----------------
        header_data = {
            'partner_id': 1, # TODO
            'picking_type_id': type_cl_id,            
            'date': date,
            'min_date': date,
            'date_done': date,
            'origin': fullname,
            }        
            
        # Create object:
        cl_proxy = self.create(cr, uid, ids, header_data, context=context)
        data['picking_type_id'] = type_sl_id
        sl_proxy = self.create(cr, uid, ids, header_data, context=context)

        # ---------------------------------------------------------------------
        #                Open XLS document (first WS):
        # ---------------------------------------------------------------------
        error = note = ''

        # Read excel filename:
        try:
            filename = os.path.join(filename, fullname)
            wb = xlrd.open_workbook(filename)
            ws = wb.sheet_by_index(0)
        except:
            error = 'Error opening XLS file: %s' % (sys.exc_info(), )
            raise osv.except_osv(
                _('Open file error'), 
                _('Cannot found file: %s' % filename),
                )  

        # Loop on line:
        for i in range(0, max_line):
            try:
                row = ws.row(i) # generate error at end
            except:
                # Out of range error ends import:
                note += _('Import end at line: %s\n') % i
                break

            try:
                # Loop on colums (trace)
                try:
                    default_code = str(row[0].value).replace('.0', '')
                except:
                    default = ''
                    
                # Search product with code:
                if not default_code:
                    error += _('%s. No default code on file found\n') % i
                    continue # jump

                try:
                    product_qty = float(row[1].value)
                except:
                    product_qty = 0

                product_ids = product_pool.search(cr, uid, [
                    ('default_code', '=', default_code)], context=context)
                
                if not product_ids:
                    error += _(
                        '%s. Error code not found, code: %s\n') % (
                            i, default_code)
                    continue # jump
                
                elif len(product_ids) > 1:
                    error += _(
                        '%s. Warning more code (take first), code: %s\n') % (
                                i, default_code)
                                              
                product_proxy = product_pool.browse(
                    cr, uid, product_ids, context=context)[0]
                    
                # Update with stock:
                gap_qty = product_qty - product_proxy.mx_net_qty:
                
                if gap_qty >= 0:
                    document = 'SL'
                    picking = sl_proxy
                else:
                    document = 'CL'
                    picking = cl_proxy
                    gap_qty = -gap_qty # positive quantity        

                move_pool.create(cr, uid, {
                    'name': default_code,
                    #'date_planned': '2015-12-31',
                    'product_id': product_ids[0],
                    'picking_id': picking.id,
                    'product_uom_qty': gap_qty,
                    'date': date,
                    'date_expected': date,
                    'location_id': 
                        picking.picking_type_id.default_location_src_id.id,
                    'location_dest_id': 
                        picking.picking_type_id.default_location_dest_id.id,
                        
                    'price_unit': 1.0, # TODO for stock evaluation
                    'product_uom': product_proxy.uom_id.id
                    }, context=context)

                note += '%s. %s from %s to %s [%s %s]\n' % (
                    i, 
                    default_code, 
                    product_proxy.mx_net_qty,
                    product_qty,
                    document,
                    gap_qty,
                    )
            except:
                error += _('%s. Import error code: %s [%s]\n') % (
                    i, default_code, sys.exc_info())
                    
        self.write(cr, uid, log_id, {
            'error': error,
            'note': 'File: %s\n%s' % (
                filename, note),
            }, context=context)

        _logger.info('End import XLS purchase file: %s' % (
            purchase_proxy.filename))
        return True

    _columns = {
        'fullname': fields.char(
            'File name', size=80, required=True), 
        'max_line': fields.integer('Max line'), 
        'cl_picking_type_id': fields.many2one(
            'stock.picking.type', 'Type CL', required=True),
        'sl_picking_type_id': fields.many2one(
            'stock.picking.type', 'Type SL', required=True),
        'inventory_cl_id': fields.many2one(
            'stock.picking', 'Inventory CL', ondelete='set null'),
        'inventory_sl_id': fields.many2one(
            'stock.picking', 'Inventory SL', ondelete='set null'),
        'error': fields.text('Error'),
        'note': fields.text('Note'),
        }
        
    _defaults = {
        'max_line': lambda *x: 15000,
        }
     
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
