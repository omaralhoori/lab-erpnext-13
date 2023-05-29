# Copyright (c) 2015, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import absolute_import, print_function, unicode_literals

import click
import frappe
from frappe.commands import get_site, pass_context


def call_command(cmd, context):
	return click.Context(cmd, obj=context).forward(cmd)

@click.command('make-demo')
@click.option('--site', help='site name')
@click.option('--domain', default='Manufacturing')
@click.option('--days', default=100,
	help='Run the demo for so many days. Default 100')
@click.option('--resume', default=False, is_flag=True,
	help='Continue running the demo for given days')
@click.option('--reinstall', default=False, is_flag=True,
	help='Reinstall site before demo')
@pass_context
def make_demo(context, site, domain='Manufacturing', days=100,
	resume=False, reinstall=False):
	"Reinstall site and setup demo"
	from frappe.commands.site import _reinstall
	from frappe.installer import install_app

	site = get_site(context)

	if resume:
		with frappe.init_site(site):
			frappe.connect()
			from erpnext.demo import demo
			demo.simulate(days=days)
	else:
		if reinstall:
			_reinstall(site, yes=True)
		with frappe.init_site(site=site):
			frappe.connect()
			if not 'erpnext' in frappe.get_installed_apps():
				install_app('erpnext')

			# import needs site
			from erpnext.demo import demo
			demo.make(domain, days)


@click.command("start-infinty-results")
@click.option("--ip", default="10.123.4.150")
@click.option("--port", default=9090)
@click.option("--back", is_flag=True, default=True)
@pass_context
def start_infinty_results(
	context, ip="10.123.4.150",port=9090, back=True
):
	"Start Test Command"
	from erpnext.healthcare.socket_communication import start_infinty_listener
	print(f"Starting Infinty results server on {ip}:{port}")
	start_infinty_listener(ip, int(port))


@click.command("start-infinty-orders")
@click.option("--ip", default="10.123.4.12")
@click.option("--port", default=9091)
@click.option("--local-ip", "local_ip", default="127.0.0.1")
@click.option("--local-port","local_port", default=9990)
@click.option("--back", is_flag=True, default=True)
@pass_context
def start_infinty_orders(
	context, ip="10.123.4.12",port=9091,local_ip="127.0.0.1", local_port=9990, back=True
):
	"Start Test Command"
	from erpnext.healthcare.socket_communication import start_infinty_order_listener
	print(f"Starting Infinty order client on {ip}:{port}")
	start_infinty_order_listener(ip, int(port), local_ip, int(local_port))


@click.command("start-sysmex-results")
@click.option("--ip", default="10.123.4.150")
@click.option("--port", default=9094)
@click.option("--back", is_flag=True, default=True)
@pass_context
def start_sysmex_results(
	context, ip="10.123.4.150",port=9094, back=True
):
	"Start Test Command"
	from erpnext.healthcare.socket_communication import start_sysmex_listener
	print(f"Starting Infinty results server on {ip}:{port}")
	start_sysmex_listener(ip, int(port))



@click.command("start-sysmex-xp-results")
@click.option("--ip", default="10.123.4.150")
@click.option("--port", default=9095)
@click.option("--back", is_flag=True, default=True)
@pass_context
def start_sysmex_xp_results(
	context, ip="10.123.4.150",port=9095, back=True
):
	"Start Test Command"
	from erpnext.healthcare.socket_communication import start_sysmex_xp_listener
	print(f"Starting Infinty results server on {ip}:{port}")
	start_sysmex_xp_listener(ip, int(port))



@click.command("start-lision-results")
@click.option("--ip", default="10.123.4.150")
@click.option("--port", default=9096)
@click.option("--back", is_flag=True, default=True)
@pass_context
def start_lision_results(
	context, ip="10.123.4.150",port=9096, back=True
):
	"Start Test Command"
	from erpnext.healthcare.socket_communication import start_lision_listener
	print(f"Starting Lision server on {ip}:{port}")
	start_lision_listener(ip, int(port))

@click.command("start-rubycd-results")
@click.option("--ip", default="10.123.4.150")
@click.option("--port", default=9097)
@click.option("--back", is_flag=True, default=True)
@pass_context
def start_rubycd_results(
	context, ip="10.123.4.150",port=9097, back=True
):
	"Start Test Command"
	from erpnext.healthcare.socket_communication import start_ruby_cd_listener
	print(f"Starting Ruby CD server on {ip}:{port}")
	start_ruby_cd_listener(ip, int(port))

@click.command("start-bioradd10-results")
@click.option("--ip", default="10.123.4.150")
@click.option("--port", default=9098)
@click.option("--back", is_flag=True, default=True)
@pass_context
def start_bioradd10_results(
	context, ip="10.123.4.150",port=9098, back=True
):
	"Start Test Command"
	from erpnext.healthcare.socket_communication import start_biorad_d10_listener
	print(f"Starting Lision server on {ip}:{port}")
	start_biorad_d10_listener(ip, int(port))


@click.command("start-results-service")
@pass_context
def start_results_service(
	context
):
	"Start Test Command"
	from erpnext.healthcare.result_service import results_service_process
	print(f"Starting Results Service")
	results_service_process()

commands = [
	make_demo, start_infinty_results, start_sysmex_results, start_infinty_orders, 
	start_sysmex_xp_results, start_lision_results,start_rubycd_results, start_results_service, start_bioradd10_results
]
