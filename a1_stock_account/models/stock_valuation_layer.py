# -*- coding: utf-8 -*-
from odoo import _, fields, models, SUPERUSER_ID
from odoo.tools import config
import configparser

def get_odoo_conf_path():
    conf_file_path = config.config_file or config.rcfile
    return conf_file_path

def update_odoo_config(file_path, section, option, value):
    config = configparser.ConfigParser()
    config.read(file_path)
    if not config.has_section(section):
        config.add_section(section)

    if config.has_option(section, option):
        existing_value = config.get(section, option)
        if value not in existing_value.split(","):
            new_value = existing_value + "," + value
        else:
            new_value = existing_value
    else:
        new_value = value
    config.set(section, option, new_value)
    with open(file_path, 'w') as configfile:
        config.write(configfile)


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _validate_accounting_entries(self):
        context = self.env.context
        if self:
            job_name = 'wh_' + str(self[0].company_id.id) + '_job_channel'
            if not context.get('job_uuid', False):
                model_job_channel = self.env['queue.job.channel'].sudo()
                job_channel = model_job_channel.search([('name', '=', job_name)], limit=1)
                channel_root = self.env.ref('queue_job.channel_root')
                if not job_channel:
                    model_job_channel.create({
                        'name': job_name,
                        'parent_id': channel_root.id
                    })
                    file_path = get_odoo_conf_path()
                    update_odoo_config(file_path=file_path, section='queue_job', option='channels', value=job_name + ':1')
                return super(StockValuationLayer, self).with_user(SUPERUSER_ID).with_delay(channel=job_name)._validate_accounting_entries()
            else:
                return super(StockValuationLayer, self)._validate_accounting_entries()
        return super(StockValuationLayer, self)._validate_accounting_entries()
