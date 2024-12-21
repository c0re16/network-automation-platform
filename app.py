from flask import Flask, render_template, request, redirect
import duckdb as dd
import paramiko

class database():
    def __init__(self):
        self.con = dd.connect('network.db')
        self.con.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                hostname VARCHAR PRIMARY KEY,
                device_type VARCHAR NOT NULL,
                mgmt_ip VARCHAR NOT NULL,
                user VARCHAR NOT NULL,
                password VARCHAR NOT NULL,
                secondary_password VARCHAR,
                ios_version VARCHAR NOT NULL,
                location VARCHAR NOT NULL,
                device_owner VARCHAR
            );
        ''')
        self.con.execute('''
            CREATE TABLE IF NOT EXISTS device_interfaces (
                hostname VARCHAR NOT NULL,
                interface_name VARCHAR NOT NULL,
                mac_address VARCHAR NOT NULL,
                ip_address VARCHAR,
                subnet_mask VARCHAR,
                status VARCHAR,
                description VARCHAR,
                PRIMARY KEY (hostname, interface_name),
                FOREIGN KEY (hostname) REFERENCES devices(hostname)
            );
        ''')
        self.con.execute('''
            CREATE TABLE IF NOT EXISTS networks (
                network_name VARCHAR PRIMARY KEY,  
                network_address VARCHAR NOT NULL,    
                area VARCHAR NOT NULL,          
                ospf_area VARCHAR NOT NULL,
                ospf_network_type VARCHAR NOT NULL, 
                ospf_passive_interface BOOLEAN NOT NULL
            );
        ''')
        self.con.execute('''
            CREATE TABLE IF NOT EXISTS device_network_connections (
                hostname VARCHAR NOT NULL,
                interface_name VARCHAR NOT NULL,
                network_name VARCHAR NOT NULL,
                ip_address VARCHAR,
                PRIMARY KEY (hostname, interface_name, network_name), 
                FOREIGN KEY (hostname, interface_name) REFERENCES device_interfaces(hostname, interface_name),  -- Composite foreign key
                FOREIGN KEY (network_name) REFERENCES networks(network_name)
            );
        ''')
    def get_record(self, table, **kwargs):
        try:
            if len(kwargs) >= 2:
                querycondition = ''
                for key, value in kwargs.items():
                    querycondition += f"{key} = '{value}' AND "
                querycondition = querycondition.rstrip(' AND ')
            else:
                querycondition = ''
                for key, value in kwargs.items():
                    querycondition += f"{key} = '{value}'"
            query = f"SELECT * FROM {table} WHERE {querycondition}"

            print(query)
            result = self.con.execute(query).fetchall()
            return result
        except Exception as e:
            print(f"Error getting record from {table}: {e}")
            return None
    def get_all_records(self, table, **kwargs):
        try:
            query = f"SELECT * FROM {table}"

            print(query)
            result = self.con.execute(query).fetchall()
            print(result)
            return result
        except Exception as e:
            print(f"Error getting record from {table}: {e}")
            return None
    def add_record(self, table, **kwargs):
        try:

            querycols=', '.join(kwargs.keys())
            queryvalueslist =[]
            for value in kwargs.values():
                queryvalueslist.append(f"'{value}'")
            queryvalues=', '.join(queryvalueslist)
            query = f'INSERT INTO {table} ({querycols}) VALUES ({queryvalues})'

            print(query)
            self.con.execute(query)

            self.con.commit()  # Commit the transaction
            print(f"Record added to {table} successfully.")
        except Exception as e:
            print(f"Error adding record to {table}: {e}")
            self.con.rollback()  # Rollback if there was an error
    def describe_table(self, table):
        try:
            query = f"PRAGMA table_info({table})"
            result = self.con.execute(query).fetchall()
            print(query)
            cols = []
            for i in result:
                cols.append(i[1])
            return cols
        except Exception as e:
            print(f"Error describing table {table}: {e}")
            return []
    def update_record(self, table: str, primarykeys: dict, **kwargs: dict):
        try:
            theprimarykeys = ''
            for key, value in primarykeys.items():
                theprimarykeys += f"{key} = '{value}' AND "
            theprimarykeys = theprimarykeys.rstrip(' AND ')  # Remove the last 'AND'

        except Exception as e:
            print(f"Could not parse primarykeys: {e}")

        try:
            if len(kwargs) >= 2:
                update_payload = ''
                for key, value in kwargs.items():
                    update_payload += f"{key} = '{value}' , "
                update_payload = update_payload.rstrip(' , ')  # Remove the trailing comma
            else:
                update_payload = ''
                for key, value in kwargs.items():
                    update_payload += f"{key} = '{value}'"

            query = f"UPDATE {table} SET {update_payload} WHERE {theprimarykeys}"

            print(query)
            result = self.con.execute(query).fetchall()
            return result
        except Exception as e:
            print(f"Error updating record in {table}: {e}")
            return None
    def delete_record(self, table, primarykeys, **kwargs):

        try:
            theprimarykeys = ''
            for key, value in primarykeys.items():
                theprimarykeys += f"{key} = '{value}' AND "
            theprimarykeys = theprimarykeys.rstrip(' AND ')  # Remove the last 'AND'

        except Exception as e:
            print(f"Could not parse primarykeys: {e}")

        try:
            query = f"DELETE FROM {table} WHERE {theprimarykeys}"
            # Execute the query
            print(query)
            result = self.con.execute(query).fetchall()
            return result
        except Exception as e:
            print(f"Error deleting record in {table}: {e}")
            return None 
class device():
    def __init__(self, hostname, table="devices", device_type=None, mgmt_ip=None, user=None, password=None, ios_version=None, location=None, secondary_password=None, device_owner=None):
        self.table = table
        self.hostname = hostname
        self.device_type = device_type
        self.mgmt_ip = mgmt_ip
        self.user = user
        self.password = password
        self.ios_version = ios_version
        self.location = location
        self.secondary_password = secondary_password
        self.device_owner = device_owner
        self.primary_keys = {'hostname': self.hostname}
        self.running_config = None
        try:
            self.autofill()
        except Exception as e:
            print(f"Error initializing device: {e}")
    def autofill(self):
        try:
            result = database().get_record(table=self.table, hostname=self.hostname)
            if result == []:
                print('Device not found.')
                self.precheck()
                self.add_device()
            else:
                print("Device Found in Database")
                device_properties = self.get_device()
                for a, b in device_properties.items():
                    setattr(self, a, b)
        except Exception as e:
            print(f"Error in autofill: {e}")
    def precheck(self):
        try:
            for i in ["hostname", "device_type", "mgmt_ip", "user", "password", "ios_version", "location"]:
                if not getattr(self, i):
                    raise ValueError(f'{i} not populated')
        except Exception as e:
            print(f"Error in precheck: {e}")
    def add_device(self):
        try:
            #mandatory_cols = ["hostname", "device_type", "mgmt_ip", "user", "password", "ios_version", "location"]
            database().add_record(table=self.table, hostname=self.hostname,device_type=self.device_type,mgmt_ip=self.mgmt_ip,user=self.user,password=self.password,ios_version=self.ios_version,location=self.location)
        except Exception as e:
            print(f"Error adding device: {e}")
    def get_device(self):
        try:
            cols = database().describe_table(self.table)
            values = database().get_record(self.table, hostname=self.hostname)
            result = dict(zip(cols, values[0]))
            return result
        except Exception as e:
            print(f"Error getting device information: {e}")
            return {}
    def update_device(self, **kwargs):
        try:
            updates = dict(kwargs)
            # Updating attributes first
            for key, value in updates.items():
                setattr(self, key, value)            
            database().update_record(self.table, self.primary_keys, **updates)

        except Exception as e:
            print(f"Error updating network interface: {e}")

    def delete_device(self):
        try:
            database().delete_record(self.table, self.primary_keys)
        except Exception as e:
            print(f"Error deleting device: {e}")      
    def get_running_config(self):
        from netmiko import ConnectHandler
        device = {
        'device_type': 'cisco_ios', 
        'host': self.mgmt_ip,        
        'username': self.user,    
        'password': self.password,   
        'port': 22,                   
        'secret': self.secondary_password, 
        'verbose': True,                   }
        print(device)
        try:
            connection = ConnectHandler(**device)
            connection.enable()
            output = connection.send_command('show run')
            print("Command output:")
            print(output)
            connection.disconnect()

        except Exception as e:
            print(f"Failed to connect to the device: {e}")  

    def send_commands(self,commands):
        from netmiko import ConnectHandler
        device = {
        'device_type': 'cisco_ios',    
        'host': self.mgmt_ip,            
        'username': self.user,       
        'password': self.password,        
        'port': 22,                       
        'secret': self.secondary_password, 
        'verbose': True,                   }
        print(device)
        try:
            # Connect to the device
            connection = ConnectHandler(**device)

            # Enter enable mode if necessary
            connection.enable()
            # Example command to test the connection
            output = connection.send_config_set(commands.splitlines())
            #self.running_config = output
            print("Command output:")
            print(output)
            return output

            connection.disconnect()

        except Exception as e:
            print(f"Failed to connect to the device: {e}")  
    def day_one(self, **kwargs):
    
        updates = dict(kwargs)
        for key, value in updates.items():
            setattr(self, key, value)   
    
        # assert self.hostname not None
        # assert self.ntp_server_ip not None
        # assert self.snmp_server_ip not None
        # assert self.snmp_community not None
        # assert self.snmp_user not None
        # assert self.snmp_auth_password not None
        # assert self.snmp_priv_password not None
        # assert self.snmp_access_list not None
        config_commands = f"""
        hostname {self.hostname}

        ntp server {self.ntp_server_ip}

        snmp-server community {self.snmp_community} RO

        snmp-server user {self.snmp_user} v3 auth md5 {self.snmp_auth_password} priv aes 128 {self.snmp_priv_password} access {self.snmp_access_list}

        snmp-server host {self.snmp_server_ip} version 3 priv {self.snmp_user}

        snmp-server enable traps
        """
        self.send_commands(config_commands)

class network():
    def __init__(self, network_name, table="networks", network_address=None, area=None, ospf_area=None, ospf_network_type=None, ospf_passive_interface=None):
        self.table = table
        self.network_name = network_name
        self.network_address = network_address
        self.area = area
        self.ospf_area = ospf_area
        self.ospf_network_type = ospf_network_type
        self.ospf_passive_interface = ospf_passive_interface
        self.primary_keys = {'network_name': self.network_name}
        try:
            self.autofill()
        except Exception as e:
            print(f"Error initializing network: {e}")
    def autofill(self):
        try:
            result = database().get_record(table=self.table, network_name=self.network_name)
            if result == []:
                print('Network not found.')
                self.precheck()
                self.add_network()
            else:
                print("Network Found in Database")
                network_properties = self.get_network()
                for a, b in network_properties.items():
                    setattr(self, a, b)
        except Exception as e:
            print(f"Error in autofill: {e}")
    def precheck(self):
        try:
            for i in ["network_name", "network_address", "area", "ospf_area", "ospf_network_type", "ospf_passive_interface"]:
                if not getattr(self, i):
                    raise ValueError(f'{i} not populated')
        except Exception as e:
            print(f"Error in precheck: {e}")
    def add_network(self):
        try:
            database().add_record(table=self.table,
                network_name=self.network_name,
                network_address=self.network_address,
                area=self.area,
                ospf_area=self.ospf_area,
                ospf_network_type=self.ospf_network_type,
                ospf_passive_interface=self.ospf_passive_interface
            )
        except Exception as e:
            print(f"Error adding network: {e}")
    def get_network(self):
        try:
            cols = database().describe_table(self.table)
            values = database().get_record(self.table, network_name=self.network_name)
            result = dict(zip(cols, values[0]))
            return result
        except Exception as e:
            print(f"Error getting network information: {e}")
            return {}
    def update_network(self, **kwargs):
        try:
            updates = dict(kwargs)
            for key, value in updates.items():
                setattr(self, key, value)
            database().update_record(self.table, self.primary_keys, **updates)

        except Exception as e:
            print(f"Error updating network: {e}")
    def delete_network(self):
        try:
            database().delete_record(self.table, self.primary_keys)
            print(f"Network {self.network_name} deleted successfully.")
        except Exception as e:
            print(f"Error deleting network: {e}")
class device_interface():
    def __init__(self, hostname, interface_name, table="device_interfaces", mac_address=None, ip_address=None, subnet_mask=None, status=None, description=None):
        self.table = table
        self.hostname = hostname
        self.interface_name = interface_name
        self.mac_address = mac_address
        self.ip_address = ip_address
        self.subnet_mask = subnet_mask
        self.status = status
        self.description = description
        self.primary_keys = {
                'hostname': self.hostname, 
                'interface_name': self.interface_name
            }
        try:
            self.autofill()
        except Exception as e:
            print(f"Error initializing network interface: {e}")

    def autofill(self):
        try:
            result = database().get_record(table=self.table, hostname=self.hostname,interface_name=self.interface_name)
            if result == []:
                print('Network interface not found.')
                self.precheck()
                self.add_device_interface()
            else:
                print("Network Interface Found in Database")
                interface_properties = self.get_device_interface()
                for a, b in interface_properties.items():
                    setattr(self, a, b)
        except Exception as e:
            print(f"Error in autofill: {e}")

    def precheck(self):
        try:
            for i in ["hostname", "interface_name", "mac_address"]:
                if not getattr(self, i):
                    raise ValueError(f'{i} not populated')
        except Exception as e:
            print(f"Error in precheck: {e}")

    def add_device_interface(self):
        try:
            database().add_record(table=self.table,
                hostname=self.hostname,
                interface_name=self.interface_name,
                mac_address=self.mac_address,
                ip_address=self.ip_address,
                subnet_mask=self.subnet_mask,
                status=self.status,
                description=self.description
            )
        except Exception as e:
            print(f"Error adding network interface: {e}")

    def get_device_interface(self):
        try:
            cols = database().describe_table(self.table)
            values = database().get_record(self.table, hostname=self.hostname, interface_name=self.interface_name)
            result = dict(zip(cols, values[0]))
            return result
        except Exception as e:
            print(f"Error getting network interface information: {e}")
            return {}


    def update_device_interface(self, **kwargs):
        try:
            updates = dict(kwargs)
            for key, value in updates.items():
                setattr(self, key, value)


            primary_keys = {
                'hostname': self.hostname, 
                'interface_name': self.interface_name
            }

            database().update_record(self.table, primary_keys, **updates)

        except Exception as e:
            print(f"Error updating device network connection: {e}")

    def delete_device_interface(self):
        try:

            database().delete_record(self.table, self.primary_keys)
            print(f"Interface {self.hostname} deleted successfully.")
        except Exception as e:
            print(f"Error deleting device: {e}")

    def sync_interfaces(self):
        try:
            from netmiko import ConnectHandler
            device = {
            'device_type': 'cisco_ios',
            'host': self.mgmt_ip,    
            'username': self.user,  
            'password': self.password,            
            'port': 22,                       
            'secret': self.secondary_password, 
            'verbose': True,                   }
            print(device)
            try:
                connection = ConnectHandler(**device)
                connection.enable()
                output = connection.send_config_set('sh ip int br')
                print("Command output:")
                print(output)
                return output
                connection.disconnect()
            except Exception as e:
                print(f"Error Connecting to device: {e}")
        except Exception as e:
            print(f"Error grabbing interface config: {e}")
class device_network_connection():
    def __init__(self, hostname, interface_name, network_name, ip_address=None, table="device_network_connections"):
        self.table = table
        self.hostname = hostname
        self.interface_name = interface_name
        self.network_name = network_name
        self.ip_address = ip_address
        self.primary_keys = {'hostname':self.hostname, 'interface_name':self.interface_name, "network_name":self.network_name}
        try:
            self.autofill()
        except Exception as e:
            print(f"Error initializing device network connection: {e}")

    def autofill(self):
        try:
            result = database().get_record(table=self.table, hostname=self.hostname,interface_name=self.interface_name,network_name=self.network_name)
            if result == []:
                print('Device Network Connection not found.')
                self.precheck()
                self.add_device_network_connection()
            else:
                print("Device Network Connection Found in Database")
                connection_properties = self.get_device_network_connection()
                for a, b in connection_properties.items():
                    setattr(self, a, b)
        except Exception as e:
            print(f"Error in autofill: {e}")

    def precheck(self):
        try:
            for i in ["hostname", "interface_name", "network_name"]:
                if not getattr(self, i):
                    raise ValueError(f'{i} not populated')
        except Exception as e:
            print(f"Error in precheck: {e}")

    def add_device_network_connection(self):
        try:
            database().add_record(
                table=self.table,
                hostname=self.hostname,
                interface_name=self.interface_name,
                network_name=self.network_name,
                ip_address=self.ip_address)
        except Exception as e:
            print(f"Error adding device network connection: {e}")

    def get_device_network_connection(self):
        try:
            cols = database().describe_table(self.table)
            values = database().get_record(self.table, 
                hostname=self.hostname, 
                interface_name=self.interface_name,
                network_name=self.network_name)
            result = dict(zip(cols, values[0]))
            return result
        except Exception as e:
            print(f"Error getting device network connection information: {e}")
            return {}


    def update_device_network_connection(self, **kwargs):
        try:
            updates = dict(kwargs)
            for key, value in updates.items():
                setattr(self, key, value)
            database().update_record(self.table, self.primary_keys, **updates)

        except Exception as e:
            print(f"Error updating device network connection: {e}")
    def delete_device_network_connection(self):
        try:
            database().delete_record(self.table, self.primary_keys)
            print(f"Device {self.hostname} deleted successfully.")
        except Exception as e:
            print(f"Error deleting device: {e}")   




app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    try:
        # Fetch records for both devices and networks
        rows_devices = database().get_all_records('devices')
        rows_networks = database().get_all_records('networks')
        rows_device_interfaces = database().get_all_records('device_interfaces')
        rows_device_network_connections = database().get_all_records('device_network_connections')

        # Get column names for both devices and networks
        columns_devices = database().describe_table('devices')
        columns_networks = database().describe_table('networks')
        columns_device_interfaces = database().describe_table('device_interfaces')
        columns_device_network_connections = database().describe_table('device_network_connections')

        # Convert rows to a list of dictionaries for both devices and networks
        entries_devices = [dict(zip(columns_devices, row)) for row in rows_devices]
        entries_networks = [dict(zip(columns_networks, row)) for row in rows_networks]
        entries_device_interfaces = [dict(zip(columns_device_interfaces, row)) for row in rows_device_interfaces]
        entries_device_network_connections = [dict(zip(columns_device_network_connections, row)) for row in rows_device_network_connections]

        # Prepare data for the graphs
        device_types = [entry['device_type'] for entry in entries_devices]
        network_areas = [entry['area'] for entry in entries_networks]
        interface_status = [entry['status'] for entry in entries_device_interfaces]
        connection_network_names = [entry['network_name'] for entry in entries_device_network_connections]

        # Count occurrences for each category (use a helper function for counting)
        device_type_counts = {device: device_types.count(device) for device in set(device_types)}
        network_area_counts = {area: network_areas.count(area) for area in set(network_areas)}
        interface_status_counts = {status: interface_status.count(status) for status in set(interface_status)}
        connection_network_counts = {network: connection_network_names.count(network) for network in set(connection_network_names)}

        return render_template('dashboard.html', 
                               entries_devices=entries_devices, 
                               entries_networks=entries_networks,
                               device_type_counts=device_type_counts,
                               network_area_counts=network_area_counts,
                               interface_status_counts=interface_status_counts,
                               connection_network_counts=connection_network_counts)
    except Exception as e:
        return f"Error retrieving dashboard data: {e}", 500

@app.route('/enroll_device')
def enroll():
    return render_template('device_enroll.html')

@app.route('/submit-enrollment', methods=['POST'])
def submit_enrollment():
    # Retrieve form data
    hostname = request.form.get('hostname')
    device_type = request.form.get('device_type')
    mgmt_ip = request.form.get('mgmt_ip')
    user = request.form.get('user')
    password = request.form.get('password')
    ios_version = request.form.get('ios_version')
    location = request.form.get('location')
    secondary_password = request.form.get('secondary_password') or None
    device_owner = request.form.get('device_owner') or None

    try:
        # Create and save the new device using the 'device' class
        new_device = device(
            hostname=hostname,
            device_type=device_type,
            mgmt_ip=mgmt_ip,
            user=user,
            password=password,
            ios_version=ios_version,
            location=location,
            secondary_password=secondary_password,
            device_owner=device_owner
        )
        return redirect('/dashboard')  # Redirect to dashboard after successful enrollment
    except Exception as e:
        return f"Error enrolling device: {e}", 500

@app.route('/enroll_network', methods=['GET', 'POST'])
def network_enroll():
    if request.method == 'POST':
        try:
            # Get the form data
            network_name = request.form['network_name']
            network_address = request.form['network_address']
            area = request.form['area']
            ospf_area = request.form['ospf_area']
            ospf_network_type = request.form['ospf_network_type']
            ospf_passive_interface = 'ospf_passive_interface' in request.form  # Checkbox handling

            # Create a new network entry in the database
            database().add_record('networks',
                                  network_name=network_name,
                                  network_address=network_address,
                                  area=area,
                                  ospf_area=ospf_area,
                                  ospf_network_type=ospf_network_type,
                                  ospf_passive_interface=ospf_passive_interface)
            
            return redirect('/dashboard')  # Redirect to the dashboard after success
        except Exception as e:
            return f"Error enrolling network: {e}", 500
    return render_template('network_enroll.html')

@app.route('/device-interface-enroll', methods=['GET', 'POST'])
def device_interface_enroll():
    if request.method == 'POST':
        try:
            # Fetch form data
            hostname = request.form['hostname']
            interface_name = request.form['interface_name']
            mac_address = request.form['mac_address']
            ip_address = request.form['ip_address']
            subnet_mask = request.form['subnet_mask']
            status = request.form['status']
            description = request.form['description']

            # Create an interface record
            database().add_record('device_interfaces',
                                  hostname=hostname,
                                  interface_name=interface_name,
                                  mac_address=mac_address,
                                  ip_address=ip_address,
                                  subnet_mask=subnet_mask,
                                  status=status,
                                  description=description)

            return redirect(url_for('dashboard'))  # Redirect back to the dashboard
        except Exception as e:
            return f"Error enrolling device interface: {e}", 500

    # For GET request, display the form to enroll a new device interface
    return render_template('device_interface_enroll.html')



@app.route('/device-network-connection-enroll', methods=['GET', 'POST'])
def device_network_connection_enroll():
    if request.method == 'POST':
        try:
            # Fetch form data
            hostname = request.form['hostname']
            interface_name = request.form['interface_name']
            network_name = request.form['network_name']
            ip_address = request.form['ip_address']

            # Add the device network connection record to the database
            database().add_record('device_network_connections',
                                  hostname=hostname,
                                  interface_name=interface_name,
                                  network_name=network_name,
                                  ip_address=ip_address)

            return redirect('dashboard')  # Redirect back to the dashboard
        except Exception as e:
            return f"Error enrolling device network connection: {e}", 500

    # For GET request, display the form to enroll a new device network connection
    return render_template('device_network_connection_enroll.html')

@app.route('/modify-device/<hostname>', methods=['GET', 'POST'])
def modify_device(hostname):
    try:
        # Fetch device details based on hostname
        device = database().get_record('devices', hostname=hostname)
        
        if not device:
            return "Device not found", 404

        # If form is submitted, update the device
        if request.method == 'POST':
            updated_device = {
                'device_type': request.form['device_type'],
                'mgmt_ip': request.form['mgmt_ip'],
                'user': request.form['user'],
                'password': request.form['password'],
                'ios_version': request.form['ios_version'],
                'location': request.form['location'],
                'device_owner': request.form['device_owner']
            }

            # Update the device record in the database
            database().update_record('devices', {'hostname': hostname}, **updated_device)
            return redirect('dashboard')  # Redirect back to the dashboard

        # For GET request, display the current details in the form
        return render_template('modify_device.html', device=device)

    except Exception as e:
        return f"Error modifying device: {e}", 500
@app.route('/modify-network/<network_name>', methods=['GET', 'POST'])
def modify_network(network_name):
    try:
        # Fetch network details based on network_name
        network = database().get_record('networks', network_name=network_name)

        if not network:
            return "Network not found", 404

        # If form is submitted, update the network
        if request.method == 'POST':
            updated_network = {
                'network_type': request.form['network_type'],
                'network_address': request.form['network_address'],
                'area': request.form['area'],
                'ospf_area': request.form['ospf_area'],
                'ospf_network_type': request.form['ospf_network_type'],
                'ospf_passive_interface': 'ospf_passive_interface' in request.form  # Checkbox handling
            }

            # Update the network record in the database
            database().update_record('networks', {'network_name': network_name}, **updated_network)
            return redirect('dashboard')  # Redirect back to the dashboard

        # For GET request, display the current details in the form
        return render_template('modify_network.html', network=network)

    except Exception as e:
        return f"Error modifying network: {e}", 500

app.run(debug=True)
r1 = device(hostname='S1',device_type="cisco",mgmt_ip="192.168.2.1",user='root',password='password',location="TOR-A6-B9")
r1.secondary_password = 'password'
r1.get_running_config()
