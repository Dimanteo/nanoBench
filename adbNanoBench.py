import sys
import subprocess

TMPDIR = '/data/local/tmp/'
USING_ADB = False


def push(local, remote):
    try:
        subprocess.check_call(['adb', 'push', local, remote])
    except subprocess.CalledProcessError as e:
        sys.stderr.write(str(e.returncode) + ' ADB could not push ' + local + ' to ' + remote + ' ' + '\n')
        raise e


def pull(remote, local):
    try:
        subprocess.check_call(['adb', 'pull', remote, local])
    except subprocess.CalledProcessError as e:
        sys.stderr.write(str(e.returncode) + ' ADB could not pull ' + remote + ' to ' + local + '\n')
        raise e


def exec(cmd):
    try:
        output = subprocess.check_output(['adb', 'shell', cmd])
        return output
    except subprocess.CalledProcessError as e:
        sys.stderr.write(' ADB could not execute "' + cmd + '" ' + e.output + '\n')
        raise e


# TODO Get measurment results from device
def runNanoBench():
    pass
