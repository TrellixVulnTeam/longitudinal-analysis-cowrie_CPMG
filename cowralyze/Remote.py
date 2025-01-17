import subprocess
import sys, os
import threading


def run_on_remote(top_n_events):
    """Runner to execute map-reduce on remote node"""
    # executed on remote machine

    # Map
    mstream = open("/home/cowrie/cowrie/var/log/cowrie/Map.py")
    map_file = mstream.read()
    exec(map_file)

    # Reduce
    subprocess.run(['python3', '/home/cowrie/cowrie/var/log/cowrie/Reduce.py', f'{top_n_events}'])



def error_cli():
    """Processes input errors."""
    print(f"Please call script like: {sys.argv[0]} IP_ADDRESS PORT USER PASSWORD")
    sys.exit(1)


def fetch_from_remote(ip_address, port, user, pw):
    """Download reduced log files from remote node."""
    import paramiko
    try:
        # fetch reduced.json file
        print(f"Copying reduced JSON from {ip_address}:{port}")
        # Setup sftp connection and fetch the reduced.json file
        remote_path = '/home/cowrie/cowrie/var/log/cowrie/reduced.json'
        local_path = f'{os.path.dirname(__file__)}/{ip_address}_reduced.json'

        # Connect to remote host
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip_address, username=user, password=pw, port=port)

        sftp = client.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
        print(f'Downloaded reduced log file from {ip_address}:{port} into {local_path}')
        return local_path
    except Exception as e:
        print(f"Error fetching files from remote {ip_address}:{port}")
        print(e)
        exit(0)


def copy_scripts_to_remote(client):
    """Copy python scripts for map-reduce processing to remote node."""
    # Setup sftp connection and transmit necessary scripts
    sftp = client.open_sftp()
    print(f"copy {__file__}")
    sftp.put(__file__, '/home/cowrie/cowrie/var/log/cowrie/Remote.py')
    print(f"copy Map.py")
    sftp.put('Map.py', '/home/cowrie/cowrie/var/log/cowrie/Map.py')
    print(f"copy Reduce.py")
    sftp.put('Reduce.py', '/home/cowrie/cowrie/var/log/cowrie/Reduce.py')
    print(f"copy Local.py")
    sftp.put('Local.py', '/home/cowrie/cowrie/var/log/cowrie/Local.py')
    print(f"copy Helpers.py")
    sftp.put('Helpers.py', '/home/cowrie/cowrie/var/log/cowrie/Helpers.py')
    print(f"copy MapReduce.py")
    sftp.put('MapReduce.py', '/home/cowrie/cowrie/var/log/cowrie/MapReduce.py')
    print(f"copy requirements.txt")
    sftp.put('requirements.txt', '/home/cowrie/cowrie/var/log/cowrie/requirements.txt')
    print(f"copying config.json")
    sftp.put('config.json', '/home/cowrie/cowrie/var/log/cowrie/config.json')
    sftp.close()


def install_python_env_remote(client):
    """Install the python environment on the remote ubuntu 18.04 node."""
    commands = ["sudo apt-get -y update && sudo apt-get -y upgrade",
                "sudo apt-get install -y python3.9",
                "sudo apt install -y python3-pip",
                "sudo apt-get -y install python3-venv",
                "python3 -m venv honeypot-env",                                         # create virtual environment
                "source honeypot-env/bin/activate",
                "sudo -H pip3 install --upgrade pip",                                   # upgrade pip's
                "pip3 install -r /home/cowrie/cowrie/var/log/cowrie/requirements.txt"]  # install required libraries

    for command in commands:
        stdin, stdout, stderr = client.exec_command(command, get_pty=True)
        for line in iter(stdout.readline, ""):
            print(line, end="")


def deploy_exec_remote(ip_address, port, user, pw, top_n_events, setup_remote_environment):
    """Runner to deploy and execute Map-Reduce reduction on remote node."""
    import paramiko
    try:
        # Connect to remote host
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip_address, username=user, password=pw, port=port)

        if setup_remote_environment == 'True':
            print(f"Deploying scripts to {ip_address}:{port}")
            copy_scripts_to_remote(client)
            install_python_env_remote(client)

        print(f"Starting map-reduce on remote node <{ip_address}:{port}>")
        # Run the transmitted script remotely without args and show its output.
        stdin, stdout, stderr = client.exec_command(f'python3 /home/cowrie/cowrie/var/log/cowrie/Remote.py {top_n_events}', get_pty=True)

        for line in iter(stdout.readline, ""):
            print(line, end="")
        client.close()

    except Exception as e:
        print(f"Error deploying files to remote {ip_address}:{port}")
        print(e)
        exit(0)


def progress(current, total):
    c = round(current / (1024 ** 2), 2)
    t = round(total / (1024 ** 2), 2)
    print(f'{c} MB / {t} MB', end='\r')
    # print(f'{threading.current_thread()} : {c} MB / {t} MB')


def download_file(client, file, remote_folder_path, local_path):
    sftp = client.open_sftp()
    info = sftp.stat(remote_folder_path + "/" + file)
    size_mb = int(round((info.st_size / 1024 ** 2)))

    if size_mb > 500:
        print(f'Skipped {file} as too big for paramiko..')
        return

    file_remote = os.path.join(remote_folder_path, file)
    file_local = os.path.join(local_path, file)
    print(file_remote + ' >>>> ' + file_local)

    sftp.get(file_remote, file_local, callback=progress)
    sftp.close()


def download_scripts_from_remote(ip_address, port, user, pw, local_path):
    """Runner to copy cowrie log files from remote droplet."""
    import multiprocessing
    import paramiko
    from tqdm import tqdm
    print(f"Copying log files from {ip_address}:{port}")
    try:
        # Connect to remote host
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip_address, username=user, password=pw, port=port, timeout=100)

        sftp = client.open_sftp()
        remote_folder_path = '/home/cowrie/cowrie/var/log/cowrie'
        files = sftp.listdir(remote_folder_path)

        #threads = []
        for file in files:
            if '.mapped' in file or '.reduced' in file or '.log' in file or '.py' in file:
                continue
            download_file(client, file, remote_folder_path, local_path)

        # TODO: make multithreaded download in future

        #    t = threading.Thread(target=download_file, args=(client, file, remote_folder_path, local_path))
        #    threads.append(t)

        #for t in threads:
        #    t.start()

        #for t in threads:
        #    t.join()
            # _thread.start_new_thread(download_file, (client, file, remote_folder_path, local_path))
            # thread.start_new_thread(progress, ('20', '100'))
            # items.append((client, file, remote_folder_path, local_path))

        # pool = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
        # for _ in tqdm.tqdm(pool.starmap(download_file, items), total=len(items)):
            # log_files.append(_)
        #    pass

        for line in iter(sys.stdout.readline, ""):
            print(line, end="")
        client.close()

    except Exception as e:
        print(f"Error copying files from remote {ip_address}:{port}")
        print(e)
        exit(0)

if __name__ == '__main__':
    # !/usr/bin/env python3
    from Helpers import get_files_from_path, split_data_by_events, write_to_file    # do not delete this is necessary for remote execution
    """If command line argument provided call deploy + execute, else just execute as we are on remote node."""
    if len(sys.argv) > 4:
        try:
            ip_address = sys.argv[1]
            port = sys.argv[2]
            user = sys.argv[3]
            pw = sys.argv[4]

            # deploy to REMOTE server
            deploy_exec_remote(ip_address, port, user, pw, 5, False)
            # fetch reduced file from REMOTE server
            fetch_from_remote(ip_address, port, user, pw)
        except Exception as e:
            print(f"Error executing Remote.py script")
            print(e)
            exit(0)
    else:
        # No cmd-line args provided, run script normally (on REMOTE server)
        top_n_events = 5        # fallback
        if len(sys.argv) > 1:
            top_n_events = sys.argv[1]

        run_on_remote(top_n_events)
