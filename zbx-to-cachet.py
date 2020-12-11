import configparser
import click
import cachetclient
from cachetclient.v1 import enums
import sys
from jinja2 import Template

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
    # Load config file, raise exception if file not found
    config = configparser.ConfigParser()
    config.read('config.ini')
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
@click.argument('subcomponent_group')
def create(component_id, severity, subcomponent_name, subcomponent_group):
    component = CachetComponent(component_id)
    component.create_incident(severity, subcomponent_name, subcomponent_group)
    

@main.command(help='Update Cachet Incident')
@click.argument('component_id')
def ack(component_id):
    component = CachetComponent(component_id)
    component.acknowledge_incident()


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

    def ping(self):
        if self.client.ping():
            if DEBUG:
                click.secho("[D] Cachet is up and running", fg='green')
            return True
        else:
            return False

    def _render_template(self, subcomponent_group, subcomponent_name, component_name, type='create'):
        create_template = Template('''
Our team is aware of an issue affecting one of our **{{ subcomponent_group }}**`{{ subcomponent_name }}` in **{{ component_name }}**. 
We are currently investigating the cause of the issue.

We will have an update as soon as more information is available.
        ''')

        if type=='create':
            return create_template.render(subcomponent_group=subcomponent_group,subcomponent_name=subcomponent_name,component_name=component_name)

    def _get_active_incidents_for_component(self):
        return [incident for incident in self.client.incidents.list() if incident.component_id == int(self.component_id) and incident.status != 4]

    def _filter_most_recent_incident(self, incidents_list):
        listdates = []
        for incident in incidents_list:
            listdates.append(incident.created_at)
        latest_incident_time = max(listdates)
        latest_incident= [incident for incident in incidents_list if incident.created_at == latest_incident_time]
        return latest_incident

    def create_incident(self, severity, subcomponent_group, subcomponent_name):
        self.client.incidents.create(
            # name="Something blew up! on %s" % subcomponent_name,
            # message="We are looking into it",
            status=enums.INCIDENT_INVESTIGATING,
            component_id=self.component_id,
            component_status=severity,
            name = 'Incident affecting %s %s' % (subcomponent_group, subcomponent_name),
            message = self._render_template(subcomponent_group, subcomponent_name, self.client.components.get(component_id=self.component_id).description, type='create')
        )

    def acknowledge_incident(self):
        component_incidents = self._get_active_incidents_for_component()
        latest_incident = self._filter_most_recent_incident(component_incidents)
        self.client.incident_updates.create(
            incident_id = latest_incident[0].id,
            status = 2,
            message = "We have identified the issue and we are currently working on a fix"
        )
    
    def resolve_incident(self):
        component_incidents = self._get_active_incidents_for_component()
        latest_incident = self._filter_most_recent_incident(component_incidents)
        self.client.incident_updates.create(
            incident_id = latest_incident[0].id,
            status = 4,
            message = "The issue has been resolved"
        )
        self.client.components.update(
            component_id= self.component_id,
            status = enums.COMPONENT_STATUS_OPERATIONAL
        )

if __name__ == '__main__':
    main()

