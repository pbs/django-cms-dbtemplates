# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0001_initial'),
        ('dbtemplates', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PluginModelA',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin')),
                ('some_template', models.ForeignKey(blank=True, to='dbtemplates.Template', null=True)),
            ],
            options={
                'db_table': 'cmsplugin_pluginmodela',
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.CreateModel(
            name='PluginModelB',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin')),
                ('some_template_name', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'cmsplugin_pluginmodelb',
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.CreateModel(
            name='PluginModelC',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin')),
                ('templ_name', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'cmsplugin_pluginmodelc',
            },
            bases=('cms.cmsplugin',),
        ),
    ]
