#!/usr/bin/python3

import configparser
import click
import cachetclient
from cachetclient.v1 import enums
import sys
import os

@click.group()
@click.option('--debug/--no-debug', default=False, help="Enable verbose output")
def main(debug):
    """ zbx-to-cachet is a program to create/update/resolve incidents on Cachet server """
    global DEBUG
    DEBUG = debug
    if debug:
        click.echo('Debug mode is %s' % ('on'))
    load_config()

def load_config():
    # Load config file
    config = configparser.ConfigParser()
    config.read(os.path.join(sys.path[0],'config.ini'))
    # Read CACHET section, raise error if not found
    if not 'CACHET' in config.sections():
        click.secho("[!] Configuration file config.ini is missing or invalid")
        sys.exit(1)
    else:
        try:
            global endpoint
            endpoint = config['CACHET']['endpoint']
        except:
            click.secho("[!] Configuration file is missing Cachet 'endpoint' Config")
            sys.exit(1)
        try:
            global api_token
            api_token = config['CACHET']['api_token']
        except:
            click.secho("[!] Configuration file is missing Cachet 'api_token' Config")
            sys.exit(1)
    if DEBUG:
        click.secho("[D] Successfuly loaded confing from config.ini", fg='green')


@main.command(help='Create Cachet Incident')
@click.argument('component_id')
@click.argument('severity')
@click.argument('subcomponent_name')
def create(component_id, severity, subcomponent_name):
    component = CachetComponent(component_id)
    component.create_incident(severity, subcomponent_name)
    

@main.command(help='Update Cachet Incident')
@click.argument('component_id')
@click.argument('update_message')
def ack(component_id, update_message):
    component = CachetComponent(component_id)
    component.acknowledge_incident(update_message)


@main.command(help="Resolve Cachet Incident")
@click.argument('component_id')
def resolve(component_id):
    component = CachetComponent(component_id)
    component.resolve_incident()

class CachetComponent(object):
    def __init__(self, component_id):
        self.endpoint = endpoint
        self.api_token = api_token
        self.component_id = component_id
        self.client = cachetclient.Client(self.endpoint, self.api_token)
        if DEBUG:
            click.secho("[D] Initializing Cachet Component with ID %s" % component_id, fg='green')
        if not self.ping():
            click.secho("[!] Unable to connect to Cachet server at %s" % endpoint, fg='red')
        self.latest_incident = self._get_most_recent_incident()

    def ping(self):
        if self.client.ping():
            if DEBUG:
                click.secho("[D] Cachet is up and running", fg='green')
            return True
        else:
            return False

    def _get_most_recent_incident(self):
        listdates = []
        try: 
            incidents_list = [incident for incident in self.client.incidents.list() if incident.component_id == int(self.component_id) and incident.status != 4]
            for incident in incidents_list:
                listdates.append(incident.created_at)
            latest_incident_time = max(listdates)
            latest_incident= [incident for incident in incidents_list if incident.created_at == latest_incident_time]
            return latest_incident
        except:
            return []

    def create_incident(self, severity, subcomponent_name):
        # get component group
        component_group_id = self.client.components.get(component_id=self.component_id).group_id
        component_group_name = self.client.component_groups.get(group_id=component_group_id).name
        self.client.incidents.create(
            status=enums.INCIDENT_INVESTIGATING,
            component_id=self.component_id,
            component_status=severity,
            name = 'Incident affecting %s %s' % (component_group_name, subcomponent_name),
            message = '''
Our team is aware of an issue affecting **%s** component (`%s`) in **%s**. 
We are currently investigating the cause of the issue.

The status of the incident will be updated as soon as more information is available.
            ''' % (component_group_name, subcomponent_name, self.client.components.get(component_id=self.component_id).description)
        )

    def acknowledge_incident(self, update_message=''):
        if not len(update_message) > 0:
            update_message = "We have identified the issue and we are currently working on a fix"
        self.client.incident_updates.create(
            incident_id = self.latest_incident[0].id,
            status = 2,
            message = update_message
        )
    
    def resolve_incident(self):
        self.client.incident_updates.create(
            incident_id = self.latest_incident[0].id,
            status = 4,
            message = "The issue has been resolved"
        )
        self.client.components.update(
            component_id= self.component_id,
            status = enums.COMPONENT_STATUS_OPERATIONAL
        )

if __name__ == '__main__':
    main()

