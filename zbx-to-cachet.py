import configparser
import click
import cachetclient
from cachetclient.v1 import enums
import sys

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
def create(component_id, severity, subcomponent_name):
    component = CachetComponent(component_id)
    component.create_incident(severity, subcomponent_name)
    pass

@main.command(help='Update Cachet Incident')
def update():
    pass

@main.command(help="Resolve Cachet Incident")
def resolve():
    pass

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

    def create_incident(self, severity, subcomponent_name):
        self.client.incidents.create(
            name="Something blew up! on %s" % subcomponent_name,
            message="We are looking into it",
            status=enums.INCIDENT_INVESTIGATING,
            component_id=self.component_id,
            component_status=severity,
        )


if __name__ == '__main__':
    main()

