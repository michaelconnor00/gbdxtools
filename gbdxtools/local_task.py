import StringIO
import os
import subprocess
import json
import time
import tarfile
from docker import Client

from gbdxtools.simpleworkflows import Task


class InvalidPortError(Exception):
    pass


class Path(object):
    def __init__(self, path, task):
        self.path = path
        self.parent = task


class Port(object):
    def __init__(self, name, port_type, description, required, value, task):
        self.name = name
        self.type = port_type
        self.description = description
        self.required = required
        if self.type == 'directory':
            self._value = Path(value, task)
        else:
            self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if self.type == 'directory':
            if isinstance(new_value, Path):
                self._value = new_value
            else:
                # String value
                self._value.path = new_value
            # TODO raise exception if not str or Path
        else:
            self._value = new_value


class LocalPortList(object):
    def __init__(self, ports, task):
        self.portnames = set([p['name'] for p in ports])
        for p in ports:
            self.__setattr__(
                p['name'],
                Port(
                    p['name'],
                    p['type'],
                    p.get('required'),
                    p.get('description'),
                    None,
                    task
                )
            )

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        out = ""
        for input_port_name in self.portnames:
            out += input_port_name + "\n"
        return out


class LocalInputs(LocalPortList):
    def __setattr__(self, key, value):
        if key == "task":
            object.__setattr__(self, key, value)
            return

        # special attributes for internal use
        if key in ['portnames']:
            object.__setattr__(self, key, value)
            return

        # special handling for setting port values
        if key in self.portnames and hasattr(self, key):

            port = self.__getattribute__(key)
            port.value = value
            return

        # default for initially setting up ports
        if key in self.portnames:
            object.__setattr__(self, key, value)
        else:
            raise AttributeError('Task has no input port named %s.' % key)


class LocalOutputs(LocalPortList):
    pass


class LocalTask(Task):

    def __init__(self, interface, task_type, **kwargs):
        super(LocalTask, self).__init__(interface, task_type, **kwargs)

        # Override Inputs and Outputs with new Port class
        self.inputs = LocalInputs(self.input_ports, self)
        self.outputs = LocalOutputs(self.output_ports, self)

        # Only support docker
        if len([x['type'] for x in self.definition['containerDescriptors'] if x['type'] != 'DOCKER']) > 0:
            raise ValueError("Local Tasks must be DOCKER type")

        self.task_type = task_type

        # Docker Image
        self.image = self.definition['containerDescriptors'][0]['properties']['image']

        # Store command override
        self.command = self.definition['containerDescriptors'][0].get('command', None)

        # Print more outputs for debugging
        self.verbose = kwargs.get('verbose', False)

        # Status
        self.status = None  # True means done, False means pending

    def __eq__(self, other):
        return self.name == other.name

    def __str__(self):
        return """
            status: %s
            reason: %s
        """ % (self.status['status'], self.status['reason'])

    @property
    def success(self):
        if self.status is None:
            # TODO, it is possible some tasks don't use the gbdx_interface
            # In those cases, this should return True.
            return False

        status = self.status.get('status', None)

        if status.lower() == 'success':
            return True
        else:
            return False

    @property
    def reason(self):
        if self.status is None:
            return 'No status.json Found'
        else:
            return self.status['reason']

    def execute(self, temp_output_dir):
        """
        Runs the task locally.
        Steps:
            - Iterate through inputs,
                - directory -> add to mounts
                - string -> add to env vars
            - Iterate through outputs,
                - directory ->
                    - if savedata
                        -> create output dir
                    - else
                        -> create temp dir
                    - add to mounts
            - Configure Docker container
            - Run Container
            - Print output
        """
        dkr = Client(timeout=3600)

        temp_output_dir = os.path.join(temp_output_dir, self.task_type)

        cont_input_path = '/mnt/work/input'
        cont_output_path = '/mnt/work/output'

        vol_mnts = []
        vol_binds = []

        string_input_ports = {}

        for port_name in self.inputs.portnames:

            port = self.inputs.__getattribute__(port_name)

            if port.type == 'directory':

                if port.value.path is None:
                    raise InvalidPortError('Directory Input ports must have a value')

                port_path = port.value.path

                # Check if abs path
                if os.path.isabs(port_path) and os.path.isdir(port_path):
                    dest_path = port_path
                # Check if relative path
                elif os.path.isabs(os.path.join(os.getcwd(), port_path)) and \
                        os.path.isdir(os.path.join(os.getcwd(), port_path)):
                    dest_path = os.path.join(os.getcwd(), port_path)
                # Use std input path from cwd.
                else:
                    dest_path = os.path.join(os.getcwd(), 'inputs', port.name)
                    if not os.path.isdir(dest_path):
                        raise InvalidPortError("Directory type input ports must be a valid directory")

                cont_path = os.path.join(cont_input_path, port.name)
                vol_mnts.append(cont_path)
                vol_binds.append(
                    '%s:%s:rw' % (dest_path, cont_path)
                )
            else:
                if port.value is not None:
                    string_input_ports['gbdx-input-port-' + port.name] = port.value

        for port_name in self.outputs.portnames:

            port = self.outputs.__getattribute__(port_name)

            if port.type == 'directory':
                if port.value.path is None:
                    # Write output to temp dir
                    dest_path = os.path.join(temp_output_dir, port.name)
                    port.value.path = dest_path
                    os.makedirs(dest_path)
                else:
                    # Write output to the ports value
                    # Assumption is it exists.
                    dest_path = port.value.path

                cont_path = os.path.join(cont_output_path, port.name)
                vol_mnts.append(cont_path)
                vol_binds.append(
                    '%s:%s:rw' % (dest_path, cont_path)
                )

        cont_args = {
            "image": self.image,
            "volumes": vol_mnts,
            "host_config": dkr.create_host_config(binds=vol_binds),
            "environment": string_input_ports
        }

        if self.command is not None:
            cont_args['command'] = self.command

        if self.verbose:
            print('Container Args: %s\n' % cont_args)

        container_id = dkr.create_container(**cont_args)

        if self.verbose:
            print('Container ID: %s\n' % container_id)

        # if pull:
        #     print('Pulling Latest Image')
        #     dkr.pull(img)

        print('\n%s Starting' % self.task_type)
        start_time = time.time()
        dkr.start(container_id.get('Id'))
        dkr.wait(container_id.get('Id'))
        end_time = time.time()
        print('Runtime: %ssec\n' % (end_time - start_time))

        output_ports_exist = self._get_output_string_ports(dkr, container_id)

        status_exist = self._get_task_status(dkr, container_id)

        output = dkr.logs(
            container=container_id.get('Id'),
            stdout=True,
            stderr=True
        ).decode("utf-8")

        print('\t--Start Output--:\n')
        print(output_ports_exist if output_ports_exist else '')
        print(output)
        print(status_exist if status_exist else '')
        print('\t--End Output--\n')

        # Stop and Remove Container
        dkr.remove_container(container_id.get('Id'))

    def _get_task_status(self, dkr, container_id):
        try:
            strm, _ = dkr.get_archive(
                container_id.get('Id'),
                '/mnt/work/status.json'
            )

            file_content = StringIO.StringIO(strm.read())
            tf = tarfile.open(fileobj=file_content)
            ef = tf.extractfile("status.json")

            self.status = json.load(ef)
            status_exist = None
        except Exception:
            status_exist = 'No status.json file found'

        return status_exist

    def _set_output_string_ports(self, output_str_ports):
        for port_name in self.outputs.portnames:
            port = self.outputs.__getattribute__(port_name)
            if port.name in output_str_ports.keys():
                port.value = output_str_ports[port.name]

    def _get_output_string_ports(self, dkr, container_id):
        try:
            strm, _ = dkr.get_archive(
                container_id.get('Id'),
                '/mnt/work/output/ports.json'
            )

            file_content = StringIO.StringIO(strm.read())
            tf = tarfile.open(fileobj=file_content)
            ef = tf.extractfile("ports.json")

            self._set_output_string_ports(json.load(ef))
            output_ports_exist = None
        except Exception:
            output_ports_exist = "No output ports.json found"

        return output_ports_exist
